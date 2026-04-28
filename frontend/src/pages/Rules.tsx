import { useEffect, useState } from "react";
import { api } from "../api";
import type { CategoryRule } from "../types";

export function Rules() {
  const [rules, setRules] = useState<CategoryRule[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setRules(await api.listRules());
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
    if (!keyword.trim() || !category.trim()) return;
    try {
      await api.createRule({ keyword: keyword.trim(), category: category.trim(), priority });
      setKeyword("");
      setCategory("");
      setPriority(0);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Create failed");
    }
  }

  async function update(r: CategoryRule, patch: Partial<CategoryRule>) {
    try {
      await api.updateRule(r.id, patch);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function del(r: CategoryRule) {
    if (!confirm(`Delete rule "${r.keyword}" → ${r.category}?`)) return;
    try {
      await api.deleteRule(r.id);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Category rules</h2>
          <div className="sub">
            Keyword matches in descriptions assign categories. Higher priority runs first.
          </div>
        </div>
      </div>
      {err && <div className="alert danger">{err}</div>}

      <div className="card mb-2">
        <h2>Add rule</h2>
        <form onSubmit={add} className="flex gap-2 wrap" style={{ alignItems: "flex-end" }}>
          <div style={{ minWidth: 200, flex: 1 }}>
            <label>Keyword</label>
            <input value={keyword} onChange={(e) => setKeyword(e.target.value)} required />
          </div>
          <div style={{ minWidth: 180, flex: 1 }}>
            <label>Category</label>
            <input value={category} onChange={(e) => setCategory(e.target.value)} required />
          </div>
          <div style={{ width: 100 }}>
            <label>Priority</label>
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
          </div>
          <button type="submit">Add</button>
        </form>
      </div>

      <div className="card">
        <h2>Your rules</h2>
        {rules.length === 0 ? (
          <div className="muted">No custom rules yet. The built-in defaults still apply.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Keyword</th>
                <th>Category</th>
                <th className="amount">Priority</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>
                    <input
                      className="inline"
                      defaultValue={r.keyword}
                      onBlur={(e) => {
                        if (e.target.value !== r.keyword) update(r, { keyword: e.target.value });
                      }}
                    />
                  </td>
                  <td>
                    <input
                      className="inline"
                      defaultValue={r.category}
                      onBlur={(e) => {
                        if (e.target.value !== r.category) update(r, { category: e.target.value });
                      }}
                    />
                  </td>
                  <td className="amount">
                    <input
                      className="inline"
                      type="number"
                      defaultValue={r.priority}
                      onBlur={(e) => {
                        const v = Number(e.target.value);
                        if (v !== r.priority) update(r, { priority: v });
                      }}
                      style={{ width: 70 }}
                    />
                  </td>
                  <td>
                    <button className="secondary" onClick={() => del(r)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
