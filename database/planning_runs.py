from database.supabase_client import supabase


def create_planning_run(
    trip_id,
    run_number,
    status="started",
    iteration_count=0,
):
    response = (
        supabase
        .table("planning_runs")
        .insert(
            {
                "trip_id": trip_id,
                "run_number": run_number,
                "status": status,
                "iteration_count": iteration_count,
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Planning run could not be created."
        )

    return response.data[0]


def update_planning_run(
    run_id,
    status=None,
    iteration_count=None,
):
    updates = {}

    if status is not None:
        updates["status"] = status

    if iteration_count is not None:
        updates["iteration_count"] = iteration_count

    if not updates:
        return None

    response = (
        supabase
        .table("planning_runs")
        .update(updates)
        .eq("run_id", run_id)
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Planning run could not be updated."
        )

    return response.data[0]