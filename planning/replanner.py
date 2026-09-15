from typing import Any
from datetime import date

from planning.planner import (
    build_candidate_plans,
    select_best_plan,
)
from planning.opening_hours import is_attraction_open
from planning.weather_planner import (
    select_weather_suitable_activities,
)
from planning.route_optimizer import (
    optimise_daily_route,
)
from planning.daily_itinerary import (
    build_daily_itinerary,
)


MAX_REPLANS = 3


def replan_travel(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Perform a bounded automatic replanning attempt.

    Replanning keeps the original trip requirements while
    progressively reducing optional costs and improving
    feasibility.

    The replanner continues to respect:

    - budget constraints
    - user preferences
    - opening hours
    - weather suitability
    - daily activity limits
    - deterministic plan scoring
    """

    current_count = int(
        state.get("replan_count", 0)
    )

    # --------------------------------------------------
    # Stop after maximum number of replans
    # --------------------------------------------------

    if current_count >= MAX_REPLANS:
        return {
            "replan_count": current_count,
            "replan_required": False,
            "candidate_plans": state.get(
                "candidate_plans",
                [],
            ),
            "selected_plan": state.get(
                "selected_plan"
            ),
            "message": (
                "Maximum replanning attempts reached."
            ),
        }

    current_count += 1

    # --------------------------------------------------
    # Calculate trip duration
    # --------------------------------------------------

    try:
        start = date.fromisoformat(
            str(state["start_date"])
        )
        end = date.fromisoformat(
            str(state["end_date"])
        )

        trip_days = max(
            (end - start).days,
            1,
        )

    except (ValueError, TypeError, KeyError):
        trip_days = 1

    # --------------------------------------------------
    # Build fresh candidate plans
    # --------------------------------------------------

    candidates = build_candidate_plans(state)

    weather = state.get(
        "weather_data",
        {},
    )

    attractions = state.get(
        "attraction_options",
        [],
    )

    # --------------------------------------------------
    # Apply opening-hours filtering
    # --------------------------------------------------

    available_attractions = [
        attraction
        for attraction in attractions
        if is_attraction_open(
            attraction,
            str(state["start_date"]),
        )
    ]

    # --------------------------------------------------
    # Apply weather-aware filtering
    # --------------------------------------------------

    weather_suitable_attractions = (
        select_weather_suitable_activities(
            available_attractions,
            weather,
        )
    )

    # --------------------------------------------------
    # Apply route optimisation
    # --------------------------------------------------

    optimised_attractions = (
        optimise_daily_route(
            weather_suitable_attractions,
            max_hours=8.0,
        )
    )

    # --------------------------------------------------
    # Replanning strategy
    # --------------------------------------------------

    for plan in candidates:

        # ----------------------------------------------
        # Replan 1
        # Remove paid attractions
        # ----------------------------------------------

        if current_count == 1:

            plan["attractions"] = [
                attraction
                for attraction in optimised_attractions
                if attraction.get("price", 0) == 0
            ]

        # ----------------------------------------------
        # Replan 2
        # Remove paid attractions and reduce
        # estimated food expenditure
        # ----------------------------------------------

        elif current_count == 2:

            plan["attractions"] = [
                attraction
                for attraction in optimised_attractions
                if attraction.get("price", 0) == 0
            ]

            plan["estimated_food_cost"] = (
                15
                * state["travellers"]
                * trip_days
            )

        # ----------------------------------------------
        # Replan 3
        # Use cheapest flight and hotel
        # ----------------------------------------------

        elif current_count == 3:

            flight_options = state.get(
                "flight_options",
                [],
            )

            hotel_options = state.get(
                "hotel_options",
                [],
            )

            if flight_options:
                cheapest_flight = min(
                    flight_options,
                    key=lambda x: x.get(
                        "total_price",
                        float("inf"),
                    ),
                )

                plan["flight"] = cheapest_flight

            if hotel_options:
                cheapest_hotel = min(
                    hotel_options,
                    key=lambda x: x.get(
                        "total_price",
                        float("inf"),
                    ),
                )

                plan["hotel"] = cheapest_hotel

            plan["attractions"] = [
                attraction
                for attraction in optimised_attractions
                if attraction.get("price", 0) == 0
            ]

            plan["estimated_food_cost"] = (
                15
                * state["travellers"]
                * trip_days
            )

        # ----------------------------------------------
        # Recalculate total cost
        # ----------------------------------------------

        attraction_cost = sum(
            float(attraction.get("price", 0) or 0)
            for attraction in plan.get(
                "attractions",
                [],
            )
        )

        flight_cost = float(
            plan.get("flight", {}).get(
                "total_price",
                0,
            )
            or 0
        )

        hotel_cost = float(
            plan.get("hotel", {}).get(
                "total_price",
                0,
            )
            or 0
        )

        food_cost = float(
            plan.get(
                "estimated_food_cost",
                0,
            )
            or 0
        )

        plan["total_cost"] = round(
            flight_cost
            + hotel_cost
            + attraction_cost
            + food_cost,
            2,
        )

        plan["within_budget"] = (
            plan["total_cost"]
            <= float(state["budget"])
        )

        # ----------------------------------------------
        # Rebuild daily itinerary
        # ----------------------------------------------

        try:
            plan["daily_itinerary"] = (
                build_daily_itinerary(
                    plan.get("attractions", []),
                    state["start_date"],
                    state["end_date"],
                )
            )
        except Exception:
            plan["daily_itinerary"] = []

    # --------------------------------------------------
    # Score all replanned candidates
    # --------------------------------------------------

    best_plan = select_best_plan(
        candidates,
        state,
    )

    # --------------------------------------------------
    # Determine whether another replan is required
    # --------------------------------------------------

    if best_plan is not None:

        replan_required = False

        message = (
            f"Replanning attempt "
            f"{current_count} found a feasible "
            f"plan."
        )

    else:

        replan_required = (
            current_count < MAX_REPLANS
        )

        message = (
            f"Replanning attempt "
            f"{current_count} completed, but "
            f"no feasible plan was found."
        )

    return {
        "replan_count": current_count,
        "replan_required": replan_required,
        "candidate_plans": state.get(
            "candidate_plans",
            candidates,
        ),
        "selected_plan": best_plan,
        "message": message,
    }

def apply_user_replan_changes(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply user-requested changes to the current
    planning state.

    Unlike automatic replanning, user-initiated
    replanning can be performed repeatedly.
    """

    changes = state.get(
        "user_replan_changes",
        {},
    )

    if not changes:
        return state

    # --------------------------------------------------
    # Update supported trip requirements
    # --------------------------------------------------

    allowed_fields = {
        "origin",
        "destination",
        "start_date",
        "end_date",
        "travellers",
        "budget",
        "preferences",
        "priorities",
    }

    for field, value in changes.items():

        if field in allowed_fields:
            state[field] = value

    # --------------------------------------------------
    # Reset automatic replanning counter
    # --------------------------------------------------

    state["replan_count"] = 0

    state["replan_required"] = False

    # --------------------------------------------------
    # Clear old planning outputs
    # --------------------------------------------------

    state["candidate_plans"] = []

    state["selected_plan"] = None

    state["daily_itinerary"] = []

    state["evaluation_result"] = {}

    state["validation_result"] = {}

    state["conflicts"] = []

    state["explanations"] = []

    # --------------------------------------------------
    # Mark user replanning request as processed
    # --------------------------------------------------

    state["user_replan_requested"] = False

    state["user_replan_changes"] = {}

    return state