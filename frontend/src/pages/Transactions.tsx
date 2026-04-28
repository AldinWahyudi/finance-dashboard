import { useEffect, useState } from "react";
import { api } from "../api";
import type { Transaction } from "../types";
import { fmtRp } from "../util";

export function Transactions() {
  const [rows, setRows] = useState<Transaction[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<Record<number, string>>({});

  async function load() {
    try {
      setRows(await api.listTransactions());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function save(tx: Transaction) {
    const next = editing[tx.id];
    if (next == null || next === tx.category) {
      setEditing((m) => {
        const copy = { ...m };
        delete copy[tx.id];
        return copy;
      });
      return;
    }
    try {
      const updated = await api.updateTransaction(tx.id, { category: next });
      setRows((prev) => prev.map((r) => (r.id === tx.id ? updated : r)));
      setEditing((m) => {
        const copy = { ...m };
        delete copy[tx.id];
        return copy;
      });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function recategorize() {
    setErr(null);
    try {
      const r = await api.recategorize();
      await load();
      alert(`Recategorized ${r.updated} of ${r.scanned} uncategorized transactions.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Recategorize failed");
    }
  }

  async function del(tx: Transaction) {
    if (!confirm(`Delete "${tx.description}"?`)) return;
    try {
      await api.deleteTransaction(tx.id);
      setRows((prev) => prev.filter((r) => r.id !== tx.id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Transactions</h2>
          <div className="sub">All imported and manually-added transactions.</div>
        </div>
        <button className="secondary" onClick={recategorize}>
          Re-run auto-categorization
        </button>
      </div>
      {err && <div className="alert danger">{err}</div>}
      <div className="card">
        {rows.length === 0 ? (
          <div className="muted">
            No transactions yet. Upload a CSV on the <a href="/import">Import</a> page.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Bank</th>
                <th>Category</th>
                <th>Type</th>
                <th className="amount">Amount</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((tx) => {
                const editVal = editing[tx.id];
                return (
                  <tr key={tx.id}>
                    <td>{tx.date}</td>
                    <td>{tx.description}</td>
                    <td>{tx.bank ?? "—"}</td>
                    <td>
                      {editVal !== undefined ? (
                        <input
                          className="inline"
                          autoFocus
                          value={editVal}
                          onChange={(e) =>
                            setEditing((m) => ({ ...m, [tx.id]: e.target.value }))
                          }
                          onBlur={() => save(tx)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") save(tx);
                            if (e.key === "Escape")
                              setEditing((m) => {
                                const copy = { ...m };
                                delete copy[tx.id];
                                return copy;
                              });
                          }}
                        />
                      ) : (
                        <span
                          onClick={() => setEditing((m) => ({ ...m, [tx.id]: tx.category }))}
                          style={{ cursor: "pointer", textDecoration: "underline dotted" }}
                          title="Click to edit"
                        >
                          {tx.category}
                        </span>
                      )}
                    </td>
                    <td className={tx.type === "credit" ? "credit" : "debit"}>{tx.type}</td>
                    <td className={`amount ${tx.type === "credit" ? "credit" : "debit"}`}>
                      {tx.type === "credit" ? "+" : "-"}
                      {fmtRp(tx.amount)}
                    </td>
                    <td>
                      <button className="secondary" onClick={() => del(tx)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
