from typing import Any


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def priority_weight(priority: str) -> float:
    weights = {
        "HIGH": 4.0,
        "MEDIUM": 2.0,
        "LOW": 0.5,
    }

    return weights.get(
        str(priority).upper(),
        1.0,
    )


# ============================================================
# BUDGET SCORE
# ============================================================

def calculate_budget_score(
    plan: dict[str, Any],
    budget: float,
) -> float:

    total_cost = safe_float(
        plan.get("total_cost", 0)
    )

    if budget <= 0:
        return 0.0

    if total_cost > budget:
        return 0.0

    remaining = budget - total_cost

    return clamp(
        remaining / budget
    )


# ============================================================
# FOOD PREFERENCE
# ============================================================

def _normalise_food_preference(
    state: dict[str, Any],
) -> str:

    explicit = str(
        state.get(
            "food_preference",
            "",
        )
    ).strip().lower()

    if explicit:

        if "non-vegetarian" in explicit:
            return "non-vegetarian"

        if "non vegetarian" in explicit:
            return "non-vegetarian"

        if "vegan" in explicit:
            return "vegan"

        if "vegetarian" in explicit:
            return "vegetarian"

        if "no food" in explicit:
            return "no food preference"

    preferences = str(
        state.get(
            "preferences",
            "",
        )
    ).lower()

    if "non-vegetarian" in preferences:
        return "non-vegetarian"

    if "non vegetarian" in preferences:
        return "non-vegetarian"

    if "vegan" in preferences:
        return "vegan"

    if "vegetarian" in preferences:
        return "vegetarian"

    return "no food preference"


# ============================================================
# FOOD SCORE
# ============================================================

def calculate_food_score(
    plan: dict[str, Any],
    state: dict[str, Any],
) -> float:

    restaurants = plan.get(
        "restaurants",
        [],
    )

    if not restaurants:
        return 0.5

    preference = _normalise_food_preference(
        state
    )

    # --------------------------------------------------------
    # No preference
    # --------------------------------------------------------

    if preference == "no food preference":
        return 1.0

    # --------------------------------------------------------
    # Vegetarian
    # --------------------------------------------------------

    if preference == "vegetarian":

        matches = sum(
            1
            for restaurant in restaurants
            if (
                restaurant.get(
                    "vegetarian",
                    False,
                )
                or
                "vegetarian"
                in str(
                    restaurant.get(
                        "cuisine",
                        "",
                    )
                ).lower()
            )
        )

        return clamp(
            matches / len(restaurants)
        )

    # --------------------------------------------------------
    # Vegan
    # --------------------------------------------------------

    if preference == "vegan":

        matches = sum(
            1
            for restaurant in restaurants
            if (
                restaurant.get(
                    "vegan",
                    False,
                )
                or
                "vegan"
                in str(
                    restaurant.get(
                        "cuisine",
                        "",
                    )
                ).lower()
            )
        )

        return clamp(
            matches / len(restaurants)
        )

    # --------------------------------------------------------
    # Non-Vegetarian
    # --------------------------------------------------------

    if preference == "non-vegetarian":

        matches = sum(
            1
            for restaurant in restaurants
            if not restaurant.get(
                "vegetarian",
                False,
            )
        )

        return clamp(
            matches / len(restaurants)
        )

    return 1.0


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def calculate_vegetarian_score(
    plan: dict[str, Any],
) -> float:

    restaurants = plan.get(
        "restaurants",
        [],
    )

    if not restaurants:
        return 0.5

    vegetarian_count = sum(
        1
        for restaurant in restaurants
        if restaurant.get(
            "vegetarian",
            False,
        )
    )

    return clamp(
        vegetarian_count
        / len(restaurants)
    )


# ============================================================
# MUSEUM SCORE
# ============================================================

def calculate_museum_score(
    plan: dict[str, Any],
) -> float:

    attractions = plan.get(
        "attractions",
        [],
    )

    if not attractions:
        return 0.5

    museum_count = sum(
        1
        for attraction in attractions
        if "museum"
        in str(
            attraction.get(
                "category",
                "",
            )
        ).lower()
    )

    return clamp(
        museum_count
        / len(attractions)
    )


# ============================================================
# LOCATION SCORE
# ============================================================

def calculate_location_score(
    plan: dict[str, Any],
) -> float:

    hotel = plan.get(
        "hotel",
        {},
    )

    text = (
        str(
            hotel.get(
                "location",
                "",
            )
        ).lower()
        + " "
        + str(
            hotel.get(
                "address",
                "",
            )
        ).lower()
    )

    central_keywords = [
        "central",
        "centre",
        "center",
        "city centre",
        "city center",
        "1st arrondissement",
        "2nd arrondissement",
        "3rd arrondissement",
        "4th arrondissement",
        "5th arrondissement",
        "6th arrondissement",
        "7th arrondissement",
        "8th arrondissement",
    ]

    if any(
        keyword in text
        for keyword in central_keywords
    ):
        return 1.0

    return 0.5


# ============================================================
# LUXURY SCORE
# ============================================================

def calculate_luxury_score(
    plan: dict[str, Any],
) -> float:

    hotel = plan.get(
        "hotel",
        {},
    )

    rating = safe_float(
        hotel.get(
            "rating",
            0,
        )
    )

    return clamp(
        rating / 5.0
    )


