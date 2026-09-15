from typing import Any


# ==================================================
# WEATHER CLASSIFICATION
# ==================================================

def classify_weather(weather: dict[str, Any]) -> str:
    """
    Classify overall weather conditions using
    available precipitation probabilities.

    Missing rain-probability values are ignored.
    """

    forecast = weather.get("forecast", [])

    if not forecast:
        return "unknown"

    rain_probabilities = [
        item.get("rain_probability")
        for item in forecast
        if item.get("rain_probability") is not None
    ]

    if not rain_probabilities:
        return "unknown"

    average_rain = (
        sum(rain_probabilities)
        / len(rain_probabilities)
    )

    if average_rain >= 60:
        return "poor"

    if average_rain >= 30:
        return "mixed"

    return "good"


# ==================================================
# WEATHER-SUITABLE ACTIVITIES
# ==================================================

def select_weather_suitable_activities(
    attractions: list[dict[str, Any]],
    weather: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Select activities based on the overall weather
    classification.

    Poor weather prioritises indoor activities.
    Good or mixed weather keeps the available
    attraction list.
    """

    weather_status = classify_weather(weather)

    if weather_status == "unknown":
        return attractions

    if weather_status == "poor":

        indoor = [
            attraction
            for attraction in attractions
            if attraction.get(
                "category",
                "",
            ).lower()
            in {
                "museum",
                "gallery",
                "indoor",
            }
        ]

        if indoor:
            return indoor

    return attractions