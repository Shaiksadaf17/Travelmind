from typing import Any, TypedDict


class TravelState(TypedDict, total=False):
    name: str
    origin: str
    destination: str
    start_date: str
    end_date: str
    travellers: int
    budget: float
    preferences: str
    food_preference: str
    priorities: dict[str, str]
    trip_type: str
    selected_outbound_flight: dict[str, Any]
    selected_return_flight: dict[str, Any]
    selected_flight: dict[str, Any]

    user_replan_requested: bool
    user_replan_changes: dict[str, Any]
    planning_session_id: str

    trip_id: str
    planning_run_id: str
    planning_run_number: int
    itinerary_id: str
    itinerary_version: int

    flight_options: list[dict[str, Any]]
    hotel_options: list[dict[str, Any]]
    attraction_options: list[dict[str, Any]]
    restaurant_options: list[dict[str, Any]]
    weather_data: dict[str, Any]
    route_data: dict[str, Any]

    opening_hours_data: dict[str, Any]
    route_optimisation: dict[str, Any]
    daily_itinerary: list[dict[str, Any]]
    tool_results: dict[str, dict[str, Any]]

    candidate_plans: list[dict[str, Any]]
    selected_plan: dict[str, Any] | None

    validation_result: dict[str, Any]
    evaluation_result: dict[str, Any]
    conflicts: list[dict[str, Any]]

    replan_required: bool
    replan_count: int

    explanations: list[str]
    data_quality: dict[str, Any]
    agent_trace: list[dict[str, Any]]
