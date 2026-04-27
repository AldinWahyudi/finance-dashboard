from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Budget, Transaction, User
from ..schemas import BudgetCreate, BudgetOut, BudgetStatus, BudgetUpdate

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _current_month_spent(db: Session, user_id: int, category: str) -> float:
    today = date.today()
    month_start = today.replace(day=1)
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.category == category,
            Transaction.type == "debit",
            Transaction.date >= month_start,
        )
        .all()
    )
    return float(sum(t.amount for t in rows))


def _budget_status(b: Budget, spent: float) -> BudgetStatus:
    limit = float(b.monthly_limit)
    remaining = limit - spent
    percent = (spent / limit * 100.0) if limit > 0 else 0.0
    return BudgetStatus(
        category=b.category,
        monthly_limit=limit,
        spent=spent,
        remaining=remaining,
        percent_used=round(percent, 2),
        over_budget=spent > limit,
        month=date.today().strftime("%Y-%m"),
    )


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[BudgetOut]:
    budgets = db.query(Budget).filter(Budget.user_id == user.id).order_by(Budget.category).all()
    return [BudgetOut.model_validate(b) for b in budgets]


@router.get("/status", response_model=list[BudgetStatus])
def budgets_status(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[BudgetStatus]:
    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()
    out: list[BudgetStatus] = []
    for b in budgets:
        spent = _current_month_spent(db, user.id, b.category)
        out.append(_budget_status(b, spent))
    out.sort(key=lambda s: (-s.percent_used, s.category))
    return out


@router.post("", response_model=BudgetOut, status_code=201)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetOut:
    existing = (
        db.query(Budget)
        .filter(Budget.user_id == user.id, Budget.category == payload.category)
        .first()
    )
    if existing:
        raise HTTPException(409, f"Budget for category '{payload.category}' already exists")
    b = Budget(user_id=user.id, category=payload.category, monthly_limit=payload.monthly_limit)
    db.add(b)
    db.commit()
    db.refresh(b)
    return BudgetOut.model_validate(b)


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetOut:
    b = db.query(Budget).filter(and_(Budget.id == budget_id, Budget.user_id == user.id)).first()
    if not b:
        raise HTTPException(404, "Budget not found")
    if payload.monthly_limit is not None:
        b.monthly_limit = payload.monthly_limit
    db.commit()
    db.refresh(b)
    return BudgetOut.model_validate(b)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    b = db.query(Budget).filter(and_(Budget.id == budget_id, Budget.user_id == user.id)).first()
    if not b:
        raise HTTPException(404, "Budget not found")
    db.delete(b)
    db.commit()
