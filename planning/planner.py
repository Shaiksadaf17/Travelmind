from typing import Any
from planning.scoring import score_candidate_plans
from planning.opening_hours import is_attraction_open
from planning.weather_planner import select_weather_suitable_activities
from planning.route_optimizer import optimise_daily_route
from planning.daily_itinerary import build_daily_itinerary


def _as_list(value):
    """Return tool records whether the tool returned a list or an envelope."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        data = value.get("data", [])
        return data if isinstance(data, list) else []
    return []


def _as_dict(value):
    """Return dictionary payloads safely."""
    if isinstance(value, dict):
        data = value.get("data", value)
        return data if isinstance(data, dict) else {}
    return {}



def _normalise_food_preference(state: dict[str, Any]) -> str:
    explicit = str(
        state.get("food_preference", "")
    ).strip()

    if explicit:
        return explicit

    text = str(
        state.get("preferences", "")
    ).lower()

    if "vegan" in text:
        return "Vegan"
    if "non-vegetarian" in text or "non vegetarian" in text:
        return "Non-Vegetarian"
    if "vegetarian" in text:
        return "Vegetarian"

    return "No Food Preference"


def _select_restaurants(
    restaurants: list[dict[str, Any]],
    state: dict[str, Any],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """
    Deterministically rank restaurants/cafes according to
    the user's food preference.

    Non-vegetarian is deliberately treated as a real preference,
    not as an empty/no-preference value.
    """
    if not restaurants:
        return []

    preference = _normalise_food_preference(state)

    def rating(place):
        return float(place.get("rating", 0) or 0)

    def is_veg(place):
        return bool(place.get("vegetarian", False))

    def is_vegan(place):
        return bool(place.get("vegan", False))

    if preference == "Vegetarian":
        ranked = sorted(
            restaurants,
            key=lambda x: (
                not is_veg(x),
                -rating(x),
            ),
        )

    elif preference == "Vegan":
        ranked = sorted(
            restaurants,
            key=lambda x: (
                not is_vegan(x),
                not is_veg(x),
                -rating(x),
            ),
        )

    elif preference == "Non-Vegetarian":
        # Do not filter out restaurants simply because the API
        # does not explicitly label them as non-vegetarian.
        ranked = sorted(
            restaurants,
            key=lambda x: (
                is_veg(x),
                is_vegan(x),
                -rating(x),
            ),
        )

    else:
        ranked = sorted(
            restaurants,
            key=rating,
            reverse=True,
        )

    return ranked[:limit]

def build_candidate_plans(
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build three genuinely different candidate plans:

    1. Budget Optimised
    2. Balanced
    3. Comfort Focused

    Hard budget feasibility is handled later by
    deterministic validation.
    """

    flights = _as_list(state.get("flight_options", []))

    hotels = _as_list(state.get("hotel_options", []))

    attractions = _as_list(state.get("attraction_options", []))

    restaurants = _as_list(state.get("restaurant_options", []))

    weather = _as_dict(state.get("weather_data", {}))

    selected_restaurants = _select_restaurants(
        restaurants,
        state,
        limit=3,
    )

    budget = float(
        state.get(
            "budget",
            0,
        )
    )

    travellers = int(
        state.get(
            "travellers",
            1,
        )
    )

    if not flights or not hotels:
        return []

    # --------------------------------------------------
    # Weather + opening-hours filtering
    # --------------------------------------------------

    available_attractions = [
        attraction
        for attraction in attractions
        if is_attraction_open(
            attraction,
            state["start_date"],
        )
    ]

    weather_suitable_attractions = (
        select_weather_suitable_activities(
            available_attractions,
            weather,
        )
    )

    optimised_attractions = (
        optimise_daily_route(
            weather_suitable_attractions,
            max_hours=8.0,
        )
    )

    # --------------------------------------------------
    # Daily itinerary helper
    # --------------------------------------------------

    def create_itinerary(
        selected_attractions,
    ):
        return build_daily_itinerary(
            selected_attractions,
            state["start_date"],
            state["end_date"],
            max_activity_hours=8.0,
            restaurants=selected_restaurants,
        )

    # ==================================================
    # 1. BUDGET OPTIMISED
    # ==================================================

    cheapest_flight = min(
        flights,
        key=lambda x: x.get(
            "total_price",
            float("inf"),
        ),
    )

    cheapest_hotel = min(
        hotels,
        key=lambda x: x.get(
            "total_price",
            float("inf"),
        ),
    )

    budget_attractions = [
        attraction
        for attraction in optimised_attractions
        if float(
            attraction.get(
                "price",
                0,
            )
            or 0
        ) <= 20
    ]

    budget_attractions = budget_attractions[
        :3
    ]

    budget_food = (
        20
        * travellers
        * max(
            (
                (
                    __import__("datetime")
                    .date.fromisoformat(
                        state["end_date"]
                    )
                    - __import__("datetime")
                    .date.fromisoformat(
                        state["start_date"]
                    )
                ).days
            ),
            1,
        )
    )

    budget_itinerary = create_itinerary(
        budget_attractions
    )

    budget_attraction_cost = sum(
        float(
            attraction.get(
                "price",
                0,
            )
            or 0
        )
        for attraction in budget_attractions
    )

    budget_total = (
        cheapest_flight["total_price"]
        + cheapest_hotel["total_price"]
        + budget_attraction_cost
        + budget_food
    )

    budget_plan = {
        "name": "Budget Optimised",
        "strategy": (
            "Minimise total cost while "
            "satisfying key preferences."
        ),
        "flight": cheapest_flight,
        "hotel": cheapest_hotel,
        "attractions": budget_attractions,
        "restaurants": selected_restaurants,
        "estimated_food_cost": budget_food,
        "daily_itinerary": budget_itinerary,
        "total_cost": budget_total,
        "within_budget": (
            budget_total <= budget
        ),
    }

    # ==================================================
    # 2. BALANCED
    # ==================================================

    # Reasonable price + good quality.
    balanced_flight = min(
        flights,
        key=lambda x: (
            float(
                x.get(
                    "total_price",
                    float("inf"),
                )
            )
        ),
    )

    balanced_hotel = max(
        hotels,
        key=lambda x: (
            float(
                x.get(
                    "rating",
                    0,
                )
                or 0
            )
            / max(
                float(
                    x.get(
                        "total_price",
                        1,
                    )
                    or 1
                ),
                1,
            )
        ),
    )

    balanced_attractions = (
        optimised_attractions[:3]
    )

    balanced_food = (
        25
        * travellers
        * max(
            (
                (
                    __import__("datetime")
                    .date.fromisoformat(
                        state["end_date"]
                    )
                    - __import__("datetime")
                    .date.fromisoformat(
                        state["start_date"]
                    )
                ).days
            ),
            1,
        )
    )

    balanced_itinerary = create_itinerary(
        balanced_attractions
    )

    balanced_attraction_cost = sum(
        float(
            attraction.get(
                "price",
                0,
            )
            or 0
        )
        for attraction in balanced_attractions
    )

    balanced_total = (
        balanced_flight["total_price"]
        + balanced_hotel["total_price"]
        + balanced_attraction_cost
        + balanced_food
    )

    balanced_plan = {
        "name": "Balanced",
        "strategy": (
            "Balance cost, accommodation "
            "quality and user preferences."
        ),
        "flight": balanced_flight,
        "hotel": balanced_hotel,
        "attractions": balanced_attractions,
        "restaurants": selected_restaurants,
        "estimated_food_cost": balanced_food,
        "daily_itinerary": balanced_itinerary,
        "total_cost": balanced_total,
        "within_budget": (
            balanced_total <= budget
        ),
    }

    # ==================================================
    # 3. COMFORT FOCUSED
    # ==================================================

    comfort_flight = max(
        flights,
        key=lambda x: (
            float(
                x.get(
                    "total_price",
                    0,
                )
                or 0
            )
        ),
    )

    comfort_hotel = max(
        hotels,
        key=lambda x: (
            float(
                x.get(
                    "rating",
                    0,
                )
                or 0
            )
        ),
    )

    comfort_attractions = (
        optimised_attractions[:3]
    )

    comfort_food = (
        35
        * travellers
        * max(
            (
                (
                    __import__("datetime")
                    .date.fromisoformat(
                        state["end_date"]
                    )
                    - __import__("datetime")
                    .date.fromisoformat(
                        state["start_date"]
                    )
                ).days
            ),
            1,
        )
    )

    comfort_itinerary = create_itinerary(
        comfort_attractions
    )

    comfort_attraction_cost = sum(
        float(
            attraction.get(
                "price",
                0,
            )
            or 0
        )
        for attraction in comfort_attractions
    )

    comfort_total = (
        comfort_flight["total_price"]
        + comfort_hotel["total_price"]
        + comfort_attraction_cost
        + comfort_food
    )

    comfort_plan = {
        "name": "Comfort Focused",
        "strategy": (
            "Prioritise higher-rated accommodation "
            "and greater travel comfort."
        ),
        "flight": comfort_flight,
        "hotel": comfort_hotel,
        "attractions": comfort_attractions,
        "restaurants": selected_restaurants,
        "estimated_food_cost": comfort_food,
        "daily_itinerary": comfort_itinerary,
        "total_cost": comfort_total,
        "within_budget": (
            comfort_total <= budget
        ),
    }

    return [
        budget_plan,
        balanced_plan,
        comfort_plan,
    ]

