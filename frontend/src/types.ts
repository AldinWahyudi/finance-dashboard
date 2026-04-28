export type TxType = "debit" | "credit";

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Transaction {
  id: number;
  date: string; // YYYY-MM-DD
  amount: number;
  type: TxType;
  description: string;
  category: string;
  bank: string | null;
}

export interface CategoryRule {
  id: number;
  keyword: string;
  category: string;
  priority: number;
}

export interface Budget {
  id: number;
  category: string;
  monthly_limit: number;
}

export interface BudgetStatus {
  category: string;
  monthly_limit: number;
  spent: number;
  remaining: number;
  percent_used: number;
  over_budget: boolean;
  month: string;
}

export interface MonthlySpend {
  month: string;
  income: number;
  expense: number;
}

export interface CategoryBreakdown {
  category: string;
  total: number;
}

export interface BalancePoint {
  month: string;
  balance: number;
}

export interface DashboardSummary {
  monthly_spend: MonthlySpend[];
  category_breakdown: CategoryBreakdown[];
  balance_trend: BalancePoint[];
  budget_status: BudgetStatus[];
  total_income: number;
  total_expense: number;
  net: number;
}

export interface ImportResult {
  bank: string;
  inserted: number;
  skipped: number;
  errors: string[];
  transactions: Transaction[];
}
