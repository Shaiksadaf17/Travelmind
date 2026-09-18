import os
from datetime import date
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
# HOTEL SEARCH
# ==================================================

def search_hotels(
    destination: str,
    start_date: str,
    end_date: str,
    travellers: int,
) -> dict[str, Any]:
    """
    Search real hotels using SerpApi Google Hotels.

    Returns:
        {
            "status": "ok" | "error" | "limited",
            "message": str,
            "data": list
        }
    """

    # --------------------------------------------------
    # API KEY CHECK
    # --------------------------------------------------

    if not SERPAPI_API_KEY:
        return {
            "status": "error",
            "message": "SERPAPI_API_KEY is missing from .env",
            "data": [],
        }

    # --------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------

    destination = str(destination or "").strip()

    if not destination:
        return {
            "status": "error",
            "message": "Destination is required.",
            "data": [],
        }

    if travellers < 1:
        return {
            "status": "error",
            "message": "Travellers must be at least 1.",
            "data": [],
        }

    try:
        check_in = date.fromisoformat(str(start_date))
        check_out = date.fromisoformat(str(end_date))

        if check_out <= check_in:
            return {
                "status": "error",
                "message": "End date must be after start date.",
                "data": [],
            }

    except ValueError:
        return {
            "status": "error",
            "message": "Dates must use YYYY-MM-DD format.",
            "data": [],
        }

    number_of_nights = (check_out - check_in).days

    # --------------------------------------------------
    # GOOGLE HOTELS PARAMETERS
    # --------------------------------------------------

    params = {
        "engine": "google_hotels",
        "api_key": SERPAPI_API_KEY,
        "q": f"hotels in {destination}",
        "check_in_date": str(start_date),
        "check_out_date": str(end_date),
        "adults": travellers,
        "currency": "GBP",
        "gl": "uk",
        "hl": "en",
    }

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=(5, 15),
        )

        response.raise_for_status()

        result = response.json()

        # --------------------------------------------------
        # SERPAPI ERROR
        # --------------------------------------------------

        if result.get("error"):
            return {
                "status": "error",
                "message": str(result["error"]),
                "data": [],
            }

        # --------------------------------------------------
        # HOTEL RESULTS
        # --------------------------------------------------

        properties = result.get("properties", [])

        if not isinstance(properties, list):
            properties = []

        if not properties:
            return {
                "status": "limited",
                "message": (
                    f"No hotels were found in {destination} "
                    f"for {start_date} to {end_date}."
                ),
                "data": [],
            }

        hotels = []

        for property_data in properties:

            if not isinstance(property_data, dict):
                continue

            # Ignore obvious non-hotel properties.
            property_type = str(
                property_data.get("type", "")
            ).lower()

            if property_type and property_type not in {
                "hotel",
                "lodging",
                "resort",
            }:
                continue

            # --------------------------------------------------
            # PRICE
            # --------------------------------------------------

            rate_per_night = property_data.get(
                "rate_per_night",
                {},
            )

            total_rate = property_data.get(
                "total_rate",
                {},
            )

            if not isinstance(rate_per_night, dict):
                rate_per_night = {}

            if not isinstance(total_rate, dict):
                total_rate = {}

            nightly_price = rate_per_night.get(
                "extracted_lowest"
            )

            total_price = total_rate.get(
                "extracted_lowest"
            )

            # Some SerpApi responses may expose a price
            # directly rather than inside extracted_lowest.
            if nightly_price is None:
                nightly_price = rate_per_night.get("lowest")

            if total_price is None:
                total_price = total_rate.get("lowest")

            try:
                nightly_price = (
                    float(nightly_price)
                    if nightly_price is not None
                    else None
                )
            except (TypeError, ValueError):
                nightly_price = None

            try:
                total_price = (
                    float(total_price)
                    if total_price is not None
                    else None
                )
            except (TypeError, ValueError):
                total_price = None

            # --------------------------------------------------
            # CALCULATE TOTAL WHEN NECESSARY
            # --------------------------------------------------

            if (
                total_price is None
                and nightly_price is not None
            ):
                total_price = (
                    nightly_price * number_of_nights
                )

            if nightly_price is None:
                continue

            if total_price is None:
                continue

            # --------------------------------------------------
            # OTHER DATA
            # --------------------------------------------------

            rating = property_data.get(
                "overall_rating",
                0,
            )

            reviews = property_data.get(
                "reviews",
                0,
            )

            try:
                rating = float(rating or 0)
            except (TypeError, ValueError):
                rating = 0.0

            try:
                reviews = int(reviews or 0)
            except (TypeError, ValueError):
                reviews = 0

            gps = property_data.get(
                "gps_coordinates",
                {},
            )

            if not isinstance(gps, dict):
                gps = {}

            amenities = property_data.get(
                "amenities",
                [],
            )

            if not isinstance(amenities, list):
                amenities = []

            hotels.append(
                {
                    "name": property_data.get(
                        "name",
                        "Unknown Hotel",
                    ),
                    "description": property_data.get(
                        "description",
                        "",
                    ),
                    "address": property_data.get(
                        "address",
                        "",
                    ),
                    "location": property_data.get(
                        "address",
                        destination,
                    ),
                    "rating": rating,
                    "reviews": reviews,
                    "price_per_night": nightly_price,
                    "total_price": total_price,
                    "currency": "GBP",
                    "nights": number_of_nights,
                    "amenities": amenities,
                    "latitude": gps.get("latitude"),
                    "longitude": gps.get("longitude"),
                    "check_in_time": property_data.get(
                        "check_in_time",
                        "",
                    ),
                    "check_out_time": property_data.get(
                        "check_out_time",
                        "",
                    ),
                    "website": property_data.get(
                        "link",
                        "",
                    ),
                    "property_token": property_data.get(
                        "property_token",
                        "",
                    ),
                    "sponsored": property_data.get(
                        "sponsored",
                        False,
                    ),
                }
            )

        # --------------------------------------------------
        # NO USABLE RESULTS
        # --------------------------------------------------

        if not hotels:
            return {
                "status": "limited",
                "message": (
                    "Hotel results were returned, "
                    "but no usable priced hotels were found."
                ),
                "data": [],
            }

        # --------------------------------------------------
        # SORT CHEAPEST FIRST
        # --------------------------------------------------

        hotels.sort(
            key=lambda hotel: hotel["total_price"]
        )

        return {
            "status": "ok",
            "message": (
                f"Retrieved {len(hotels)} "
                "hotel options successfully."
            ),
            "data": hotels[:20],
        }

    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": f"Hotel API request failed: {exc}",
            "data": [],
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Unexpected hotel search error: {exc}",
            "data": [],
        }