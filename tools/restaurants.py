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
# FOOD PREFERENCE
# ==================================================

def _normalise_food_preference(
    preferences: str,
) -> str:

    text = str(
        preferences or ""
    ).strip().lower()

    if "vegan" in text:
        return "Vegan"

    if (
        "non-vegetarian" in text
        or "non vegetarian" in text
    ):
        return "Non-Vegetarian"

    if "vegetarian" in text:
        return "Vegetarian"

    return "No Food Preference"


# ==================================================
# FOOD CLASSIFICATION
# ==================================================

def _is_probably_vegetarian(
    place: dict[str, Any],
) -> bool:

    text = " ".join(
        str(place.get(key, ""))
        for key in (
            "name",
            "title",
            "type",
            "category",
            "description",
            "cuisine",
        )
    ).lower()

    return any(
        word in text
        for word in (
            "vegetarian",
            "vegan",
            "plant-based",
            "plant based",
        )
    )


def _is_probably_vegan(
    place: dict[str, Any],
) -> bool:

    text = " ".join(
        str(place.get(key, ""))
        for key in (
            "name",
            "title",
            "type",
            "category",
            "description",
            "cuisine",
        )
    ).lower()

    return "vegan" in text


# ==================================================
# RESTAURANT SEARCH
# ==================================================

def search_restaurants(
    destination: str,
    preferences: str,
) -> dict[str, Any]:
    """
    Search real restaurants and cafes using
    SerpApi Google Maps.
    """

    if not SERPAPI_API_KEY:
        return {
            "status": "error",
            "message": (
                "SERPAPI_API_KEY is missing from .env"
            ),
            "data": [],
        }

    destination = str(
        destination or ""
    ).strip()

    if not destination:
        return {
            "status": "error",
            "message": "Destination is required.",
            "data": [],
        }

    food_preference = (
        _normalise_food_preference(
            preferences
        )
    )

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    query = (
        f"restaurants cafes food in {destination}"
    )

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_maps",
                "q": query,
                "type": "search",
                "api_key": SERPAPI_API_KEY,
                "hl": "en",
                "gl": "uk",
            },
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("error"):
            return {
                "status": "error",
                "message": str(
                    payload["error"]
                ),
                "data": [],
            }

        places = payload.get(
            "local_results",
            [],
        )

        if not isinstance(places, list):
            places = []

        restaurants = []

        # --------------------------------------------------
        # NORMALISE RESULTS
        # --------------------------------------------------

        for place in places:

            if not isinstance(place, dict):
                continue

            name = (
                place.get("title")
                or place.get("name")
            )

            if not name:
                continue

            place_type = str(
                place.get("type", "")
            ).lower()

            category = str(
                place.get(
                    "category",
                    place_type,
                )
            )

            combined_type = (
                f"{place_type} "
                f"{category}".lower()
            )

            # Google Maps may return restaurants/cafes
            # under slightly different type names.
            is_food_venue = any(
                keyword in combined_type
                for keyword in (
                    "restaurant",
                    "cafe",
                    "coffee",
                    "bakery",
                    "food",
                    "bistro",
                    "bar",
                    "pizzeria",
                    "brasserie",
                )
            )

            # Don't unnecessarily throw away a valid
            # Google Maps result if it has a rating.
            if not is_food_venue:
                if not place.get("rating"):
                    continue

            rating = place.get(
                "rating",
                0,
            )

            reviews = place.get(
                "reviews",
                0,
            )

            try:
                rating = float(
                    rating or 0
                )
            except (TypeError, ValueError):
                rating = 0.0

            try:
                reviews = int(
                    reviews or 0
                )
            except (TypeError, ValueError):
                reviews = 0

            price_level = place.get(
                "price",
                None,
            )

            gps = place.get(
                "gps_coordinates",
                {},
            )

            if not isinstance(gps, dict):
                gps = {}

            restaurants.append(
                {
                    "name": name,
                    "cuisine": place.get(
                        "type",
                        "Restaurant",
                    ),
                    "category": place.get(
                        "type",
                        "Restaurant",
                    ),
                    "price_level": price_level,
                    "price": price_level,
                    "rating": rating,
                    "reviews": reviews,
                    "address": place.get(
                        "address",
                        "",
                    ),
                    "website": place.get(
                        "website",
                        "",
                    ),
                    "phone": place.get(
                        "phone",
                        "",
                    ),
                    "latitude": gps.get(
                        "latitude"
                    ),
                    "longitude": gps.get(
                        "longitude"
                    ),
                    "vegetarian": (
                        _is_probably_vegetarian(
                            place
                        )
                    ),
                    "vegan": (
                        _is_probably_vegan(
                            place
                        )
                    ),
                    "food_preference": (
                        food_preference
                    ),
                }
            )

        # --------------------------------------------------
        # PREFERENCE-AWARE RANKING
        # --------------------------------------------------

        if food_preference == "Vegetarian":

            restaurants.sort(
                key=lambda r: (
                    not r["vegetarian"],
                    -r["rating"],
                    r["price_level"] is None,
                )
            )

        elif food_preference == "Vegan":

            restaurants.sort(
                key=lambda r: (
                    not r["vegan"],
                    not r["vegetarian"],
                    -r["rating"],
                )
            )

        elif food_preference == "Non-Vegetarian":

            restaurants.sort(
                key=lambda r: (
                    r["category"].lower()
                    == "cafe",
                    -r["rating"],
                )
            )

        else:

            restaurants.sort(
                key=lambda r: -r["rating"]
            )

        # --------------------------------------------------
        # RETURN
        # --------------------------------------------------

        if not restaurants:
            return {
                "status": "limited",
                "message": (
                    "No restaurant or cafe results "
                    "were returned."
                ),
                "data": [],
            }

        return {
            "status": "ok",
            "message": (
                f"{len(restaurants)} "
                "restaurant/cafe options retrieved."
            ),
            "data": restaurants[:20],
        }

    except requests.RequestException as exc:

        return {
            "status": "error",
            "message": (
                f"Restaurant search failed: {exc}"
            ),
            "data": [],
        }

    except Exception as exc:

        return {
            "status": "error",
            "message": (
                f"Restaurant processing failed: {exc}"
            ),
            "data": [],
        }