from typing import Any


def generate_plan_explanation(
    selected_plan: dict[str, Any],
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[str]:
    """
    Generate concise, deterministic explanations for why
    the selected travel plan was chosen.

    This does NOT expose LLM chain-of-thought.
    """

    explanations = []

    budget = float(
        state.get("budget", 0)
    )

    total_cost = float(
        selected_plan.get(
            "total_cost",
            0,
        )
    )

    remaining = budget - total_cost

    plan_name = selected_plan.get(
        "name",
        "Selected plan",
    )

    # --------------------------------------------------
    # Selected plan
    # --------------------------------------------------

    explanations.append(
        f"{plan_name} was selected as the highest-scoring "
        "feasible plan."
    )

    # --------------------------------------------------
    # Budget
    # --------------------------------------------------

    if total_cost <= budget:

        explanations.append(
            f"The plan costs £{total_cost:.2f}, "
            f"leaving £{remaining:.2f} within your "
            f"£{budget:.2f} budget."
        )

    # --------------------------------------------------
    # Budget priority
    # --------------------------------------------------

    budget_priority = (
        state.get("priorities", {})
        .get("budget", "MEDIUM")
    )

    if budget_priority == "HIGH":

        explanations.append(
            "Budget was given HIGH priority, so "
            "cost efficiency had a strong influence "
            "on the selection."
        )

    elif budget_priority == "MEDIUM":

        explanations.append(
            "Budget was given MEDIUM priority and "
            "was considered alongside other factors."
        )

    # --------------------------------------------------
    # Vegetarian preference
    # --------------------------------------------------

    preferences = str(
        state.get(
            "preferences",
            "",
        )
    ).lower()

    if "vegetarian" in preferences:

        vegetarian_score = selected_plan.get(
            "vegetarian_score"
        )

        if vegetarian_score is not None:

            explanations.append(
                f"The plan's vegetarian preference "
                f"score was "
                f"{float(vegetarian_score) * 100:.0f}%."
            )

        else:

            explanations.append(
                "Vegetarian preference was considered "
                "during plan evaluation."
            )

    # --------------------------------------------------
    # Museum preference
    # --------------------------------------------------

    if "museum" in preferences:

        museum_score = selected_plan.get(
            "museum_score"
        )

        if museum_score is not None:

            explanations.append(
                f"The plan's museum preference "
                f"score was "
                f"{float(museum_score) * 100:.0f}%."
            )

        else:

            explanations.append(
                "Museum preference was considered "
                "during plan evaluation."
            )

    # --------------------------------------------------
    # Hotel quality
    # --------------------------------------------------

    hotel = selected_plan.get(
        "hotel",
        {}
    )

    hotel_rating = hotel.get(
        "rating"
    )

    if hotel_rating:

        explanations.append(
            f"The selected accommodation has a "
            f"{float(hotel_rating):.1f}/5 rating."
        )

    # --------------------------------------------------
    # Route
    # --------------------------------------------------

    itinerary = selected_plan.get(
        "daily_itinerary",
        []
    )

    if itinerary:

        total_travel_hours = sum(
            float(
                day.get(
                    "travel_hours",
                    0,
                )
                or 0
            )
            for day in itinerary
        )

        explanations.append(
            f"The itinerary uses geographic route "
            f"optimisation with approximately "
            f"{total_travel_hours:.2f} hours of "
            f"estimated travel time."
        )

    # --------------------------------------------------
    # Rejected alternatives
    # --------------------------------------------------

    for candidate in candidates:

        candidate_name = candidate.get(
            "name",
            "Alternative",
        )

        candidate_cost = float(
            candidate.get(
                "total_cost",
                0,
            )
        )

        if (
            candidate_name != plan_name
            and candidate_cost > budget
        ):

            exceeded_by = (
                candidate_cost - budget
            )

            explanations.append(
                f"{candidate_name} was not feasible "
                f"because it exceeded the budget by "
                f"£{exceeded_by:.2f}."
            )

    # --------------------------------------------------
    # Final score
    # --------------------------------------------------

    score = selected_plan.get(
        "score"
    )

    if score is not None:

        explanations.append(
            f"Final deterministic planning score: "
            f"{float(score):.2f}/100."
        )

    return explanations