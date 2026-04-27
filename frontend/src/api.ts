import type {
  Budget,
  BudgetStatus,
  CategoryRule,
  DashboardSummary,
  ImportResult,
  Transaction,
  User,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseError(text) ?? `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function parseError(text: string): string | null {
  try {
    const j = JSON.parse(text);
    if (typeof j?.detail === "string") return j.detail;
    if (Array.isArray(j?.detail)) return j.detail.map((d: { msg?: string }) => d.msg).join("; ");
  } catch {
    // fallthrough
  }
  return text || null;
}

export const api = {
  async signup(email: string, password: string) {
    return request<{ access_token: string; user: User }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async login(email: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) throw new Error(parseError(await res.text()) ?? "Login failed");
    return (await res.json()) as { access_token: string; user: User };
  },

  async me() {
    return request<User>("/api/auth/me");
  },

  async listTransactions(params: { start?: string; end?: string; category?: string } = {}) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) q.append(k, v);
    });
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return request<Transaction[]>(`/api/transactions${suffix}`);
  },

  async createTransaction(payload: Omit<Transaction, "id">) {
    return request<Transaction>("/api/transactions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateTransaction(id: number, payload: Partial<Transaction>) {
    return request<Transaction>(`/api/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async deleteTransaction(id: number) {
    return request<void>(`/api/transactions/${id}`, { method: "DELETE" });
  },

  async importCsv(file: File, bank?: string) {
    const form = new FormData();
    form.append("file", file);
    if (bank) form.append("bank", bank);
    const res = await fetch(`${API_BASE}/api/transactions/import`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    if (!res.ok) throw new Error(parseError(await res.text()) ?? "Import failed");
    return (await res.json()) as ImportResult;
  },

  async recategorize() {
    return request<{ updated: number; scanned: number }>("/api/transactions/recategorize", {
      method: "POST",
    });
  },

  async listRules() {
    return request<CategoryRule[]>("/api/rules");
  },

  async createRule(payload: Omit<CategoryRule, "id">) {
    return request<CategoryRule>("/api/rules", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateRule(id: number, payload: Partial<CategoryRule>) {
    return request<CategoryRule>(`/api/rules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async deleteRule(id: number) {
    return request<void>(`/api/rules/${id}`, { method: "DELETE" });
  },

  async listBudgets() {
    return request<Budget[]>("/api/budgets");
  },

  async budgetsStatus() {
    return request<BudgetStatus[]>("/api/budgets/status");
  },

  async createBudget(payload: Omit<Budget, "id">) {
    return request<Budget>("/api/budgets", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateBudget(id: number, monthly_limit: number) {
    return request<Budget>(`/api/budgets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ monthly_limit }),
    });
  },

  async deleteBudget(id: number) {
    return request<void>(`/api/budgets/${id}`, { method: "DELETE" });
  },

  async dashboardSummary() {
    return request<DashboardSummary>("/api/dashboard/summary");
  },

  exportPdfUrl() {
    return `${API_BASE}/api/export/pdf`;
  },

  async exportPdf() {
    const res = await fetch(`${API_BASE}/api/export/pdf`, { headers: authHeaders() });
    if (!res.ok) throw new Error("Failed to export PDF");
    return await res.blob();
  },
};
