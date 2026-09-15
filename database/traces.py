from database.supabase_client import supabase


def create_trace(
    run_id,
    step,
    action,
    status,
    message,
):
    """
    Store one high-level agent trace event.
    """

    response = (
        supabase
        .table("agent_trace")
        .insert(
            {
                "run_id": run_id,
                "step": step,
                "action": action,
                "status": status,
                "message": message,
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Agent trace could not be created."
        )

    return response.data[0]


def create_traces(
    run_id,
    trace_events,
):
    """
    Store multiple agent trace events.
    """

    if not trace_events:
        return []

    records = []

    for trace in trace_events:

        records.append(
            {
                "run_id": run_id,
                "step": trace.get("step"),
                "action": trace.get("action"),
                "status": trace.get("status"),
                "message": trace.get("message"),
            }
        )

    response = (
        supabase
        .table("agent_trace")
        .insert(records)
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Agent traces could not be created."
        )

    return response.data


def get_traces_for_run(run_id):
    """
    Retrieve the high-level agent journey
    for a planning run.
    """

    response = (
        supabase
        .table("agent_trace")
        .select("*")
        .eq("run_id", run_id)
        .order("step")
        .execute()
    )

    return response.data