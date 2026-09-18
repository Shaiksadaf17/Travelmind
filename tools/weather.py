from typing import Any

import requests


# ==================================================
# GEOCODING
# ==================================================

def geocode_location(location: str) -> dict[str, Any]:
    """
    Convert a city/location name into latitude and longitude
    using the Open-Meteo Geocoding API.
    """

    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params=params,
            timeout=(5, 15),
        )

        response.raise_for_status()

        result = response.json()

        results = result.get("results", [])

        if not results:
            return {
                "status": "error",
                "message": f"Location not found: {location}",
                "data": None,
            }

        location_data = results[0]

        return {
            "status": "ok",
            "message": "Location geocoded successfully.",
            "data": {
                "name": location_data.get("name"),
                "latitude": location_data.get("latitude"),
                "longitude": location_data.get("longitude"),
                "country": location_data.get("country"),
                "timezone": location_data.get("timezone"),
            },
        }

    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": f"Geocoding request failed: {exc}",
            "data": None,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Unexpected geocoding error: {exc}",
            "data": None,
        }


# ==================================================
# WEATHER CODE
# ==================================================

def weather_code_to_condition(code: int) -> str:
    """
    Convert WMO weather codes into readable conditions.
    """

    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    return weather_codes.get(
        code,
        "Unknown",
    )


# ==================================================
# WEATHER SEARCH
# ==================================================

def get_weather(
    destination: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Retrieve real weather forecast data from Open-Meteo.
    """

    # --------------------------------------------------
    # Step 1: Geocode destination
    # --------------------------------------------------

    location = geocode_location(destination)

    if location["status"] != "ok":
        return {
            "status": "error",
            "message": location["message"],
            "data": {},
        }

    latitude = location["data"]["latitude"]
    longitude = location["data"]["longitude"]

    # --------------------------------------------------
    # Step 2: Request weather forecast
    # --------------------------------------------------

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "rain_sum,"
            "precipitation_probability_max,"
            "weather_code"
        ),
        "timezone": "auto",
    }

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=(5, 15),
        )

        response.raise_for_status()

        result = response.json()

        daily = result.get("daily", {})

        dates = daily.get("time", [])
        max_temperatures = daily.get(
            "temperature_2m_max",
            [],
        )
        min_temperatures = daily.get(
            "temperature_2m_min",
            [],
        )
        precipitation = daily.get(
            "precipitation_sum",
            [],
        )
        rain = daily.get(
            "rain_sum",
            [],
        )
        rain_probability = daily.get(
            "precipitation_probability_max",
            [],
        )
        weather_codes = daily.get(
            "weather_code",
            [],
        )

        forecast = []

        for index, forecast_date in enumerate(dates):
            code = (
                weather_codes[index]
                if index < len(weather_codes)
                else None
            )

            forecast.append(
                {
                    "date": forecast_date,
                    "condition": (
                        weather_code_to_condition(code)
                        if code is not None
                        else "Unknown"
                    ),
                    "temperature_max_c": (
                        max_temperatures[index]
                        if index < len(max_temperatures)
                        else None
                    ),
                    "temperature_min_c": (
                        min_temperatures[index]
                        if index < len(min_temperatures)
                        else None
                    ),
                    "precipitation_mm": (
                        precipitation[index]
                        if index < len(precipitation)
                        else None
                    ),
                    "rain_mm": (
                        rain[index]
                        if index < len(rain)
                        else None
                    ),
                    "rain_probability": (
                        rain_probability[index]
                        if index < len(rain_probability)
                        else None
                    ),
                    "weather_code": code,
                }
            )

        if not forecast:
            return {
                "status": "error",
                "message": "No weather forecast was returned.",
                "data": {},
            }

        return {
            "status": "ok",
            "message": "Weather data retrieved successfully.",
            "data": {
                "location": location["data"],
                "forecast": forecast,
            },
        }

    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": f"Weather API request failed: {exc}",
            "data": {},
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Unexpected weather error: {exc}",
            "data": {},
        }