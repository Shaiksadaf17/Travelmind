from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from agent.state import TravelState

from agent.nodes import (
    understand_request,
    collect_travel_data,
    create_travel_plan,
    evaluate_travel_plan,
    replan_travel_node,
    user_replan_node,
)


MAX_REPLANS = 3


def should_replan(
    state: TravelState,
) -> str:
    """
    Decide whether the graph should perform
    an automatic replan or finish.
    """

    if (
        state.get("replan_required", False)
        and state.get("replan_count", 0)
        < MAX_REPLANS
    ):
        return "replan"

    return "finish"


def route_initial_request(
    state: TravelState,
) -> str:
    """
    Decide whether the graph is handling a new
    trip request or a user-initiated replan.
    """

    if state.get(
        "user_replan_requested",
        False,
    ):
        return "user_replan"

    return "understand_request"


def build_travel_graph():

    graph = StateGraph(TravelState)

    # --------------------------------------------------
    # Nodes
    # --------------------------------------------------

    graph.add_node(
        "understand_request",
        understand_request,
    )

    graph.add_node(
        "collect_travel_data",
        collect_travel_data,
    )

    graph.add_node(
        "create_travel_plan",
        create_travel_plan,
    )

    graph.add_node(
        "evaluate_travel_plan",
        evaluate_travel_plan,
    )

    graph.add_node(
        "replan_travel",
        replan_travel_node,
    )

    graph.add_node(
        "user_replan",
        user_replan_node,
    )

    # --------------------------------------------------
    # Initial routing
    # --------------------------------------------------

    graph.add_conditional_edges(
        START,
        route_initial_request,
        {
            "user_replan": "user_replan",
            "understand_request": "understand_request",
        },
    )

    # --------------------------------------------------
    # Normal new-trip workflow
    # --------------------------------------------------

    graph.add_edge(
        "understand_request",
        "collect_travel_data",
    )

    graph.add_edge(
        "collect_travel_data",
        "create_travel_plan",
    )

    graph.add_edge(
        "create_travel_plan",
        "evaluate_travel_plan",
    )

    # --------------------------------------------------
    # Conditional automatic replan
    # --------------------------------------------------

    graph.add_conditional_edges(
        "evaluate_travel_plan",
        should_replan,
        {
            "replan": "replan_travel",
            "finish": END,
        },
    )

    # --------------------------------------------------
    # Automatic replan → evaluate again
    # --------------------------------------------------

    graph.add_edge(
        "replan_travel",
        "evaluate_travel_plan",
    )

    # --------------------------------------------------
    # User-initiated replan → fresh travel data
    # --------------------------------------------------

    graph.add_edge(
        "user_replan",
        "collect_travel_data",
    )

    return graph.compile()


travel_graph = build_travel_graph()