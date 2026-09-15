from agent.llm import llm
from agent.prompts import SYSTEM_PROMPT
from agent.state import TravelState

from validation.evaluator import evaluate_plan
from validation.conflicts import detect_conflicts

from tools.flights import search_flights
from tools.hotels import search_hotels
from tools.attractions import search_attractions
from tools.restaurants import search_restaurants
from tools.weather import get_weather
from tools.maps import get_route

from planning.daily_itinerary import build_daily_itinerary
from planning.explanations import generate_plan_explanation
from planning.replanner import replan_travel
from planning.planner import (
    build_candidate_plans,
    select_best_plan,
)
from planning.replanner import (
    apply_user_replan_changes,
)

# ==================================================
# DATABASE PERSISTENCE
# ==================================================

from database.users import get_or_create_user
from database.trips import create_trip

from database.planning_runs import (
    create_planning_run,
    update_planning_run,
)

from database.queries import (
    create_query,
)

from database.tool_results import (
    create_tool_result,
)

from database.itineraries import (
    create_itinerary_version,
)

from database.evaluations import (
    create_evaluation,
)

from database.traces import (
    create_traces,
)


# ==================================================
# TRACE HELPER
# ==================================================

def add_trace(
    state: TravelState,
    action: str,
    status: str,
    message: str,
) -> None:
    """
    Add a sequential high-level agent trace event.
    """

    trace = state.get("agent_trace", [])

    trace.append(
        {
            "step": len(trace) + 1,
            "action": action,
            "status": status,
            "message": message,
        }
    )

    state["agent_trace"] = trace


# ==================================================
# DATABASE HELPERS
# ==================================================

def ensure_trip_and_run(
    state: TravelState,
) -> TravelState:
    """
    Ensure that the current planning session has
    a draft trip and a planning run.

    Draft trips are created with is_saved=False,
    so they do not appear in Travel History.
    """

    # --------------------------------------------------
    # Existing planning run
    # --------------------------------------------------

    if state.get("planning_run_id"):
        return state

    # --------------------------------------------------
    # Create/reuse user
    # --------------------------------------------------

    user = get_or_create_user(
        state["name"]
    )

    # --------------------------------------------------
    # Create draft trip if necessary
    # --------------------------------------------------

    trip_id = state.get("trip_id")

    if not trip_id:

        trip_record = create_trip(
            user["user_id"],
            {
                "origin": state["origin"],
                "destination": state["destination"],
                "start_date": state["start_date"],
                "end_date": state["end_date"],
                "travellers": state["travellers"],
                "budget": state["budget"],
                "preferences": state.get(
                    "preferences",
                    "",
                ),
                "priorities": state.get(
                    "priorities",
                    {},
                ),
            },
        )

        trip_id = trip_record["trip_id"]

        state["trip_id"] = trip_id

    # --------------------------------------------------
    # Determine run number
    # --------------------------------------------------

    run_number = (
        int(state.get("planning_run_number", 0))
        + 1
    )

    # --------------------------------------------------
    # Create planning run
    # --------------------------------------------------

    run = create_planning_run(
        trip_id=trip_id,
        run_number=run_number,
        status="started",
        iteration_count=0,
    )

    state["planning_run_id"] = run["run_id"]

    state["planning_run_number"] = run_number

    return state


def _tool_result_parts(result):
    """
    Normalise tool responses.

    TravelMind tools may return either:
      1. a raw list of records, or
      2. an envelope such as {"status": "ok", "data": [...], "message": "..."}.

    The planner needs the raw records, while persistence needs a
    consistent envelope. This helper supports both formats.
    """
    if isinstance(result, dict):
        status = result.get("status", "unknown")
        data = result.get("data", result)
        message = result.get("message", "")
        return status, data, message

    if isinstance(result, list):
        status = "ok" if result else "unavailable"
        message = "" if result else "No results returned by tool."
        return status, result, message

    if result is None:
        return "unavailable", [], "Tool returned no result."

    return "ok", result, ""


def persist_tool_query(
    state: TravelState,
    tool_name: str,
    parameters: dict,
    result,
) -> None:
    """
    Persist one tool query and its result.

    Accepts both raw tool output lists and structured result dictionaries.
    """
    run_id = state.get("planning_run_id")

    if not run_id:
        return

    query = create_query(
        run_id=run_id,
        tool_name=tool_name,
        query_parameters=parameters,
    )

    status, data, message = _tool_result_parts(result)

    create_tool_result(
        query_id=query["query_id"],
        tool_name=tool_name,
        status=status,
        result_data=data,
        message=message,
    )


