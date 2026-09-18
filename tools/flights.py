import os
import os
import re
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

AIRPORT_TO_CITY = {code: city for city, code in CITY_TO_AIRPORT.items()}


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
# FLIGHT DETAIL HELPERS
# ==================================================

def _extract_datetime_parts(value: Any) -> tuple[Any, Any]:
    """Return ISO date and time parts from a SerpApi timestamp."""
    if not value:
        return None, None

    raw = str(value).strip()

    # SerpApi may return ISO timestamps such as:
    # "2026-09-18 12:50".
    iso_match = re.search(
        r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[ T]+(?P<time>\d{1,2}:\d{2}(?:\s*(?:AM|PM))?)",
        raw,
        re.IGNORECASE,
    )
    if iso_match:
        return f"{iso_match.group('year')}-{iso_match.group('month')}-{iso_match.group('day')}", iso_match.group('time')

    # SerpApi may also return values such as:
    # "Fri, Sep 18, 8:15 AM"
    # Keep the original value if it cannot be parsed reliably.
    match = re.search(
        r"(?P<month>[A-Za-z]{3,9})\s+(?P<day>\d{1,2}),?\s+(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM)?)",
        raw,
        re.IGNORECASE,
    )

    if not match:
        return None, raw

    month = match.group("month")
    day = int(match.group("day"))
    time_value = match.group("time").strip()

    month_lookup = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    month_number = month_lookup.get(month.lower())
    if not month_number:
        return None, time_value

    return f"{month_number:02d}-{day:02d}", time_value


def _airport_details(airport_data: Any, fallback_city: str) -> Dict[str, Any]:
    """Normalise a SerpApi airport object."""
    if not isinstance(airport_data, dict):
        airport_data = {}

    airport_code = (
        airport_data.get("id")
        or airport_data.get("code")
        or ""
    )

    airport_name = (
        airport_data.get("name")
        or airport_data.get("airport")
        or airport_code
        or "Unknown airport"
    )

    return {
        "name": airport_name,
        "code": airport_code,
        "city": (
            airport_data.get("city")
            or AIRPORT_TO_CITY.get(airport_code)
            or fallback_city
        ),
    }


def _normalise_segment(
    segment: Dict[str, Any],
    fallback_origin: str,
    fallback_destination: str,
) -> Dict[str, Any]:
    """Create a detailed, UI-friendly flight segment."""
    departure = segment.get("departure_airport", {})
    arrival = segment.get("arrival_airport", {})

    departure_details = _airport_details(
        departure,
        fallback_origin,
    )
    arrival_details = _airport_details(
        arrival,
        fallback_destination,
    )

    departure_raw = (
        departure.get("time")
        if isinstance(departure, dict)
        else None
    )
    arrival_raw = (
        arrival.get("time")
        if isinstance(arrival, dict)
        else None
    )

    departure_date_from_api, departure_time = _extract_datetime_parts(
        departure_raw
    )
    arrival_date_from_api, arrival_time = _extract_datetime_parts(
        arrival_raw
    )

    return {
        "airline": (
            segment.get("airline")
            or "Unknown airline"
        ),
        "flight_number": (
            segment.get("flight_number")
            or segment.get("flight_number_text")
            or "Unknown flight"
        ),
        "departure_airport": departure_details["code"],
        "departure_airport_name": departure_details["name"],
        "departure_city": departure_details["city"],
        "departure_time": departure_time or departure_raw,
        "departure_date_from_api": departure_date_from_api,
        "arrival_airport": arrival_details["code"],
        "arrival_airport_name": arrival_details["name"],
        "arrival_city": arrival_details["city"],
        "arrival_time": arrival_time or arrival_raw,
        "arrival_date_from_api": arrival_date_from_api,
        "duration_minutes": segment.get("duration"),
        "aircraft": segment.get("airplane"),
        "travel_class": segment.get("travel_class"),
    }


# ==================================================
# FLIGHT SEARCH
# ==================================================

