from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import Budget, Transaction


def month_start(d: date) -> date:
    return d.replace(day=1)


def spend_by_category(user, month: date):
    """Total spend per category for the given month. Only positive amounts
    (debits) count as spend; refunds/income don't count against a budget."""
    start = month_start(month)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    rows = (
        Transaction.objects.filter(
            user=user, date__gte=start, date__lt=end, amount__gt=0
        )
        .values("category_id")
        .annotate(total=Sum("amount"))
    )
    return {row["category_id"]: row["total"] for row in rows}


def budget_vs_actual(user, month: date):
    """One row per budget the user has set for this month: limit, actual
    spend, remaining, and whether they're over."""
    start = month_start(month)
    spend = spend_by_category(user, start)
    budgets = Budget.objects.filter(user=user, month=start).select_related("category")

    results = []
    for budget in budgets:
        actual = spend.get(budget.category_id, Decimal("0"))
        remaining = budget.limit_amount - actual
        results.append(
            {
                "category_id": budget.category_id,
                "category_name": budget.category.name,
                "limit_amount": budget.limit_amount,
                "actual_spend": actual,
                "remaining": remaining,
                "over_budget": remaining < 0,
            }
        )
    return results