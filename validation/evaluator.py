from typing import Any

from validation.budget import validate_budget
from validation.constraints import validate_constraints
from validation.preferences import validate_preferences
from validation.conflicts import detect_conflicts


def evaluate_plan(
    plan: dict[str, Any] | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate a travel plan using deterministic validation.

    Hard constraints determine whether the plan is feasible.
    Preferences are evaluated separately so that a preference
    conflict does not incorrectly make an otherwise feasible
    plan appear invalid.
    """

    # --------------------------------------------------
    # No plan available
    # --------------------------------------------------

    if plan is None:

        conflicts = detect_conflicts(
            None,
            state,
            {},
        )

        return {
            "passed": False,
            "feasible": False,
            "score": 0,

            "budget": {
                "passed": False,
                "message": "No plan available.",
            },

            "constraints": {
                "passed": False,
                "checks": [],
            },

            "preferences": {
                "passed": False,
                "checks": [],
            },

            "conflicts": conflicts,
        }

    # --------------------------------------------------
    # 1. Budget validation
    # --------------------------------------------------

    budget_result = validate_budget(
        plan,
        state.get("budget", 0),
    )

    # --------------------------------------------------
    # 2. Hard constraint validation
    # --------------------------------------------------

    constraint_result = validate_constraints(
        plan,
        state,
    )

    # --------------------------------------------------
    # 3. Preference validation
    # --------------------------------------------------

    preference_result = validate_preferences(
        plan,
        state,
    )

    # --------------------------------------------------
    # Combined validation information
    # --------------------------------------------------

    validation = {
        "budget": budget_result,
        "constraints": constraint_result,
        "preferences": preference_result,
    }

    # --------------------------------------------------
    # 4. Detect conflicts
    # --------------------------------------------------

    conflicts = detect_conflicts(
        plan,
        state,
        validation,
    )

    # --------------------------------------------------
    # 5. Determine feasibility
    #
    # Budget and hard constraints determine whether
    # the plan is feasible.
    #
    # Preferences do not automatically invalidate
    # a feasible plan.
    # --------------------------------------------------

    hard_constraints_passed = (
        budget_result["passed"]
        and constraint_result["passed"]
    )

    # --------------------------------------------------
    # 6. Calculate evaluation score
    # --------------------------------------------------

    score = 100 if hard_constraints_passed else 0

    # Deduct a small amount for preference conflicts.
    # This keeps the plan feasible while making the
    # preference trade-off visible.
    if hard_constraints_passed:

        failed_preferences = sum(
            1
            for check in preference_result.get(
                "checks",
                [],
            )
            if not check.get("passed", True)
        )

        score -= failed_preferences * 10

    score = max(score, 0)

    # --------------------------------------------------
    # 7. Return structured evaluation
    # --------------------------------------------------

    return {
        "passed": hard_constraints_passed,
        "feasible": hard_constraints_passed,
        "score": score,

        "budget": budget_result,

        "constraints": constraint_result,

        "preferences": preference_result,

        "conflicts": conflicts,
    }