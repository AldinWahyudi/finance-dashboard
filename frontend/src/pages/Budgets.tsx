import { useEffect, useState } from "react";
import { api } from "../api";
import type { Budget, BudgetStatus } from "../types";
import { fmtRp } from "../util";

export function Budgets() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [status, setStatus] = useState<BudgetStatus[]>([]);
  const [category, setCategory] = useState("");
  const [limit, setLimit] = useState<number>(0);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      const [bs, st] = await Promise.all([api.listBudgets(), api.budgetsStatus()]);
      setBudgets(bs);
      setStatus(st);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!category.trim() || limit <= 0) return;
    try {
      await api.createBudget({ category: category.trim(), monthly_limit: limit });
      setCategory("");
      setLimit(0);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Create failed");
    }
  }

  async function updateLimit(b: Budget, value: number) {
    if (value === b.monthly_limit || value <= 0) return;
    try {
      await api.updateBudget(b.id, value);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function del(b: Budget) {
    if (!confirm(`Delete budget for "${b.category}"?`)) return;
    try {
      await api.deleteBudget(b.id);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Delete failed");
    }
  }

  const statusMap = new Map(status.map((s) => [s.category, s]));

  return (
    <>
      <h2 style={{ margin: "0 0 1rem" }}>Budgets</h2>
      <p className="muted">
        Set a monthly limit per category. Over-budget categories are flagged on the dashboard.
      </p>
      {err && <div className="alert danger">{err}</div>}

      <div className="card mb-2">
        <h2>Add budget</h2>
        <form onSubmit={add} className="flex gap-2 wrap" style={{ alignItems: "flex-end" }}>
          <div style={{ minWidth: 200, flex: 1 }}>
            <label>Category</label>
            <input value={category} onChange={(e) => setCategory(e.target.value)} required />
          </div>
          <div style={{ minWidth: 160 }}>
            <label>Monthly limit (Rp)</label>
            <input
              type="number"
              value={limit || ""}
              onChange={(e) => setLimit(Number(e.target.value))}
              min={1}
              required
            />
          </div>
          <button type="submit">Add</button>
        </form>
      </div>

      <div className="card">
        <h2>Your budgets</h2>
        {budgets.length === 0 ? (
          <div className="muted">No budgets yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th className="amount">Limit</th>
                <th className="amount">Spent (this month)</th>
                <th className="amount">Remaining</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {budgets.map((b) => {
                const s = statusMap.get(b.category);
                return (
                  <tr key={b.id}>
                    <td>{b.category}</td>
                    <td className="amount">
                      <input
                        className="inline"
                        type="number"
                        defaultValue={b.monthly_limit}
                        onBlur={(e) => updateLimit(b, Number(e.target.value))}
                        style={{ width: 120, textAlign: "right" }}
                      />
                    </td>
                    <td className="amount">{s ? fmtRp(s.spent) : "—"}</td>
                    <td className="amount">{s ? fmtRp(s.remaining) : "—"}</td>
                    <td>
                      {s && (
                        <span
                          className={`badge ${
                            s.over_budget ? "over" : s.percent_used > 80 ? "warn" : "ok"
                          }`}
                        >
                          {s.over_budget
                            ? "Over"
                            : s.percent_used > 80
                              ? "Near"
                              : "OK"}{" "}
                          · {s.percent_used.toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td>
                      <button className="secondary" onClick={() => del(b)}>
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
