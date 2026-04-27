"""
CSV parser with auto-detection for Indonesian banks (BCA, Mandiri, BNI, BRI).

Each bank ships slightly different statement CSVs. We auto-detect by scanning
the header row for bank-specific column signatures, then normalize rows into
{date, amount, type, description, category, bank}.

Amount is always stored as a positive float; `type` is "debit" (money out) or
"credit" (money in). Indonesian statements commonly use `Rp` prefixes, dots as
thousand separators, and commas as decimal separators — we handle both styles.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

SUPPORTED_BANKS = ("BCA", "Mandiri", "BNI", "BRI")


@dataclass
class ParsedRow:
    date: date
    amount: float
    type: str  # "debit" | "credit"
    description: str
    bank: str


# ---------- helpers ----------

_MONTHS_ID = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5, "jun": 6,
    "jul": 7, "agu": 8, "agus": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10,
    "nov": 11, "des": 12, "dec": 12,
}


def _clean_amount(value: str) -> float:
    """Parse Indonesian-style amount strings into a positive float.

    Accepts forms like "Rp 1.234.567,89", "1,234,567.89", "1234567.89",
    trailing " DB" / " CR" markers, parentheses for negatives, and blanks.
    """
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = re.sub(r"(?i)\b(db|cr|dr)\b", "", s)
    s = re.sub(r"(?i)rp\.?", "", s)
    s = s.replace("\xa0", "").replace(" ", "")
    if not s or s in {"-", "--"}:
        return 0.0
    has_dot = "." in s
    has_comma = "," in s
    if has_dot and has_comma:
        # Whichever appears last is the decimal separator.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma and not has_dot:
        # Comma alone: treat as decimal if exactly 1-2 trailing digits, else thousands sep.
        parts = s.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot and not has_comma:
        parts = s.split(".")
        # If every non-first segment is exactly 3 digits, dots are thousands separators.
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")
    try:
        val = float(s)
    except ValueError:
        return 0.0
    if neg:
        val = -val
    return val


def _parse_date(value: str) -> date | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Try common formats first.
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
        "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # BCA-style "DD/MM" without year — caller should not reach here normally.
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})$", s)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        try:
            return date(datetime.now().year, month, day)
        except ValueError:
            return None
    # "12 Jan 2024" / "12-Jan-2024"
    m = re.match(r"^(\d{1,2})[\s\-/]([A-Za-z]{3,4})[\s\-/](\d{2,4})$", s)
    if m:
        day = int(m.group(1))
        mon = _MONTHS_ID.get(m.group(2)[:3].lower())
        year = int(m.group(3))
        if year < 100:
            year += 2000
        if mon:
            try:
                return date(year, mon, day)
            except ValueError:
                return None
    return None


def _normalize_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", h.lower()) if h else ""


# ---------- bank detection ----------

def detect_bank(headers: list[str]) -> str | None:
    """Return one of SUPPORTED_BANKS (or None) based on CSV header signatures."""
    norm = {_normalize_header(h) for h in headers}

    bca_hits = sum(h in norm for h in ("tanggal", "keterangan", "cabang")) + (
        1 if any("dbcr" in h or h == "dbcr" for h in norm) else 0
    )
    if bca_hits >= 2 and ("cabang" in norm or any("dbcr" in h for h in norm)):
        return "BCA"

    mandiri_hits = sum(h in norm for h in ("tanggaltransaksi", "tanggal", "remark")) + sum(
        h in norm for h in ("debit", "kredit", "credit", "saldo")
    )
    if "remark" in norm and ("debit" in norm) and ("kredit" in norm or "credit" in norm):
        return "Mandiri"

    bni_hits = sum(
        h in norm
        for h in ("tgltransaksi", "tglpembukuan", "uraiantransaksi", "teller", "debet", "kredit")
    )
    if bni_hits >= 3 or ("uraiantransaksi" in norm and ("debet" in norm or "kredit" in norm)):
        return "BNI"

    bri_hits = sum(
        h in norm for h in ("postdate", "transactiondate", "description", "debet", "kredit", "balance")
    )
    if bri_hits >= 3 or ("postdate" in norm and "description" in norm):
        return "BRI"

    # Fallback heuristic: if we see debit/credit + description/keterangan, treat as Mandiri.
    if ("debit" in norm or "debet" in norm) and (
        "kredit" in norm or "credit" in norm
    ) and ("keterangan" in norm or "description" in norm or "remark" in norm):
        if mandiri_hits >= bni_hits and mandiri_hits >= bri_hits:
            return "Mandiri"
        if bni_hits >= bri_hits:
            return "BNI"
        return "BRI"
    return None


# ---------- per-bank row parsers ----------

def _col(row: dict[str, str], *aliases: str) -> str:
    """Return the first matching column value (aliases matched loosely)."""
    norm_map = {_normalize_header(k): k for k in row.keys() if k is not None}
    for a in aliases:
        key = norm_map.get(_normalize_header(a))
        if key is not None:
            v = row.get(key)
            if v is not None:
                return str(v).strip()
    return ""


def _row_bca(row: dict[str, str]) -> ParsedRow | None:
    d = _parse_date(_col(row, "Tanggal", "Tanggal Transaksi", "Date"))
    if not d:
        return None
    desc = _col(row, "Keterangan", "Description", "Remark").replace("\n", " ").strip()
    cabang = _col(row, "Cabang", "Branch")
    if cabang and cabang.lower() not in desc.lower():
        desc = f"{desc} ({cabang})" if desc else cabang
    amount_raw = _col(row, "Jumlah", "Amount", "Nominal", "Mutasi")
    flag = _col(row, "DB/CR", "DB / CR", "D/C", "Type").upper()
    amount = _clean_amount(amount_raw)
    if amount == 0 and not amount_raw:
        # Split debit/credit style
        debit = _clean_amount(_col(row, "Debit", "Debet"))
        credit = _clean_amount(_col(row, "Credit", "Kredit"))
        if debit > 0:
            return ParsedRow(d, debit, "debit", desc, "BCA")
        if credit > 0:
            return ParsedRow(d, credit, "credit", desc, "BCA")
        return None
    tx_type: str
    if "DB" in flag or "DR" in flag:
        tx_type = "debit"
    elif "CR" in flag:
        tx_type = "credit"
    elif amount < 0:
        tx_type = "debit"
        amount = abs(amount)
    else:
        tx_type = "credit"
    return ParsedRow(d, abs(amount), tx_type, desc, "BCA")


def _row_split_debit_credit(row: dict[str, str], bank: str) -> ParsedRow | None:
    d = _parse_date(
        _col(row, "Tanggal", "Tanggal Transaksi", "Tgl. Transaksi", "Tgl Transaksi",
             "Post Date", "PostDate", "POSTDATE", "Transaction Date", "Date")
    )
    if not d:
        return None
    desc = _col(
        row, "Remark", "Uraian Transaksi", "Uraian", "Keterangan", "Description",
        "Narasi", "Berita"
    ).replace("\n", " ").strip()
    debit = _clean_amount(_col(row, "Debit", "Debet", "DEBET", "DEBIT"))
    credit = _clean_amount(_col(row, "Credit", "Kredit", "KREDIT", "CREDIT"))
    if debit > 0 and credit == 0:
        return ParsedRow(d, debit, "debit", desc, bank)
    if credit > 0 and debit == 0:
        return ParsedRow(d, credit, "credit", desc, bank)
    # Some banks use single signed "Amount" column
    amount = _clean_amount(_col(row, "Amount", "Nominal", "Mutasi", "Jumlah"))
    if amount != 0:
        return ParsedRow(d, abs(amount), "debit" if amount < 0 else "credit", desc, bank)
    return None


_BANK_PARSERS = {
    "BCA": _row_bca,
    "Mandiri": lambda r: _row_split_debit_credit(r, "Mandiri"),
    "BNI": lambda r: _row_split_debit_credit(r, "BNI"),
    "BRI": lambda r: _row_split_debit_credit(r, "BRI"),
}


# ---------- public API ----------

def _sniff_reader(text: str) -> tuple[csv.DictReader, list[str]]:
    # Try to sniff the dialect; fall back to comma.
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        class _D(csv.excel):
            delimiter = ","
        dialect = _D
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    return reader, headers


def parse_csv(
    content: bytes | str, bank_hint: str | None = None
) -> tuple[str, list[ParsedRow], list[str]]:
    """Parse CSV bytes/text. Returns (bank, rows, errors).

    `bank_hint` overrides auto-detection if provided and supported.
    """
    if isinstance(content, bytes):
        # Try utf-8 first, fall back to latin-1.
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = content.decode("utf-8", errors="replace")
    else:
        text = content

    # Strip BOM and leading blank lines.
    text = text.lstrip("\ufeff")
    reader, headers = _sniff_reader(text)

    bank = bank_hint if bank_hint in SUPPORTED_BANKS else detect_bank(headers)
    errors: list[str] = []
    if bank is None:
        return "", [], [
            f"Could not detect bank from headers: {headers}. "
            f"Supported: {', '.join(SUPPORTED_BANKS)}."
        ]

    parser = _BANK_PARSERS[bank]
    rows: list[ParsedRow] = []
    for i, raw in enumerate(reader, start=2):  # row 1 = header
        if not any((v or "").strip() for v in raw.values()):
            continue
        try:
            parsed = parser(raw)
        except Exception as e:  # noqa: BLE001
            errors.append(f"Row {i}: {e}")
            continue
        if parsed is None:
            continue
        rows.append(parsed)
    return bank, rows, errors


def dedupe_rows(rows: Iterable[ParsedRow]) -> list[ParsedRow]:
    """Remove exact duplicates within the same CSV import."""
    seen: set[tuple] = set()
    out: list[ParsedRow] = []
    for r in rows:
        key = (r.date.isoformat(), round(r.amount, 2), r.type, r.description.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
