"""Keyword-based auto-categorization."""

from __future__ import annotations

from ..models import CategoryRule

DEFAULT_RULES: list[tuple[str, str]] = [
    # (keyword, category) — lowercase keywords
    ("gofood", "Food & Drink"),
    ("grabfood", "Food & Drink"),
    ("shopeefood", "Food & Drink"),
    ("starbucks", "Food & Drink"),
    ("kopi", "Food & Drink"),
    ("resto", "Food & Drink"),
    ("restaurant", "Food & Drink"),
    ("warung", "Food & Drink"),
    ("mcd", "Food & Drink"),
    ("kfc", "Food & Drink"),
    ("indomaret", "Groceries"),
    ("alfamart", "Groceries"),
    ("alfamidi", "Groceries"),
    ("superindo", "Groceries"),
    ("hypermart", "Groceries"),
    ("transmart", "Groceries"),
    ("shopee", "Shopping"),
    ("tokopedia", "Shopping"),
    ("lazada", "Shopping"),
    ("blibli", "Shopping"),
    ("bukalapak", "Shopping"),
    ("grab", "Transport"),
    ("gojek", "Transport"),
    ("gopay", "Transport"),
    ("maxim", "Transport"),
    ("bluebird", "Transport"),
    ("pertamina", "Transport"),
    ("shell", "Transport"),
    ("transjakarta", "Transport"),
    ("krl", "Transport"),
    ("mrt", "Transport"),
    ("netflix", "Entertainment"),
    ("spotify", "Entertainment"),
    ("disney", "Entertainment"),
    ("youtube", "Entertainment"),
    ("steam", "Entertainment"),
    ("pln", "Utilities"),
    ("listrik", "Utilities"),
    ("pdam", "Utilities"),
    ("telkom", "Utilities"),
    ("indihome", "Utilities"),
    ("pulsa", "Utilities"),
    ("bpjs", "Health"),
    ("apotek", "Health"),
    ("rumah sakit", "Health"),
    ("klinik", "Health"),
    ("gaji", "Income"),
    ("salary", "Income"),
    ("payroll", "Income"),
    ("transfer masuk", "Income"),
    ("biaya admin", "Fees"),
    ("admin", "Fees"),
    ("pajak", "Fees"),
    ("bunga", "Income"),
]


def categorize(description: str, rules: list[CategoryRule]) -> str:
    """Return the best-match category for a description, or 'Uncategorized'.

    User-defined rules (sorted by priority desc, then id asc) are checked first.
    Falls back to the built-in defaults if no user rule matches.
    """
    if not description:
        return "Uncategorized"
    desc = description.lower()

    sorted_rules = sorted(rules, key=lambda r: (-(r.priority or 0), r.id or 0))
    for rule in sorted_rules:
        kw = (rule.keyword or "").lower().strip()
        if kw and kw in desc:
            return rule.category
    for kw, category in DEFAULT_RULES:
        if kw in desc:
            return category
    return "Uncategorized"
