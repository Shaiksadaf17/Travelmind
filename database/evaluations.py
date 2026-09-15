from database.supabase_client import supabase


def create_evaluation(
    run_id,
    itinerary_id,
    evaluation,
):
    """
    Store the deterministic evaluation result
    for a planning run and itinerary version.
    """

    evaluation = evaluation or {}

    response = (
        supabase
        .table("evaluations")
        .insert(
            {
                "run_id": run_id,
                "itinerary_id": itinerary_id,
                "passed": evaluation.get(
                    "passed",
                    False,
                ),
                "score": evaluation.get(
                    "score",
                    0,
                ),
                "budget_check": evaluation.get(
                    "budget",
                    {},
                ),
                "constraint_check": evaluation.get(
                    "constraints",
                    {},
                ),
                "preference_check": evaluation.get(
                    "preferences",
                    {},
                ),
                "route_check": evaluation.get(
                    "route",
                    {},
                ),
                "weather_check": evaluation.get(
                    "weather",
                    {},
                ),
                "data_quality": evaluation.get(
                    "data_quality",
                    {},
                ),
                "warnings": evaluation.get(
                    "warnings",
                    [],
                ),
            }
        )
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Evaluation could not be created."
        )

    return response.data[0]


def get_evaluations_for_run(run_id):
    """
    Retrieve all evaluations belonging
    to a planning run.
    """

    response = (
        supabase
        .table("evaluations")
        .select("*")
        .eq("run_id", run_id)
        .order("created_at")
        .execute()
    )

    return response.data


def get_evaluation_for_itinerary(itinerary_id):
    """
    Retrieve the evaluation associated
    with an itinerary version.
    """

    response = (
        supabase
        .table("evaluations")
        .select("*")
        .eq(
            "itinerary_id",
            itinerary_id,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]