def persist_itinerary(
    state: TravelState,
) -> None:
    """
    Persist the currently selected itinerary
    as a generated itinerary version.
    """

    trip_id = state.get("trip_id")
    run_id = state.get("planning_run_id")
    plan = state.get("selected_plan")

    if not trip_id or not run_id or not plan:
        return

    version = int(
        state.get(
            "itinerary_version",
            0,
        )
    ) + 1

    itinerary = create_itinerary_version(
        trip_id=trip_id,
        run_id=run_id,
        version=version,
        plan_data=plan,
        total_cost=float(
            plan.get(
                "total_cost",
                0,
            )
        ),
        status="generated",
        is_final=True,
        is_saved=False,
    )

    state["itinerary_version"] = version

    state["itinerary_id"] = (
        itinerary["itinerary_id"]
    )


def persist_evaluation(
    state: TravelState,
) -> None:
    """
    Persist deterministic evaluation results.
    """

    run_id = state.get(
        "planning_run_id"
    )

    itinerary_id = state.get(
        "itinerary_id"
    )

    if not run_id or not itinerary_id:
        return

    create_evaluation(
        run_id=run_id,
        itinerary_id=itinerary_id,
        evaluation=state.get(
            "evaluation_result",
            {},
        ),
    )


def persist_agent_trace(
    state: TravelState,
) -> None:
    """
    Persist the high-level agent journey.

    This stores observable actions only and does
    not store private LLM chain-of-thought.
    """

    run_id = state.get(
        "planning_run_id"
    )

    if not run_id:
        return

    trace = state.get(
        "agent_trace",
        [],
    )

    if trace:
        create_traces(
            run_id,
            trace,
        )


def complete_planning_run(
    state: TravelState,
) -> None:
    """
    Mark the current planning run as completed.
    """

    run_id = state.get(
        "planning_run_id"
    )

    if not run_id:
        return

    evaluation = state.get(
        "evaluation_result",
        {},
    )

    status = (
        "completed"
        if evaluation.get(
            "passed",
            False,
        )
        else "completed_with_warnings"
    )

    update_planning_run(
        run_id=run_id,
        status=status,
        iteration_count=state.get(
            "replan_count",
            0,
        ),
    )


# ==================================================
# UNDERSTAND REQUEST
# ==================================================

def understand_request(
    state: TravelState,
) -> TravelState:
    """
    Use the configured LLM to interpret the
    user's travel requirements.
    """

    # --------------------------------------------------
    # Ensure draft trip + planning run
    # --------------------------------------------------

    state = ensure_trip_and_run(
        state
    )

    # --------------------------------------------------
    # LLM understanding
    # --------------------------------------------------

    prompt = f"""
{SYSTEM_PROMPT}

Here is the user's travel request:

Name: {state.get("name")}
Origin: {state.get("origin")}
Destination: {state.get("destination")}
Start date: {state.get("start_date")}
End date: {state.get("end_date")}
Travellers: {state.get("travellers")}
Budget: £{state.get("budget")}
Preferences: {state.get("preferences")}
Preference priorities: {state.get("priorities")}

Briefly confirm that you understand the requirements.

Do not provide the complete itinerary yet.
"""

    response = llm.invoke(
        prompt
    )

    state["explanations"] = [
        response.content
    ]

    add_trace(
        state,
        "understand_request",
        "completed",
        "Travel requirements understood.",
    )

    return state


# ==================================================
# COLLECT TRAVEL DATA
# ==================================================

