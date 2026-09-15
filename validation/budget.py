from typing import Any


def validate_budget(
    plan: dict[str, Any],
    budget: float,
) -> dict[str, Any]:
    """
    Deterministically validate the plan's budget.
    """

    total_cost = float(
        plan.get("total_cost", 0)
    )

    budget = float(budget)

    difference = budget - total_cost

    if total_cost <= budget:
        return {
            "passed": True,
            "budget": budget,
            "total_cost": total_cost,
            "remaining": round(difference, 2),
            "exceeded_by": 0,
            "message": (
                f"Plan is within budget. "
                f"£{round(difference, 2)} remaining."
            ),
        }

    return {
        "passed": False,
        "budget": budget,
        "total_cost": total_cost,
        "remaining": 0,
        "exceeded_by": round(
            abs(difference),
            2,
        ),
        "message": (
            f"Plan exceeds the budget by "
            f"£{round(abs(difference), 2)}."
        ),
    }