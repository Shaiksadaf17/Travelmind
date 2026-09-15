import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ==================================================
# ENVIRONMENT
# ==================================================

# Always load the .env from the TravelMind project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

if not SERPAPI_API_KEY:
    raise ValueError(
        "SERPAPI_API_KEY is missing from .env"
    )


# ==================================================
# TOP-30 CITY → PRIMARY AIRPORT
# ==================================================

CITY_TO_AIRPORT = {
    "Paris": "CDG",
    "London": "LHR",
    "Rome": "FCO",
    "Barcelona": "BCN",
    "Amsterdam": "AMS",
    "Dubai": "DXB",
    "Istanbul": "IST",
    "New York": "JFK",
    "Tokyo": "NRT",
    "Singapore": "SIN",
    "Bangkok": "BKK",
    "Lisbon": "LIS",
    "Prague": "PRG",
    "Vienna": "VIE",
    "Madrid": "MAD",
    "Berlin": "BER",
    "Copenhagen": "CPH",
    "Athens": "ATH",
    "Seoul": "ICN",
    "Hong Kong": "HKG",
    "Sydney": "SYD",
    "Melbourne": "MEL",
    "Toronto": "YYZ",
    "Los Angeles": "LAX",
    "San Francisco": "SFO",
    "Zurich": "ZRH",
    "Budapest": "BUD",
    "Dublin": "DUB",
    "Edinburgh": "EDI",
    "Kuala Lumpur": "KUL",
}


# ==================================================
# CITY NORMALISATION
# ==================================================

def _normalise_city(city: str) -> str:
    """
    Convert values such as:

        London
        London, United Kingdom

    into:

        London
    """

    if not city:
        return ""

    city = str(city).strip()

    if "," in city:
        city = city.split(",", 1)[0].strip()

    return city


# ==================================================
# AIRPORT LOOKUP
# ==================================================

def _get_airport_code(city: str) -> str:
    """
    Convert a TravelMind city into its primary
    IATA airport code.
    """

    city_name = _normalise_city(city)

    airport = CITY_TO_AIRPORT.get(city_name)

    if not airport:
        raise ValueError(
            f"No airport mapping found for TravelMind city: "
            f"{city_name}"
        )

    return airport


# ==================================================
# FLIGHT SEARCH
# ==================================================