# ============================================================
# ROUTE SCORE
# ============================================================

def calculate_route_score(
    plan: dict[str, Any],
) -> float:

    itinerary = plan.get(
        "daily_itinerary",
        [],
    )

    if not itinerary:
        return 0.5

    total_travel_hours = sum(
        safe_float(
            day.get(
                "travel_hours",
                0,
            )
        )
        for day in itinerary
    )

    return clamp(
        1.0
        - total_travel_hours / 2.0
    )


# ============================================================
# PLAN SCORE
# ============================================================

def score_plan(
    plan: dict[str, Any],
    state: dict[str, Any],
) -> float:

    budget = safe_float(
        state.get(
            "budget",
            0,
        )
    )

    priorities = state.get(
        "priorities",
        {},
    )

    budget_score = calculate_budget_score(
        plan,
        budget,
    )

    food_score = calculate_food_score(
        plan,
        state,
    )

    museum_score = calculate_museum_score(
        plan,
    )

    location_score = calculate_location_score(
        plan,
    )

    luxury_score = calculate_luxury_score(
        plan,
    )

    route_score = calculate_route_score(
        plan,
    )

    components = [
        (
            budget_score,
            priority_weight(
                priorities.get(
                    "budget",
                    "MEDIUM",
                )
            ),
        ),

        (
            food_score,
            priority_weight(
                priorities.get(
                    "food",
                    priorities.get(
                        "vegetarian",
                        "MEDIUM",
                    ),
                )
            ),
        ),

        (
            museum_score,
            priority_weight("LOW"),
        ),

        (
            location_score,
            priority_weight(
                priorities.get(
                    "central_location",
                    "MEDIUM",
                )
            ),
        ),

        (
            luxury_score,
            priority_weight(
                priorities.get(
                    "luxury",
                    "MEDIUM",
                )
            ),
        ),

        (
            route_score,
            1.0,
        ),
    ]

    total_weight = sum(
        weight
        for _, weight in components
    )

    if total_weight <= 0:
        return 0.0

    weighted_score = sum(
        score * weight
        for score, weight in components
    )

    return (
        weighted_score
        / total_weight
        * 100
    )


# ============================================================
# FEASIBILITY
# ============================================================

def is_plan_feasible(
    plan: dict[str, Any],
    state: dict[str, Any],
) -> bool:

    if not plan:
        return False

    budget = safe_float(
        state.get(
            "budget",
            0,
        )
    )

    total_cost = safe_float(
        plan.get(
            "total_cost",
            0,
        )
    )

    # --------------------------------------------------------
    # Budget is a HARD constraint.
    # --------------------------------------------------------

    if budget <= 0:
        return False

    if total_cost > budget:
        return False

    # --------------------------------------------------------
    # Daily activity hours are a HARD constraint.
    # --------------------------------------------------------

    itinerary = plan.get(
        "daily_itinerary",
        [],
    )

    for day in itinerary:

        activity_hours = safe_float(
            day.get(
                "activity_hours",
                0,
            )
        )

        if activity_hours > 8.0:
            return False

    return True


# ============================================================
# FEASIBILITY REASON
# ============================================================

def get_feasibility_reason(
    plan: dict[str, Any],
    state: dict[str, Any],
) -> str:

    if not plan:
        return "No plan was generated."

    budget = safe_float(
        state.get(
            "budget",
            0,
        )
    )

    total_cost = safe_float(
        plan.get(
            "total_cost",
            0,
        )
    )

    if budget <= 0:
        return "Budget must be greater than £0."

    if total_cost > budget:

        difference = total_cost - budget

        return (
            f"Over budget by £{difference:.2f} "
            f"(plan £{total_cost:.2f} vs "
            f"budget £{budget:.2f})."
        )

    itinerary = plan.get(
        "daily_itinerary",
        [],
    )

    for day in itinerary:

        activity_hours = safe_float(
            day.get(
                "activity_hours",
                0,
            )
        )

        if activity_hours > 8.0:

            return (
                f"Daily activity time exceeds "
                f"8 hours ({activity_hours:.1f} hours)."
            )

    return "Feasible."


# ============================================================
# SCORE ALL CANDIDATES
# ============================================================

def score_candidate_plans(
    plans: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[dict[str, Any]]:

    scored_plans = []

    for plan in plans:

        feasible = is_plan_feasible(
            plan,
            state,
        )

        score = (
            score_plan(
                plan,
                state,
            )
            if feasible
            else 0.0
        )

        scored_plan = dict(
            plan
        )

        scored_plan["score"] = round(
            score,
            2,
        )

        scored_plan["feasible"] = (
            feasible
        )

        scored_plan[
            "feasibility_reason"
        ] = get_feasibility_reason(
            plan,
            state,
        )

        scored_plans.append(
            scored_plan
        )

    # Keep feasible candidates first,
    # then highest score.
    return sorted(
        scored_plans,
        key=lambda plan: (
            plan.get(
                "feasible",
                False,
            ),
            plan.get(
                "score",
                0,
            ),
        ),
        reverse=True,
    )