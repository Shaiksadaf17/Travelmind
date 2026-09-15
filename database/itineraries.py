from database.supabase_client import supabase


def create_itinerary_version(
    trip_id,
    run_id,
    version,
    plan_data,
    total_cost,
    status="generated",
    is_final=False,
    is_saved=False,
):
    response = (
        supabase
        .table("itinerary_versions")
        .insert(
            {
                "trip_id": trip_id,
                "run_id": run_id,
                "version": version,
                "plan_data": plan_data,
                "total_cost": total_cost,
                "status": status,
                "is_final": is_final,
                "is_saved": is_saved,
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Itinerary version could not be created."
        )

    return response.data[0]


def get_itineraries_for_trip(trip_id):
    response = (
        supabase
        .table("itinerary_versions")
        .select("*")
        .eq("trip_id", trip_id)
        .order("version")
        .execute()
    )

    return response.data


def mark_itinerary_as_final(itinerary_id):
    response = (
        supabase
        .table("itinerary_versions")
        .update(
            {
                "is_final": True,
            }
        )
        .eq("itinerary_id", itinerary_id)
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Itinerary could not be marked as final."
        )

    return response.data[0]


def mark_itinerary_as_saved(itinerary_id):
    response = (
        supabase
        .table("itinerary_versions")
        .update(
            {
                "is_saved": True,
                "status": "saved",
            }
        )
        .eq("itinerary_id", itinerary_id)
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Itinerary could not be marked as saved."
        )

    return response.data[0]