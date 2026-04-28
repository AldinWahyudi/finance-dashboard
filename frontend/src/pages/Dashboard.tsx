import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import type { DashboardSummary, Transaction } from "../types";
import { fmtRp, fmtRpShort } from "../util";

const COLOR_INCOME = "#34d399";
const COLOR_EXPENSE = "#f472b6";
const COLOR_BALANCE = "#a78bfa";
const COLOR_WARN = "#fbbf24";
const GRID = "#2e2e3e";
const AXIS = "#5e5e6e";
const CARD = "#1c1c25";

const CATEGORY_PALETTE = [
  "#a78bfa",
  "#f472b6",
  "#34d399",
  "#fbbf24",
  "#60a5fa",
  "#fb7185",
  "#22d3ee",
  "#c084fc",
  "#f59e0b",
  "#4ade80",
];

const TOOLTIP_STYLE: React.CSSProperties = {
  background: CARD,
  border: `1px solid ${GRID}`,
  borderRadius: 10,
  fontSize: 12,
  color: "#ececf1",
  padding: "8px 10px",
};

export function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api.dashboardSummary().then(setData).catch((e) => setErr(e.message));
    api
      .listTransactions()
      .then((rows) => setRecent(rows.slice(0, 6)))
      .catch(() => setRecent([]));
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
  const trend = data.balance_trend.slice(-6);
  const categories = [...data.category_breakdown].sort(
    (a, b) => b.total - a.total,
  );
  const totalExpense = categories.reduce((s, c) => s + c.total, 0);

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Dashboard</h2>
          <div className="sub">Overview of your finances this period.</div>
        </div>
        <button onClick={downloadPdf} disabled={downloading}>
          {downloading ? "Generating PDF…" : "Export PDF"}
        </button>
      </div>

      {overBudget.length > 0 && (
        <div className="alert danger">
          <span>
            <strong>Over budget this month:</strong>{" "}
            {overBudget
              .map(
                (b) =>
                  `${b.category} (${fmtRp(b.spent)} / ${fmtRp(b.monthly_limit)})`,
              )
              .join(" · ")}
          </span>
        </div>
      )}

      <div className="stat-grid">
        <div className="card stat income">
          <div className="flex between center">
            <span className="label">Income</span>
            <span className="pill">In</span>
          </div>
          <div className="value">{fmtRp(data.total_income)}</div>
          <div className="delta">{data.monthly_spend.length} month{data.monthly_spend.length === 1 ? "" : "s"} tracked</div>
        </div>
        <div className="card stat expense">
          <div className="flex between center">
            <span className="label">Expense</span>
            <span className="pill">Out</span>
          </div>
          <div className="value">{fmtRp(data.total_expense)}</div>
          <div className="delta">across {categories.length} categor{categories.length === 1 ? "y" : "ies"}</div>
        </div>
        <div className="card stat balance">
          <div className="flex between center">
            <span className="label">Balance</span>
            <span className="pill">Net</span>
          </div>
          <div className="value">{fmtRp(data.net)}</div>
          <div className="delta">{data.net >= 0 ? "Net positive" : "Net negative"}</div>
        </div>
      </div>

      <div className="split-grid">
        <div className="card">
          <div className="card-head">
            <h2>Spend by category</h2>
            <span className="muted-sm">{fmtRp(totalExpense)}</span>
          </div>
          {categories.length === 0 ? (
            <div className="muted">No expenses yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={categories}
                layout="vertical"
                margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
              >
                <CartesianGrid stroke={GRID} horizontal={false} />
                <XAxis
                  type="number"
                  stroke={AXIS}
                  tickFormatter={fmtRpShort}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="category"
                  stroke={AXIS}
                  tick={{ fontSize: 11 }}
                  width={110}
                />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                  formatter={(v) => fmtRp(Number(v))}
                />
                <Bar dataKey="total" radius={[0, 6, 6, 0]}>
                  {categories.map((_, i) => (
                    <Cell
                      key={i}
                      fill={CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h2>6-month balance trend</h2>
            <span className="muted-sm">{fmtRp(data.net)}</span>
          </div>
          {trend.length === 0 ? (
            <div className="muted">No data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={trend}
                margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
              >
                <defs>
                  <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={COLOR_BALANCE} stopOpacity={0.6} />
                    <stop offset="100%" stopColor={COLOR_BALANCE} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis
                  dataKey="month"
                  stroke={AXIS}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={AXIS}
                  tickFormatter={fmtRpShort}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(v) => fmtRp(Number(v))}
                />
                <Line
                  type="monotone"
                  dataKey="balance"
                  stroke={COLOR_BALANCE}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: COLOR_BALANCE, strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: COLOR_BALANCE }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="split-grid">
        <div className="card">
          <div className="card-head">
            <h2>Recent transactions</h2>
            <a href="/transactions" className="muted-sm">View all →</a>
          </div>
          {recent.length === 0 ? (
            <div className="muted">No transactions yet.</div>
          ) : (
            <div>
              {recent.map((t) => (
                <div key={t.id} className="tx-row">
                  <div>
                    <div className="desc">{t.description}</div>
                    <div className="meta">
                      {t.date} · {t.category} · {t.bank ?? "Manual"}
                    </div>
                  </div>
                  <div className={`amount ${t.type}`}>
                    {t.type === "credit" ? "+" : "−"}
                    {fmtRp(t.amount)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h2>Budgets · this month</h2>
            <a href="/budgets" className="muted-sm">Manage →</a>
          </div>
          {data.budget_status.length === 0 ? (
            <div className="muted">
              No budgets yet. Add one in the Budgets tab.
            </div>
          ) : (
            <div>
              {data.budget_status.map((b) => {
                const pct = Math.min(100, Math.round(b.percent_used));
                const status = b.over_budget
                  ? "over"
                  : pct > 80
                    ? "warn"
                    : "ok";
                const barColor =
                  status === "over"
                    ? COLOR_EXPENSE
                    : status === "warn"
                      ? COLOR_WARN
                      : COLOR_INCOME;
                return (
                  <div key={b.category} className="budget-row">
                    <div className="name">{b.category}</div>
                    <div className="nums">
                      {fmtRp(b.spent)} / {fmtRp(b.monthly_limit)}
                    </div>
                    <div className="bar">
                      <div className={`progress ${status}`}>
                        <div
                          style={{
                            width: `${pct}%`,
                            background: barColor,
                          }}
                        />
                      </div>
                    </div>
                    <div className="meta">
                      <span className={`badge ${status}`}>
                        {b.over_budget ? "Over" : pct > 80 ? "Near" : "On track"}
                      </span>
                      <span className={`pct ${status}`}>
                        {b.percent_used.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
