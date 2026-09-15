from database.supabase_client import supabase


def get_saved_trips(user_id):
    response = (
        supabase
        .table("trips")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_saved", True)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data