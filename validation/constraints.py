from typing import Any


def validate_constraints(
    plan: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate the hard constraints of a travel plan.
    """

    checks = []

    # -----------------------------------------------
    # Budget constraint
    # -----------------------------------------------

    budget = float(state.get("budget", 0))
    total_cost = float(plan.get("total_cost", 0))

    budget_passed = total_cost <= budget

    checks.append(
        {
            "constraint": "budget",
            "passed": budget_passed,
            "message": (
                "Plan is within budget."
                if budget_passed
                else "Plan exceeds the user's budget."
            ),
        }
    )

    # -----------------------------------------------
    # Traveller constraint
    # -----------------------------------------------

    travellers = int(
        state.get("travellers", 0)
    )

    traveller_passed = travellers >= 1

    checks.append(
        {
            "constraint": "travellers",
            "passed": traveller_passed,
            "message": (
                "Valid number of travellers."
                if traveller_passed
                else "At least one traveller is required."
            ),
        }
    )

    # -----------------------------------------------
    # Overall result
    # -----------------------------------------------

    passed = all(
        check["passed"]
        for check in checks
    )

    return {
        "passed": passed,
        "checks": checks,
    }