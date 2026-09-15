from database.supabase_client import supabase


def create_trip(user_id, trip):
    response = (
        supabase
        .table("trips")
        .insert(
            {
                "user_id": user_id,
                "origin": trip["origin"],
                "destination": trip["destination"],
                "start_date": str(trip["start_date"]),
                "end_date": str(trip["end_date"]),
                "travellers": trip["travellers"],
                "budget": trip["budget"],
                "preferences": trip["preferences"],
                "priorities": trip["priorities"],
                "is_saved": False,
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Trip could not be created."
        )

    return response.data[0]


def mark_trip_as_saved(trip_id):
    response = (
        supabase
        .table("trips")
        .update(
            {
                "is_saved": True,
            }
        )
        .eq(
            "trip_id",
            trip_id,
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Travel plan could not be marked as saved."
        )

    return response.data[0]


def get_trip(trip_id):
    response = (
        supabase
        .table("trips")
        .select("*")
        .eq(
            "trip_id",
            trip_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]