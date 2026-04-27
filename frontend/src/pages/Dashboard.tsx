import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import type { DashboardSummary } from "../types";
import { fmtRp, fmtRpShort } from "../util";

const PIE_COLORS = [
  "#0ea5e9",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#a855f7",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#6366f1",
  "#eab308",
];

export function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api.dashboardSummary().then(setData).catch((e) => setErr(e.message));
  }, []);

  async function downloadPdf() {
    setDownloading(true);
    try {
      const blob = await api.exportPdf();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "finance-dashboard.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  if (err) return <div className="alert danger">{err}</div>;
  if (!data) return <div className="muted">Loading dashboard…</div>;

  const overBudget = data.budget_status.filter((b) => b.over_budget);

  return (
    <>
      <div className="flex between mb-2 wrap gap-2">
        <h2 style={{ margin: 0 }}>Dashboard</h2>
        <button onClick={downloadPdf} disabled={downloading}>
          {downloading ? "Generating PDF…" : "Export PDF"}
        </button>
      </div>

      {overBudget.length > 0 && (
        <div className="alert danger">
          <strong>Over budget this month:</strong>{" "}
          {overBudget
            .map((b) => `${b.category} (${fmtRp(b.spent)} / ${fmtRp(b.monthly_limit)})`)
            .join("; ")}
        </div>
      )}

      <div className="kpi-grid">
        <div className="card kpi income">
          <div className="label">Total income</div>
          <div className="value">{fmtRp(data.total_income)}</div>
        </div>
        <div className="card kpi expense">
          <div className="label">Total expense</div>
          <div className="value">{fmtRp(data.total_expense)}</div>
        </div>
        <div className="card kpi">
          <div className="label">Net</div>
          <div className="value" style={{ color: data.net >= 0 ? "var(--success)" : "var(--danger)" }}>
            {fmtRp(data.net)}
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Months tracked</div>
          <div className="value">{data.monthly_spend.length}</div>
        </div>
      </div>

      <div className="chart-grid mb-2">
        <div className="card">
          <h2>Monthly income vs. expense</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.monthly_spend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" tickFormatter={fmtRpShort} />
              <Tooltip
                formatter={(value) => fmtRp(Number(value))}
                contentStyle={{ background: "#111c33", border: "1px solid #334155" }}
              />
              <Legend />
              <Bar dataKey="income" fill="#22c55e" name="Income" />
              <Bar dataKey="expense" fill="#ef4444" name="Expense" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2>Category breakdown</h2>
          {data.category_breakdown.length === 0 ? (
            <div className="muted">No expenses yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={data.category_breakdown}
                  dataKey="total"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={(entry) => entry.category}
                >
                  {data.category_breakdown.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => fmtRp(Number(value))}
                  contentStyle={{ background: "#111c33", border: "1px solid #334155" }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card mb-2">
        <h2>Monthly balance trend</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.balance_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="month" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" tickFormatter={fmtRpShort} />
            <Tooltip
              formatter={(value) => fmtRp(Number(value))}
              contentStyle={{ background: "#111c33", border: "1px solid #334155" }}
            />
            <Line type="monotone" dataKey="balance" stroke="#0ea5e9" strokeWidth={2} dot />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2>Budgets (current month)</h2>
        {data.budget_status.length === 0 ? (
          <div className="muted">No budgets yet. Add one in the Budgets tab.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th className="amount">Limit</th>
                <th className="amount">Spent</th>
                <th className="amount">Remaining</th>
                <th style={{ width: 160 }}>Progress</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.budget_status.map((b) => {
                const pct = Math.min(100, Math.round(b.percent_used));
                const cls = b.over_budget ? "over" : pct > 80 ? "warn" : "";
                return (
                  <tr key={b.category}>
                    <td>{b.category}</td>
                    <td className="amount">{fmtRp(b.monthly_limit)}</td>
                    <td className="amount">{fmtRp(b.spent)}</td>
                    <td className="amount">{fmtRp(b.remaining)}</td>
                    <td>
                      <div className={`progress ${cls}`}>
                        <div style={{ width: `${pct}%` }} />
                      </div>
                      <div className="muted" style={{ fontSize: "0.75rem" }}>{b.percent_used.toFixed(1)}%</div>
                    </td>
                    <td>
                      <span className={`badge ${b.over_budget ? "over" : pct > 80 ? "warn" : "ok"}`}>
                        {b.over_budget ? "Over" : pct > 80 ? "Near" : "OK"}
                      </span>
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
