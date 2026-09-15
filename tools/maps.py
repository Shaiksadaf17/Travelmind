from typing import Any


def get_route(
    origin: str,
    destination: str,
) -> dict[str, Any]:

    return {
        "status": "ok",
        "message": "Route data retrieved successfully.",
        "data": {
            "origin": origin,
            "destination": destination,
            "distance_km": 450,
            "travel_time_hours": 2.5,
            "transport": "Train",
        },
    }