def collect_travel_data(
    state: TravelState,
) -> TravelState:
    """
    Collect travel information from all available tools.

    Tools are allowed to return raw lists/dicts. Internally we keep those
    raw values in state because the planning layer expects lists, while
    database persistence uses _tool_result_parts() for a consistent shape.
    """

    state = ensure_trip_and_run(state)

    # --------------------------------------------------
    # 1. Flights
    # --------------------------------------------------
    flights = search_flights(
        origin=state["origin"],
        destination=state["destination"],
        start_date=state["start_date"],
        end_date=state["end_date"],
        travellers=state["travellers"],
    )

    persist_tool_query(
        state,
        "flights",
        {
            "origin": state["origin"],
            "destination": state["destination"],
            "start_date": state["start_date"],
            "end_date": state["end_date"],
            "travellers": state["travellers"],
        },
        flights,
    )

    # --------------------------------------------------
    # 2. Hotels
    # --------------------------------------------------
    hotels = search_hotels(
        destination=state["destination"],
        start_date=state["start_date"],
        end_date=state["end_date"],
        travellers=state["travellers"],
    )

    persist_tool_query(
        state,
        "hotels",
        {
            "destination": state["destination"],
            "start_date": state["start_date"],
            "end_date": state["end_date"],
            "travellers": state["travellers"],
        },
        hotels,
    )

    # --------------------------------------------------
    # 3. Attractions
    # --------------------------------------------------
    attractions = search_attractions(
        destination=state["destination"],
        preferences=state.get("preferences", ""),
    )

    persist_tool_query(
        state,
        "attractions",
        {
            "destination": state["destination"],
            "preferences": state.get("preferences", ""),
        },
        attractions,
    )

    # --------------------------------------------------
    # 4. Restaurants
    # --------------------------------------------------
    restaurants = search_restaurants(
        destination=state["destination"],
        preferences=state.get("preferences", ""),
    )

    persist_tool_query(
        state,
        "restaurants",
        {
            "destination": state["destination"],
            "preferences": state.get("preferences", ""),
            "food_preference": state.get(
                "food_preference",
                "No Food Preference",
            ),
        },
        restaurants,
    )

    # --------------------------------------------------
    # 5. Weather
    # --------------------------------------------------
    weather = get_weather(
        destination=state["destination"],
        start_date=state["start_date"],
        end_date=state["end_date"],
    )

    persist_tool_query(
        state,
        "weather",
        {
            "destination": state["destination"],
            "start_date": state["start_date"],
            "end_date": state["end_date"],
        },
        weather,
    )

    # --------------------------------------------------
    # 6. Route
    # --------------------------------------------------
    route = get_route(
        origin=state["origin"],
        destination=state["destination"],
    )

    persist_tool_query(
        state,
        "maps",
        {
            "origin": state["origin"],
            "destination": state["destination"],
        },
        route,
    )

    # --------------------------------------------------
    # Keep complete raw responses
    # --------------------------------------------------
    state["tool_results"] = {
        "flights": flights,
        "hotels": hotels,
        "attractions": attractions,
        "restaurants": restaurants,
        "weather": weather,
        "maps": route,
    }

    # --------------------------------------------------
    # Keep planning-layer data in the format expected by planner.py
    # --------------------------------------------------
    _, flight_data, flight_message = _tool_result_parts(flights)
    _, hotel_data, hotel_message = _tool_result_parts(hotels)
    _, attraction_data, attraction_message = _tool_result_parts(attractions)
    _, restaurant_data, restaurant_message = _tool_result_parts(restaurants)
    _, weather_data, weather_message = _tool_result_parts(weather)
    _, route_data, route_message = _tool_result_parts(route)

    state["flight_options"] = (
        flight_data if isinstance(flight_data, list) else []
    )
    state["hotel_options"] = (
        hotel_data if isinstance(hotel_data, list) else []
    )
    state["attraction_options"] = (
        attraction_data if isinstance(attraction_data, list) else []
    )
    state["restaurant_options"] = (
        restaurant_data if isinstance(restaurant_data, list) else []
    )

    state["weather_data"] = (
        weather_data
        if isinstance(weather_data, (dict, list))
        else {}
    )

    state["route_data"] = (
        route_data
        if isinstance(route_data, (dict, list))
        else {}
    )

    # --------------------------------------------------
    # Data quality
    # --------------------------------------------------
    flight_status, _, _ = _tool_result_parts(flights)
    hotel_status, _, _ = _tool_result_parts(hotels)
    attraction_status, _, _ = _tool_result_parts(attractions)
    restaurant_status, _, _ = _tool_result_parts(restaurants)
    weather_status, _, _ = _tool_result_parts(weather)
    route_status, _, _ = _tool_result_parts(route)

    state["data_quality"] = {
        "flights": flight_status,
        "hotels": hotel_status,
        "attractions": attraction_status,
        "restaurants": restaurant_status,
        "weather": weather_status,
        "maps": route_status,
    }

    # --------------------------------------------------
    # Agent trace
    # --------------------------------------------------
    add_trace(
        state,
        "collect_flight_data",
        flight_status,
        flight_message,
    )

    add_trace(
        state,
        "collect_hotel_data",
        hotel_status,
        hotel_message,
    )

    add_trace(
        state,
        "collect_attraction_data",
        attraction_status,
        attraction_message,
    )

    add_trace(
        state,
        "collect_restaurant_data",
        restaurant_status,
        restaurant_message,
    )

    add_trace(
        state,
        "collect_weather_data",
        weather_status,
        weather_message,
    )

    add_trace(
        state,
        "collect_route_data",
        route_status,
        route_message,
    )

    return state


