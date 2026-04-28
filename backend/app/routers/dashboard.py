from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Budget, Transaction, User
from ..schemas import (
    BalancePoint,
    BudgetStatus,
    CategoryBreakdown,
    DashboardSummary,
    MonthlySpend,
)
from .budgets import _budget_status, _current_month_spent

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _ym(d: date) -> str:
    return d.strftime("%Y-%m")


def _build_summary(db: Session, user: User) -> DashboardSummary:
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.date.asc())
        .all()
    )

    monthly_income: dict[str, float] = defaultdict(float)
    monthly_expense: dict[str, float] = defaultdict(float)
    category_totals: dict[str, float] = defaultdict(float)
    total_income = 0.0
    total_expense = 0.0

    for t in txs:
        month = _ym(t.date)
        if t.type == "credit":
            monthly_income[month] += t.amount
            total_income += t.amount
        else:
            monthly_expense[month] += t.amount
            category_totals[t.category or "Uncategorized"] += t.amount
            total_expense += t.amount

    months = sorted(set(list(monthly_income.keys()) + list(monthly_expense.keys())))
    monthly_spend = [
        MonthlySpend(
            month=m,
            income=round(monthly_income.get(m, 0.0), 2),
            expense=round(monthly_expense.get(m, 0.0), 2),
        )
        for m in months
    ]

    category_breakdown = [
        CategoryBreakdown(category=c, total=round(v, 2))
        for c, v in sorted(category_totals.items(), key=lambda x: -x[1])
    ]

    balance = 0.0
    balance_trend: list[BalancePoint] = []
    for m in months:
        balance += monthly_income.get(m, 0.0) - monthly_expense.get(m, 0.0)
        balance_trend.append(BalancePoint(month=m, balance=round(balance, 2)))

    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()
    budget_status: list[BudgetStatus] = []
    for b in budgets:
        spent = _current_month_spent(db, user.id, b.category)
        budget_status.append(_budget_status(b, spent))
    budget_status.sort(key=lambda s: (-s.percent_used, s.category))

    return DashboardSummary(
        monthly_spend=monthly_spend,
        category_breakdown=category_breakdown,
        balance_trend=balance_trend,
        budget_status=budget_status,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        net=round(total_income - total_expense, 2),
    )


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DashboardSummary:
    return _build_summary(db, user)
