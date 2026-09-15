from database.supabase_client import supabase


def create_tool_result(
    query_id,
    tool_name,
    status,
    result_data=None,
    message=None,
):
    response = (
        supabase
        .table("tool_results")
        .insert(
            {
                "query_id": query_id,
                "tool_name": tool_name,
                "status": status,
                "result_data": result_data or {},
                "message": message,
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Tool result could not be created."
        )

    return response.data[0]


def get_tool_results_for_query(query_id):
    response = (
        supabase
        .table("tool_results")
        .select("*")
        .eq("query_id", query_id)
        .order("created_at")
        .execute()
    )

    return response.data