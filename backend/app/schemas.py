import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    created_at: dt.datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TransactionBase(BaseModel):
    date: dt.date
    amount: float
    type: Literal["debit", "credit"]
    description: str = ""
    category: str = "Uncategorized"
    bank: str | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: dt.date | None = None
    amount: float | None = None
    type: Literal["debit", "credit"] | None = None
    description: str | None = None
    category: str | None = None


class TransactionOut(TransactionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ImportResult(BaseModel):
    bank: str
    inserted: int
    skipped: int
    errors: list[str] = []
    transactions: list[TransactionOut] = []


class CategoryRuleBase(BaseModel):
    keyword: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    priority: int = 0


class CategoryRuleCreate(CategoryRuleBase):
    pass


class CategoryRuleUpdate(BaseModel):
    keyword: str | None = None
    category: str | None = None
    priority: int | None = None


class CategoryRuleOut(CategoryRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BudgetBase(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    monthly_limit: float = Field(gt=0)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    monthly_limit: float | None = Field(default=None, gt=0)


class BudgetOut(BudgetBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BudgetStatus(BaseModel):
    category: str
    monthly_limit: float
    spent: float
    remaining: float
    percent_used: float
    over_budget: bool
    month: str  # YYYY-MM


class MonthlySpend(BaseModel):
    month: str  # YYYY-MM
    income: float
    expense: float


class CategoryBreakdown(BaseModel):
    category: str
    total: float


class BalancePoint(BaseModel):
    month: str
    balance: float


class DashboardSummary(BaseModel):
    monthly_spend: list[MonthlySpend]
    category_breakdown: list[CategoryBreakdown]
    balance_trend: list[BalancePoint]
    budget_status: list[BudgetStatus]
    total_income: float
    total_expense: float
    net: float
