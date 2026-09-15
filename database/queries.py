from database.supabase_client import supabase


def create_query(
    run_id,
    tool_name,
    query_parameters=None,
):
    response = (
        supabase
        .table("queries")
        .insert(
            {
                "run_id": run_id,
                "tool_name": tool_name,
                "query_parameters": query_parameters or {},
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Query could not be created."
        )

    return response.data[0]


def get_queries_for_run(run_id):
    response = (
        supabase
        .table("queries")
        .select("*")
        .eq("run_id", run_id)
        .order("created_at")
        .execute()
    )

    return response.data