def select_best_plan(
    candidates: list[dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any] | None:

    scored_candidates = score_candidate_plans(
        candidates,
        state,
    )

    budget = float(
        state.get(
            "budget",
            0,
        )
    )

    # Mark feasibility explicitly.
    for plan in scored_candidates:
        total_cost = float(
            plan.get(
                "total_cost",
                0,
            )
        )

        plan["within_budget"] = (
            total_cost <= budget
        )

    # Keep all scored candidates in state.
    # This is important for explainability/evaluation.
    state["candidate_plans"] = scored_candidates

    # Only feasible plans can become the final plan.
    feasible_plans = [
        plan
        for plan in scored_candidates
        if plan.get(
            "within_budget",
            False,
        )
    ]

    if not feasible_plans:
        return None

    return max(
        feasible_plans,
        key=lambda plan: plan.get(
            "score",
            0,
        ),
    )

    # --------------------------------------------------
    # Deterministic scoring
    # --------------------------------------------------

    def score(
        plan: dict[str, Any],
    ) -> float:

        score_value = 0.0

        remaining_budget = (
            budget - plan["total_cost"]
        )

        # Budget priority
        if budget_priority == "HIGH":
            score_value += (
                remaining_budget
                / max(budget, 1)
                * 50
            )

        elif budget_priority == "MEDIUM":
            score_value += (
                remaining_budget
                / max(budget, 1)
                * 25
            )

        # Vegetarian preference
        vegetarian_restaurants = sum(
            1
            for restaurant in plan.get(
                "restaurants",
                [],
            )
            if restaurant.get(
                "vegetarian",
                False,
            )
        )

        if vegetarian_priority == "HIGH":
            score_value += (
                vegetarian_restaurants * 20
            )

        elif vegetarian_priority == "MEDIUM":
            score_value += (
                vegetarian_restaurants * 10
            )

        # Central location preference
        location = plan["hotel"].get(
            "location",
            "",
        ).lower()

        if "central" in location:

            if location_priority == "HIGH":
                score_value += 30

            elif location_priority == "MEDIUM":
                score_value += 15

        # Hotel rating
        score_value += (
            plan["hotel"].get(
                "rating",
                0,
            )
            * 5
        )

        return score_value

    # --------------------------------------------------
    # Select highest-scoring feasible plan
    # --------------------------------------------------

    best_plan = max(
        feasible_plans,
        key=score,
    )

    best_plan["score"] = round(
        score(best_plan),
        2,
    )

    return best_plan