from math import radians, sin, cos, sqrt, atan2
from typing import Any


# ==================================================
# DISTANCE CALCULATION
# ==================================================

def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate distance between two coordinates
    using the Haversine formula.

    Returns distance in kilometres.
    """

    earth_radius_km = 6371.0

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad)
        * cos(lat2_rad)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return earth_radius_km * c


# ==================================================
# ROUTE OPTIMISATION
# ==================================================

def optimise_daily_route(
    attractions: list[dict[str, Any]],
    max_hours: float = 8.0,
    average_speed_kmh: float = 4.5,
) -> list[dict[str, Any]]:
    """
    Create a geographically efficient attraction route.

    The optimiser considers:

    - attraction duration
    - geographic distance
    - estimated walking/travel time
    - maximum daily activity time
    - attraction rating

    Attractions without coordinates are still supported.
    """

    if not attractions:
        return []

    remaining = attractions.copy()

    selected: list[dict[str, Any]] = []

    total_activity_hours = 0.0
    total_travel_hours = 0.0

    current_location = None

    while remaining:

        best_attraction = None
        best_score = float("-inf")
        best_travel_hours = 0.0

        for attraction in remaining:

            duration = float(
                attraction.get(
                    "duration_hours",
                    2.0,
                )
            )

            latitude = attraction.get(
                "latitude"
            )

            longitude = attraction.get(
                "longitude"
            )

            # ------------------------------------------
            # Estimate travel time
            # ------------------------------------------

            travel_hours = 0.0

            if (
                current_location is not None
                and latitude is not None
                and longitude is not None
            ):

                distance_km = haversine_distance(
                    current_location["latitude"],
                    current_location["longitude"],
                    float(latitude),
                    float(longitude),
                )

                travel_hours = (
                    distance_km
                    / average_speed_kmh
                )

            # ------------------------------------------
            # Check daily time constraint
            # ------------------------------------------

            projected_hours = (
                total_activity_hours
                + total_travel_hours
                + travel_hours
                + duration
            )

            if projected_hours > max_hours:
                continue

            # ------------------------------------------
            # Attraction quality
            # ------------------------------------------

            rating = float(
                attraction.get(
                    "rating",
                    0,
                )
                or 0
            )

            reviews = float(
                attraction.get(
                    "reviews",
                    0,
                )
                or 0
            )

            # Log-scaled review contribution.
            review_score = (
                min(reviews, 100000)
                / 100000
            ) * 2

            # Prefer highly rated attractions,
            # while also avoiding unnecessary travel.
            score = (
                rating * 10
                + review_score
                - travel_hours * 8
            )

            if score > best_score:
                best_score = score
                best_attraction = attraction
                best_travel_hours = travel_hours

        # ------------------------------------------
        # No attraction fits remaining time
        # ------------------------------------------

        if best_attraction is None:
            break

        # ------------------------------------------
        # Add selected attraction
        # ------------------------------------------

        best_attraction = best_attraction.copy()

        best_attraction["estimated_travel_hours"] = round(
            best_travel_hours,
            2,
        )

        selected.append(
            best_attraction
        )

        total_activity_hours += float(
            best_attraction.get(
                "duration_hours",
                2.0,
            )
        )

        total_travel_hours += (
            best_travel_hours
        )

        latitude = best_attraction.get(
            "latitude"
        )

        longitude = best_attraction.get(
            "longitude"
        )

        if (
            latitude is not None
            and longitude is not None
        ):
            current_location = {
                "latitude": float(latitude),
                "longitude": float(longitude),
            }

        remaining.remove(
            next(
                attraction
                for attraction in remaining
                if attraction.get("name")
                == best_attraction.get("name")
            )
        )

    return selected