def search_flights(
    origin: str,
    destination: str,
    start_date: date,
    end_date: date | None = None,
    travellers: int = 1,
    trip_type: str = "Round Trip",
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

        inbound = None
        if end_date is not None:
            inbound = (
                end_date
                if isinstance(end_date, date)
                else date.fromisoformat(str(end_date))
            )

        is_round_trip = str(trip_type).strip().lower() in {"round trip", "roundtrip", "return"}
        if is_round_trip and (inbound is None or inbound <= outbound):
            print("[Flights] A valid return date is required for Round Trip.")
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
        "return_date": inbound.isoformat() if inbound else None,
        "currency": "GBP",
        "hl": "en",
        "gl": "uk",
        "adults": travellers,
        "type": "1" if is_round_trip else "2",
        "sort_by": "2",
        "api_key": SERPAPI_API_KEY,
    }

    if not is_round_trip:
        params.pop("return_date", None)

    # --------------------------------------------------
    # API REQUEST
    # --------------------------------------------------

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=(5, 15),
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

        # --------------------------------------------------
        # DETAILED SEGMENTS
        # --------------------------------------------------

        normalised_segments: List[Dict[str, Any]] = []

        for segment in segments:
            if not isinstance(segment, dict):
                continue

            normalised_segments.append(
                _normalise_segment(
                    segment,
                    origin_city,
                    destination_city,
                )
            )

        # Keep a useful fallback if the API does not provide
        # segment-level airport information.
        first_segment = (
            normalised_segments[0]
            if normalised_segments
            else {}
        )
        last_segment = (
            normalised_segments[-1]
            if normalised_segments
            else {}
        )

        airline = (
            first_segment.get("airline")
            or "Unknown airline"
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
                    float(duration_minutes) / 60
                )
            else:
                duration_hours = 2.0
        except (TypeError, ValueError):
            duration_hours = 2.0

        # --------------------------------------------------
        # STOPS
        # --------------------------------------------------

        stops = flight.get("stops", 0)

        try:
            stops = int(stops or 0)
        except (TypeError, ValueError):
            stops = 0

        # --------------------------------------------------
        # DETAILED RESULT
        # --------------------------------------------------

        flights.append(
            {
                "airline": airline,

                "origin": origin_city,
                "destination": destination_city,

                # Primary airport codes.
                "departure_airport": (
                    first_segment.get(
                        "departure_airport"
                    )
                    or departure_airport
                ),
                "arrival_airport": (
                    last_segment.get(
                        "arrival_airport"
                    )
                    or arrival_airport
                ),

                # Human-readable airport names.
                "departure_airport_name": (
                    first_segment.get(
                        "departure_airport_name"
                    )
                    or "Unknown airport"
                ),
                "arrival_airport_name": (
                    last_segment.get(
                        "arrival_airport_name"
                    )
                    or "Unknown airport"
                ),

                "departure_city": (
                    first_segment.get(
                        "departure_city"
                    )
                    or origin_city
                ),
                "arrival_city": (
                    last_segment.get(
                        "arrival_city"
                    )
                    or destination_city
                ),

                # Requested trip dates remain authoritative
                # when the API does not expose a date.
                "departure_date": (
                    first_segment.get("departure_date_from_api")
                    or outbound.isoformat()
                ),
                "arrival_date": (
                    last_segment.get("arrival_date_from_api")
                    or outbound.isoformat()
                ),
                "return_date": inbound.isoformat() if inbound else None,

                "departure_time": (
                    first_segment.get(
                        "departure_time"
                    )
                ),
                "arrival_time": (
                    last_segment.get(
                        "arrival_time"
                    )
                ),

                "stops": stops,
                "duration_hours": round(
                    duration_hours,
                    2,
                ),

                "price_per_person": round(
                    total_price / travellers,
                    2,
                ),
                "total_price": round(
                    total_price,
                    2,
                ),

                "currency": "GBP",
                "travellers": travellers,

                # Full segment-by-segment detail for
                # connections and exact airport display.
                "segments": normalised_segments,
                "departure_token": flight.get("departure_token"),
                "booking_token": flight.get("booking_token"),
                "flight_type": "round_trip" if is_round_trip else "one_way",
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

# ==================================================
# RETURN FLIGHT SEARCH FROM SELECTED OUTBOUND
# ==================================================

def search_return_flights(
    origin: str,
    destination: str,
    return_date: date,
    travellers: int = 1,
    departure_token: str | None = None,
    outbound_date: date | None = None,
) -> List[Dict[str, Any]]:
    """Retrieve actual return options for a selected outbound flight."""
    if not departure_token:
        return []

    origin_city = _normalise_city(origin)
    destination_city = _normalise_city(destination)
    origin_airport = _get_airport_code(origin_city)
    destination_airport = _get_airport_code(destination_city)
    ret = return_date if isinstance(return_date, date) else date.fromisoformat(str(return_date))

    # SerpApi's Google Flights return-leg lookup uses the outbound
    # departure_token, but the request must still identify the original
    # round-trip search (type=1 plus the outbound/return dates and route).
    # Omitting these fields causes a 400 response for valid departure tokens.
    params = {
        "engine": "google_flights",
        "departure_id": origin_airport,
        "arrival_id": destination_airport,
        "outbound_date": (outbound_date if isinstance(outbound_date, date) else date.fromisoformat(str(outbound_date))).isoformat() if outbound_date else None,
        "return_date": ret.isoformat(),
        "type": "1",
        "departure_token": departure_token,
        "currency": "GBP",
        "hl": "en",
        "gl": "uk",
        "adults": max(int(travellers), 1),
        "api_key": SERPAPI_API_KEY,
    }
    if not params.get("outbound_date"):
        print("[Flights] Outbound date is required for return-flight lookup.")
        return []

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=(5, 15),
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"[Flights] Return-flight request failed: {exc}")
        return []
    except ValueError as exc:
        print(f"[Flights] Invalid return-flight JSON response: {exc}")
        return []
    groups = []
    groups.extend(data.get("best_flights", []) if isinstance(data.get("best_flights"), list) else [])
    groups.extend(data.get("other_flights", []) if isinstance(data.get("other_flights"), list) else [])

    results = []
    for item in groups:
        if not isinstance(item, dict) or not item.get("price"):
            continue
        segments = item.get("flights") if isinstance(item.get("flights"), list) else []
        normalised = [_normalise_segment(x, destination_city, origin_city) for x in segments if isinstance(x, dict)]
        if not normalised:
            continue
        first, last = normalised[0], normalised[-1]
        try:
            round_total = float(item.get("price"))
        except (TypeError, ValueError):
            continue
        results.append({
            "airline": first.get("airline", "Unknown airline"),
            "flight_number": first.get("flight_number", "Unknown flight"),
            "origin": destination_city,
            "destination": origin_city,
            "departure_airport": first.get("departure_airport") or destination_airport,
            "departure_airport_name": first.get("departure_airport_name", "Unknown airport"),
            "departure_city": first.get("departure_city", destination_city),
            "arrival_airport": last.get("arrival_airport") or origin_airport,
            "arrival_airport_name": last.get("arrival_airport_name", "Unknown airport"),
            "arrival_city": last.get("arrival_city", origin_city),
            "departure_date": ret.isoformat(),
            "arrival_date": last.get("arrival_date_from_api") or ret.isoformat(),
            "departure_time": first.get("departure_time"),
            "arrival_time": last.get("arrival_time"),
            "duration_hours": round(float(item.get("total_duration", 0) or 0) / 60, 2),
            "stops": int(item.get("stops", 0) or 0),
            "price_per_person": round(round_total / max(int(travellers), 1), 2),
            "total_price": round(round_total, 2),
            "round_trip_total_price": round(round_total, 2),
            "currency": "GBP",
            "travellers": max(int(travellers), 1),
            "segments": normalised,
            "booking_token": item.get("booking_token"),
            "flight_type": "return",
        })
    return results[:10]


def combine_selected_flights(outbound: dict, return_flight: dict | None = None) -> dict:
    """Create one planner-safe flight record containing both selected legs."""
    combined = dict(outbound or {})
    combined["outbound"] = dict(outbound or {})
    combined["return"] = dict(return_flight or {})
    combined["return_flight"] = dict(return_flight or {})
    if return_flight:
        try:
            outbound_total = float(outbound.get("total_price", 0) or 0)
            return_total = float(return_flight.get("total_price", 0) or 0)
            travellers = max(int(outbound.get("travellers", return_flight.get("travellers", 1)) or 1), 1)
        except (TypeError, ValueError):
            outbound_total = 0.0
            return_total = 0.0
            travellers = 1

        # Return-token results represent the inbound leg. The complete trip
        # cost is therefore outbound + inbound, not the inbound price alone.
        combined["total_price"] = round(outbound_total + return_total, 2)
        combined["price_per_person"] = round(combined["total_price"] / travellers, 2)
        combined["round_trip_total_price"] = combined["total_price"]
        combined["trip_type"] = "Round Trip"
    else:
        combined["trip_type"] = "One Way"
    return combined