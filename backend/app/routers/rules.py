from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import CategoryRule, User
from ..schemas import CategoryRuleCreate, CategoryRuleOut, CategoryRuleUpdate

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[CategoryRuleOut])
def list_rules(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CategoryRuleOut]:
    rules = (
        db.query(CategoryRule)
        .filter(CategoryRule.user_id == user.id)
        .order_by(CategoryRule.priority.desc(), CategoryRule.id.asc())
        .all()
    )
    return [CategoryRuleOut.model_validate(r) for r in rules]


@router.post("", response_model=CategoryRuleOut, status_code=201)
def create_rule(
    payload: CategoryRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CategoryRuleOut:
    rule = CategoryRule(
        user_id=user.id,
        keyword=payload.keyword.strip(),
        category=payload.category.strip(),
        priority=payload.priority,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return CategoryRuleOut.model_validate(rule)


@router.patch("/{rule_id}", response_model=CategoryRuleOut)
def update_rule(
    rule_id: int,
    payload: CategoryRuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CategoryRuleOut:
    rule = (
        db.query(CategoryRule)
        .filter(and_(CategoryRule.id == rule_id, CategoryRule.user_id == user.id))
        .first()
    )
    if not rule:
        raise HTTPException(404, "Rule not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(rule, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    db.refresh(rule)
    return CategoryRuleOut.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    rule = (
        db.query(CategoryRule)
        .filter(and_(CategoryRule.id == rule_id, CategoryRule.user_id == user.id))
        .first()
    )
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()
