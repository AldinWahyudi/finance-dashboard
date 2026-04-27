import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { ImportResult } from "../types";

const BANKS = ["", "BCA", "Mandiri", "BNI", "BRI"];

export function ImportPage() {
  const [bank, setBank] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [dragover, setDragover] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function upload(file: File) {
    setErr(null);
    setResult(null);
    setBusy(true);
    try {
      const r = await api.importCsv(file, bank || undefined);
      setResult(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2 style={{ margin: "0 0 1rem" }}>Import CSV</h2>
      <div className="card">
        <p className="muted" style={{ marginTop: 0 }}>
          Upload a statement export from BCA, Mandiri, BNI, or BRI. Bank is auto-detected from the
          CSV header; use the dropdown below to override.
        </p>
        <div className="flex gap-2 wrap mb-2" style={{ alignItems: "flex-end" }}>
          <div style={{ minWidth: 200 }}>
            <label>Bank (optional)</label>
            <select value={bank} onChange={(e) => setBank(e.target.value)}>
              {BANKS.map((b) => (
                <option key={b} value={b}>
                  {b || "Auto-detect"}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div
          className={`drop-zone ${dragover ? "dragover" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragover(true);
          }}
          onDragLeave={() => setDragover(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragover(false);
            const f = e.dataTransfer.files[0];
            if (f) upload(f);
          }}
        >
          {busy
            ? "Uploading…"
            : "Click to select a CSV file, or drop one here."}
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
              e.target.value = "";
            }}
          />
        </div>

        {err && <div className="alert danger mt-2">{err}</div>}

        {result && (
          <div className="mt-2">
            <div className="alert">
              Detected bank: <strong>{result.bank}</strong>. Inserted {result.inserted} new
              transactions, skipped {result.skipped} duplicates.
              {result.errors.length > 0 && (
                <ul>{result.errors.slice(0, 5).map((e, i) => <li key={i}>{e}</li>)}</ul>
              )}
            </div>
            <p>
              <Link to="/transactions">View transactions</Link> ·{" "}
              <Link to="/">Go to dashboard</Link>
            </p>
          </div>
        )}
      </div>

      <div className="card mt-2">
        <h2>Expected CSV headers</h2>
        <ul className="muted" style={{ lineHeight: 1.7 }}>
          <li><strong>BCA</strong>: Tanggal, Keterangan, Cabang, Jumlah, DB/CR</li>
          <li><strong>Mandiri</strong>: Tanggal, Remark, Debit, Credit, Saldo</li>
          <li><strong>BNI</strong>: Tgl Transaksi, Tgl Pembukuan, Uraian Transaksi, Teller, Debet, Kredit, Saldo</li>
          <li><strong>BRI</strong>: POSTDATE, TRANSACTION DATE, DESCRIPTION, DEBET, KREDIT, BALANCE</li>
        </ul>
        <p className="muted">
          Amounts may include <code>Rp</code>, thousand-dots, or decimal-comma — all are handled.
        </p>
      </div>
    </>
  );
}