def search_flights(
    origin: str,
    destination: str,
    start_date: date,
    end_date: date,
    travellers: int = 1,
) -> List[Dict[str, Any]]:
    """
    Search real round-trip flights using
    SerpApi Google Flights.

    Returns a list of normalised flight dictionaries.
    """

    # --------------------------------------------------
    # NORMALISE CITIES
    # --------------------------------------------------

    origin_city = _normalise_city(origin)
    destination_city = _normalise_city(destination)

    if not origin_city or not destination_city:
        print("[Flights] Origin or destination is empty.")
        return []

    # --------------------------------------------------
    # SAME CITY CHECK
    # --------------------------------------------------

    if origin_city.lower() == destination_city.lower():
        print(
            "[Flights] Origin and destination cannot "
            "be the same city."
        )
        return []

    # --------------------------------------------------
    # TRAVELLER VALIDATION
    # --------------------------------------------------

    try:
        travellers = max(int(travellers), 1)
    except (TypeError, ValueError):
        travellers = 1

    # --------------------------------------------------
    # AIRPORT LOOKUP
    # --------------------------------------------------

    try:
        departure_airport = _get_airport_code(
            origin_city
        )

        arrival_airport = _get_airport_code(
            destination_city
        )

    except ValueError as exc:
        print(f"[Flights] {exc}")
        return []

    # --------------------------------------------------
    # DATE VALIDATION
    # --------------------------------------------------

    try:
        outbound = (
            start_date
            if isinstance(start_date, date)
            else date.fromisoformat(
                str(start_date)
            )
        )

        inbound = (
            end_date
            if isinstance(end_date, date)
            else date.fromisoformat(
                str(end_date)
            )
        )

        if inbound <= outbound:
            print(
                "[Flights] Return date must be "
                "after departure date."
            )
            return []

    except (TypeError, ValueError) as exc:
        print(
            f"[Flights] Invalid dates: {exc}"
        )
        return []

    # --------------------------------------------------
    # SERPAPI PARAMETERS
    # --------------------------------------------------

    params = {
        "engine": "google_flights",
        "departure_id": departure_airport,
        "arrival_id": arrival_airport,
        "outbound_date": outbound.isoformat(),
        "return_date": inbound.isoformat(),
        "currency": "GBP",
        "hl": "en",
        "gl": "uk",
        "adults": travellers,
        "type": "1",
        "sort_by": "2",
        "api_key": SERPAPI_API_KEY,
    }

    # --------------------------------------------------
    # API REQUEST
    # --------------------------------------------------

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as exc:
        print(
            f"[Flights] Request failed: {exc}"
        )
        return []

    except ValueError as exc:
        print(
            f"[Flights] Invalid JSON response: {exc}"
        )
        return []

    # --------------------------------------------------
    # SERPAPI ERROR
    # --------------------------------------------------

    if not isinstance(data, dict):
        print(
            "[Flights] Unexpected API response format."
        )
        return []

    if data.get("error"):
        print(
            f"[Flights] SerpApi error: "
            f"{data['error']}"
        )
        return []

    # --------------------------------------------------
    # COLLECT FLIGHT GROUPS
    # --------------------------------------------------

    flight_groups: List[Dict[str, Any]] = []

    best_flights = data.get(
        "best_flights",
        [],
    )

    other_flights = data.get(
        "other_flights",
        [],
    )

    if isinstance(best_flights, list):
        flight_groups.extend(
            best_flights
        )

    if isinstance(other_flights, list):
        flight_groups.extend(
            other_flights
        )

    # --------------------------------------------------
    # NORMALISE FLIGHTS
    # --------------------------------------------------

    flights: List[Dict[str, Any]] = []

    for flight in flight_groups:

        if not isinstance(flight, dict):
            continue

        # --------------------------------------------------
        # PRICE
        # --------------------------------------------------

        price = flight.get("price")

        if price is None:
            continue

        try:
            total_price = float(price)

        except (TypeError, ValueError):
            continue

        if total_price <= 0:
            continue

        # --------------------------------------------------
        # SEGMENTS
        # --------------------------------------------------

        segments = flight.get(
            "flights",
            [],
        )

        if not isinstance(
            segments,
            list,
        ):
            segments = []

        airline = "Unknown airline"
        departure_time = None
        arrival_time = None

        # --------------------------------------------------
        # FIRST SEGMENT
        # --------------------------------------------------

        if segments:

            first_segment = (
                segments[0]
                if isinstance(
                    segments[0],
                    dict,
                )
                else {}
            )

            airline = (
                first_segment.get(
                    "airline"
                )
                or "Unknown airline"
            )

            departure_airport_data = (
                first_segment.get(
                    "departure_airport",
                    {},
                )
            )

            if isinstance(
                departure_airport_data,
                dict,
            ):
                departure_time = (
                    departure_airport_data.get(
                        "time"
                    )
                )

        # --------------------------------------------------
        # LAST SEGMENT
        # --------------------------------------------------

        if segments:

            last_segment = (
                segments[-1]
                if isinstance(
                    segments[-1],
                    dict,
                )
                else {}
            )

            arrival_airport_data = (
                last_segment.get(
                    "arrival_airport",
                    {},
                )
            )

            if isinstance(
                arrival_airport_data,
                dict,
            ):
                arrival_time = (
                    arrival_airport_data.get(
                        "time"
                    )
                )

        # --------------------------------------------------
        # DURATION
        # --------------------------------------------------

        duration_minutes = flight.get(
            "total_duration"
        )

        try:

            if duration_minutes is not None:
                duration_hours = (
                    float(duration_minutes)
                    / 60
                )
            else:
                duration_hours = 2.0

        except (
            TypeError,
            ValueError,
        ):
            duration_hours = 2.0

        # --------------------------------------------------
        # STOPS
        # --------------------------------------------------

        stops = flight.get(
            "stops",
            0,
        )

        try:
            stops = int(stops or 0)
        except (
            TypeError,
            ValueError,
        ):
            stops = 0

        # --------------------------------------------------
        # NORMALISED RESULT
        # --------------------------------------------------

        flights.append(
            {
                "airline": airline,
                "origin": origin_city,
                "destination": destination_city,

                "departure_airport": (
                    departure_airport
                ),

                "arrival_airport": (
                    arrival_airport
                ),

                "departure_date": (
                    outbound.isoformat()
                ),

                "return_date": (
                    inbound.isoformat()
                ),

                "departure_time": (
                    departure_time
                ),

                "arrival_time": (
                    arrival_time
                ),

                "stops": stops,

                "duration_hours": round(
                    duration_hours,
                    2,
                ),

                "price_per_person": round(
                    total_price
                    / travellers,
                    2,
                ),

                "total_price": round(
                    total_price,
                    2,
                ),

                "currency": "GBP",

                "travellers": travellers,
            }
        )

    # --------------------------------------------------
    # SORT BY PRICE
    # --------------------------------------------------

    flights.sort(
        key=lambda flight: flight.get(
            "total_price",
            float("inf"),
        )
    )

    # --------------------------------------------------
    # RETURN TOP 10
    # --------------------------------------------------

    return flights[:10]