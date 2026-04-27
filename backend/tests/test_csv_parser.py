from datetime import date

from app.services.csv_parser import _clean_amount, detect_bank, parse_csv


def test_clean_amount_indonesian_and_intl():
    assert _clean_amount("Rp 1.234.567,89") == 1234567.89
    assert _clean_amount("1,234,567.89") == 1234567.89
    assert _clean_amount("1234567.89") == 1234567.89
    assert _clean_amount("50.000") == 50000.0
    assert _clean_amount("50,00") == 50.0
    assert _clean_amount("100 DB") == 100.0
    assert _clean_amount("(250,50)") == -250.5
    assert _clean_amount("") == 0.0
    assert _clean_amount("-") == 0.0


def test_detect_bank_bca():
    headers = ["Tanggal", "Keterangan", "Cabang", "Jumlah", "DB/CR"]
    assert detect_bank(headers) == "BCA"


def test_detect_bank_mandiri():
    headers = ["Tanggal", "Remark", "Debit", "Credit", "Saldo"]
    assert detect_bank(headers) == "Mandiri"


def test_detect_bank_bni():
    headers = [
        "Tgl Transaksi", "Tgl Pembukuan", "Uraian Transaksi", "Teller", "Debet", "Kredit", "Saldo"
    ]
    assert detect_bank(headers) == "BNI"


def test_detect_bank_bri():
    headers = ["POSTDATE", "TRANSACTION DATE", "DESCRIPTION", "DEBET", "KREDIT", "BALANCE"]
    assert detect_bank(headers) == "BRI"


def test_parse_bca_csv():
    csv_text = (
        "Tanggal,Keterangan,Cabang,Jumlah,DB/CR\n"
        "12/03/2024,TRANSFER DARI BOSS,0001,5.000.000,CR\n"
        "13/03/2024,GOFOOD STARBUCKS,0001,75.000,DB\n"
        "14/03/2024,INDOMARET PAYMENT,0001,50.000,DB\n"
    )
    bank, rows, errors = parse_csv(csv_text.encode("utf-8"))
    assert bank == "BCA"
    assert errors == []
    assert len(rows) == 3
    assert rows[0].date == date(2024, 3, 12)
    assert rows[0].type == "credit"
    assert rows[0].amount == 5000000.0
    assert rows[1].type == "debit"
    assert "GOFOOD" in rows[1].description


def test_parse_mandiri_csv():
    csv_text = (
        "Tanggal,Remark,Debit,Credit,Saldo\n"
        "2024-03-01,GAJI BULANAN,0,10.000.000,10.000.000\n"
        "2024-03-02,GRAB TRANSPORT,25.000,0,9.975.000\n"
    )
    bank, rows, errors = parse_csv(csv_text.encode("utf-8"))
    assert bank == "Mandiri"
    assert len(rows) == 2
    assert rows[0].type == "credit" and rows[0].amount == 10000000.0
    assert rows[1].type == "debit" and rows[1].amount == 25000.0


def test_parse_bni_csv():
    csv_text = (
        "Tgl Transaksi,Tgl Pembukuan,Uraian Transaksi,Teller,Debet,Kredit,Saldo\n"
        "2024-04-01,2024-04-01,PLN LISTRIK,0001,500000,0,5500000\n"
        "2024-04-05,2024-04-05,TRANSFER MASUK,0001,0,2000000,7500000\n"
    )
    bank, rows, errors = parse_csv(csv_text.encode("utf-8"))
    assert bank == "BNI"
    assert len(rows) == 2
    assert rows[0].amount == 500000.0 and rows[0].type == "debit"
    assert rows[1].amount == 2000000.0 and rows[1].type == "credit"


def test_parse_bri_csv():
    csv_text = (
        "POSTDATE,TRANSACTION DATE,DESCRIPTION,DEBET,KREDIT,BALANCE\n"
        "01/05/2024,01/05/2024,NETFLIX SUBSCRIPTION,186000,0,1000000\n"
        "02/05/2024,02/05/2024,REFUND SHOPEE,0,75000,1075000\n"
    )
    bank, rows, errors = parse_csv(csv_text.encode("utf-8"))
    assert bank == "BRI"
    assert len(rows) == 2
    assert rows[0].amount == 186000.0 and rows[0].type == "debit"
    assert rows[1].type == "credit"


def test_parse_unknown_headers_returns_error():
    csv_text = "foo,bar,baz\n1,2,3\n"
    bank, rows, errors = parse_csv(csv_text.encode("utf-8"))
    assert bank == ""
    assert rows == []
    assert errors and "Could not detect bank" in errors[0]
