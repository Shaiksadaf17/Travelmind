import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# ==================================================
# ENVIRONMENT
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


# ==================================================
# CATEGORY MAPPING
# ==================================================

def classify_attraction(
    place: dict[str, Any],
) -> str:
    """
    Convert Google Maps place types into a
    simple category used by TravelMind.
    """

    types = [
        str(item).lower()
        for item in place.get("types", [])
    ]

    place_type = str(
        place.get("type", "")
    ).lower()

    all_types = types + [place_type]

    if any("museum" in item for item in all_types):
        return "Museum"

    if any("gallery" in item for item in all_types):
        return "Gallery"

    if any(
        keyword in item
        for item in all_types
        for keyword in ("park", "garden")
    ):
        return "Park"

    if any(
        keyword in item
        for item in all_types
        for keyword in (
            "monument",
            "landmark",
            "tourist attraction",
            "historical",
        )
    ):
        return "Sightseeing"

    return "Attraction"


# ==================================================
# ATTRACTION SEARCH
# ==================================================

def search_attractions(
    destination: str,
    preferences: str,
) -> dict[str, Any]:
    """
    Search real attractions using SerpApi Google Maps.
    """

    if not SERPAPI_API_KEY:
        return {
            "status": "error",
            "message": (
                "SERPAPI_API_KEY is missing from .env"
            ),
            "data": [],
        }

    destination = str(destination or "").strip()

    if not destination:
        return {
            "status": "error",
            "message": "Destination is required.",
            "data": [],
        }

    preference_text = str(
        preferences or ""
    ).strip()

    if preference_text:
        query = (
            f"top attractions in "
            f"{destination} "
            f"{preference_text}"
        )
    else:
        query = (
            f"top attractions in "
            f"{destination}"
        )

    params = {
        "engine": "google_maps",
        "q": query,
        "type": "search",
        "api_key": SERPAPI_API_KEY,
        "hl": "en",
        "gl": "uk",
    }

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=(5, 15),
        )

        response.raise_for_status()

        result = response.json()

        if result.get("error"):
            return {
                "status": "error",
                "message": str(result["error"]),
                "data": [],
            }

        local_results = result.get(
            "local_results",
            [],
        )

        if not isinstance(local_results, list):
            local_results = []

        if not local_results:
            return {
                "status": "limited",
                "message": (
                    f"No attractions were found "
                    f"for {destination}."
                ),
                "data": [],
            }

        attractions = []

        for place in local_results:

            if not isinstance(place, dict):
                continue

            gps = place.get(
                "gps_coordinates",
                {},
            )

            if not isinstance(gps, dict):
                gps = {}

            operating_hours = place.get(
                "operating_hours",
                {},
            )

            if not isinstance(
                operating_hours,
                dict,
            ):
                operating_hours = {}

            rating = place.get(
                "rating",
                None,
            )

            try:
                if rating is not None:
                    rating = float(rating)
            except (TypeError, ValueError):
                rating = None

            reviews = place.get(
                "reviews",
                0,
            )

            try:
                reviews = int(reviews or 0)
            except (TypeError, ValueError):
                reviews = 0

            attractions.append(
                {
                    "name": place.get(
                        "title",
                        "Unknown attraction",
                    ),
                    "category": classify_attraction(
                        place
                    ),
                    "address": place.get(
                        "address",
                        "",
                    ),
                    "rating": rating,
                    "reviews": reviews,
                    "latitude": gps.get(
                        "latitude"
                    ),
                    "longitude": gps.get(
                        "longitude"
                    ),
                    "opening_hours": operating_hours,
                    "open_state": place.get(
                        "open_state",
                        "",
                    ),
                    "website": place.get(
                        "website",
                        "",
                    ),
                    "description": place.get(
                        "description",
                        "",
                    ),
                    "price": 0.0,
                    "duration_hours": 2.0,
                }
            )

        if not attractions:
            return {
                "status": "limited",
                "message": (
                    "Google Maps returned results, "
                    "but no usable attractions were found."
                ),
                "data": [],
            }

        return {
            "status": "ok",
            "message": (
                f"Retrieved {len(attractions)} "
                "attractions successfully."
            ),
            "data": attractions[:20],
        }

    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": (
                f"Attraction API request failed: {exc}"
            ),
            "data": [],
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": (
                f"Unexpected attraction search error: {exc}"
            ),
            "data": [],
        }