# ==================================================
# CREATE TRAVEL PLAN
# ==================================================

def create_travel_plan(
    state: TravelState,
) -> TravelState:
    """
    Create candidate plans, select the best
    feasible plan, generate explanations and
    build the daily itinerary.
    """

    # --------------------------------------------------
    # 1. Create candidate plans
    # --------------------------------------------------

    candidates = build_candidate_plans(
        state
    )

    # --------------------------------------------------
    # TEMPORARY DIAGNOSTIC OUTPUT
    # --------------------------------------------------
    print("\n" + "=" * 60)
    print("TRAVELMIND PLANNER DEBUG")
    print("=" * 60)
    print("Origin:", state.get("origin"))
    print("Destination:", state.get("destination"))
    print("Dates:", state.get("start_date"), "->", state.get("end_date"))
    print("Travellers:", state.get("travellers"))
    print("Budget:", state.get("budget"))
    print("Food preference:", state.get("food_preference"))
    print("Flights:", len(state.get("flight_options", [])) if isinstance(state.get("flight_options", []), list) else "NOT LIST")
    print("Hotels:", len(state.get("hotel_options", [])) if isinstance(state.get("hotel_options", []), list) else "NOT LIST")
    print("Attractions:", len(state.get("attraction_options", [])) if isinstance(state.get("attraction_options", []), list) else "NOT LIST")
    print("Restaurants:", len(state.get("restaurant_options", [])) if isinstance(state.get("restaurant_options", []), list) else "NOT LIST")
    print("Candidates generated:", len(candidates))

    for idx, candidate in enumerate(candidates, 1):
        print(f"Candidate {idx}: {candidate.get('name')}")
        print("  Total cost:", candidate.get("total_cost"))
        print("  Within budget:", candidate.get("within_budget"))
        print("  Attractions:", len(candidate.get("attractions", [])))
        print("  Restaurants:", len(candidate.get("restaurants", [])))
        print("  Itinerary days:", len(candidate.get("daily_itinerary", [])))

    state["candidate_plans"] = candidates

    # --------------------------------------------------
    # 2. Opening-hours information
    # --------------------------------------------------

    state["opening_hours_data"] = {
        attraction["name"]: attraction.get(
            "opening_hours",
            "Unknown",
        )
        for attraction in state.get(
            "attraction_options",
            [],
        )
    }

    # --------------------------------------------------
    # 3. Select best feasible plan
    # --------------------------------------------------

    best_plan = select_best_plan(
        candidates,
        state,
    )

    print("Selected plan:", best_plan.get("name") if best_plan else None)
    if best_plan:
        print("Selected total cost:", best_plan.get("total_cost"))
        print("Selected score:", best_plan.get("score"))
    else:
        print("RESULT: NO FEASIBLE PLAN")
    print("=" * 60 + "\n")

    state["selected_plan"] = best_plan

    # --------------------------------------------------
    # 4. Generate explanation
    # --------------------------------------------------

    if best_plan:

        state["explanations"] = (
            generate_plan_explanation(
                best_plan,
                state,
                state.get(
                    "candidate_plans",
                    [],
                ),
            )
        )

    else:

        state["explanations"] = [
            "No feasible travel plan was found "
            "within the specified constraints."
        ]

    # --------------------------------------------------
    # 5. Build daily itinerary
    # --------------------------------------------------

    daily_itinerary = []

    if best_plan:

        selected_attractions = (
            best_plan.get(
                "attractions",
                [],
            )
        )

        daily_itinerary = (
            build_daily_itinerary(
                selected_attractions,
                state["start_date"],
                state["end_date"],
                max_activity_hours=8.0,
            )
        )

    state["daily_itinerary"] = (
        daily_itinerary
    )

    if best_plan:

        best_plan["daily_itinerary"] = (
            daily_itinerary
        )

        state["selected_plan"] = (
            best_plan
        )

    # --------------------------------------------------
    # 6. Route optimisation information
    # --------------------------------------------------

    state["route_optimisation"] = {
        "max_daily_activity_hours": 8.0,
        "optimisation_method": (
            "Geographic route optimisation using "
            "attraction coordinates, travel time, "
            "ratings and activity duration."
        ),
    }

    # --------------------------------------------------
    # 7. Trace plan creation
    # --------------------------------------------------

    add_trace(
        state,
        "create_travel_plan",
        "completed" if best_plan else "failed",
        (
            f"Best feasible plan selected: "
            f"{best_plan['name']}."
            if best_plan
            else
            "No candidate plan satisfies the "
            "user's budget."
        ),
    )

    # --------------------------------------------------
    # 8. Opening hours
    # --------------------------------------------------

    add_trace(
        state,
        "opening_hours_check",
        "completed",
        (
            "Attraction opening-hours information "
            "was considered during planning."
        ),
    )

    # --------------------------------------------------
    # 9. Weather + route
    # --------------------------------------------------

    add_trace(
        state,
        "weather_route_optimisation",
        "completed",
        (
            "Weather suitability, geographic "
            "routing and daily activity duration "
            "were considered during planning."
        ),
    )

    # --------------------------------------------------
    # 10. Daily itinerary
    # --------------------------------------------------

    add_trace(
        state,
        "daily_itinerary_generation",
        "completed"
        if daily_itinerary
        else "failed",
        (
            "Opening-hours-aware daily itinerary "
            "with activity time slots was generated."
            if daily_itinerary
            else
            "No daily itinerary could be generated."
        ),
    )

    # --------------------------------------------------
    # 11. Replanning decision
    # --------------------------------------------------

    state["replan_required"] = (
        best_plan is None
    )

    return state


# ==================================================
# EVALUATE TRAVEL PLAN
# ==================================================

def evaluate_travel_plan(
    state: TravelState,
) -> TravelState:

    evaluation = evaluate_plan(
        state.get("selected_plan"),
        state,
    )

    state["evaluation_result"] = (
        evaluation
    )

    # --------------------------------------------------
    # Conflict detection
    # --------------------------------------------------

    conflicts = detect_conflicts(
        state.get("selected_plan"),
        state,
        evaluation,
    )

    state["conflicts"] = conflicts

    if conflicts:

        add_trace(
            state,
            "conflict_detection",
            "warning",
            (
                f"Detected {len(conflicts)} "
                "planning conflict(s)."
            ),
        )

    else:

        add_trace(
            state,
            "conflict_detection",
            "success",
            "No planning conflicts detected.",
        )

    # --------------------------------------------------
    # Evaluation trace
    # --------------------------------------------------

    if evaluation.get("passed"):

        add_trace(
            state,
            "plan_evaluation",
            "success",
            "Selected plan passed deterministic evaluation.",
        )

    else:

        add_trace(
            state,
            "plan_evaluation",
            "warning",
            "Selected plan failed deterministic evaluation.",
        )

    # --------------------------------------------------
    # Persist itinerary + evaluation
    # --------------------------------------------------

    if state.get("selected_plan"):

        persist_itinerary(
            state
        )

        persist_evaluation(
            state
        )

    # --------------------------------------------------
    # Persist complete high-level trace
    # --------------------------------------------------

    persist_agent_trace(
        state
    )

    # --------------------------------------------------
    # Complete planning run
    # --------------------------------------------------

    complete_planning_run(
        state
    )

    return state


# ==================================================
# AUTOMATIC REPLANNING
# ==================================================

def replan_travel_node(
    state: TravelState,
) -> TravelState:
    """
    Run a bounded automatic replanning attempt.
    """

    result = replan_travel(
        state
    )

    state["replan_count"] = result[
        "replan_count"
    ]

    state["candidate_plans"] = result[
        "candidate_plans"
    ]

    state["selected_plan"] = result[
        "selected_plan"
    ]

    state["replan_required"] = result[
        "replan_required"
    ]

    # --------------------------------------------------
    # Trace replanning
    # --------------------------------------------------

    add_trace(
        state,
        "replan_travel",
        (
            "completed"
            if state["selected_plan"]
            else "no_feasible_plan"
        ),
        result["message"],
    )

    return state


# ==================================================
# USER-INITIATED REPLANNING
# ==================================================

def user_replan_node(
    state: TravelState,
) -> TravelState:
    """
    Apply changes requested by the user and
    prepare the state for a fresh planning cycle.
    """

    add_trace(
        state,
        "user_replan",
        "started",
        "Applying user-requested trip changes.",
    )

    updated_state = (
        apply_user_replan_changes(
            state
        )
    )

    # --------------------------------------------------
    # Start a new planning run
    # --------------------------------------------------

    updated_state.pop(
        "planning_run_id",
        None,
    )

    updated_state.pop(
        "itinerary_id",
        None,
    )

    add_trace(
        updated_state,
        "user_replan",
        "completed",
        (
            "User-requested changes were applied "
            "and the previous plan was cleared."
        ),
    )

    return updated_state