from datetime import date, datetime, timedelta
from typing import Any


def parse_time(time_text: str) -> int | None:
    if not time_text:
        return None

    text = (
        str(time_text)
        .strip()
        .replace("\u202f", " ")
        .replace("\u00a0", " ")
    )

    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            parsed = datetime.strptime(text.upper(), fmt)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            continue

    return None


def get_opening_window(
    place: dict[str, Any],
    day: date,
) -> tuple[int, int] | None:

    opening_hours = place.get("opening_hours", {})

    if not isinstance(opening_hours, dict):
        # Places without structured opening hours
        # can still be scheduled using a safe default.
        return 9 * 60, 22 * 60

    day_name = day.strftime("%A").lower()
    hours = opening_hours.get(day_name)

    if not hours:
        # If the API does not provide hours for this day,
        # use a general scheduling window.
        return 9 * 60, 22 * 60

    hours = (
        str(hours)
        .strip()
        .replace("\u202f", " ")
        .replace("\u00a0", " ")
        .replace("–", "-")
        .replace("—", "-")
    )

    if hours.lower() == "closed":
        return None

    parts = hours.split("-", 1)

    if len(parts) != 2:
        return 9 * 60, 22 * 60

    opening = parse_time(parts[0])
    closing = parse_time(parts[1])

    if opening is None or closing is None:
        return 9 * 60, 22 * 60

    # Handle places that close after midnight.
    if closing <= opening:
        closing += 24 * 60

    return opening, closing


def _schedule_place(
    place: dict[str, Any],
    current_time: int,
    current_day: date,
    duration_hours: float,
):
    opening_window = get_opening_window(
        place,
        current_day,
    )

    if opening_window is None:
        return None

    opening_time, closing_time = opening_window

    travel_time = float(
        place.get(
            "estimated_travel_hours",
            0.0,
        )
        or 0.0
    )

    duration_minutes = int(
        duration_hours * 60
    )

    travel_minutes = int(
        travel_time * 60
    )

    start = max(
        current_time + travel_minutes,
        opening_time,
    )

    end = start + duration_minutes

    if end > closing_time:
        return None

    return {
        "name": place.get(
            "name",
            "Unknown",
        ),
        "category": place.get(
            "category",
            place.get(
                "cuisine",
                "Restaurant",
            ),
        ),
        "address": place.get(
            "address",
            "",
        ),
        "rating": place.get(
            "rating",
            0,
        ),
        "duration_hours": duration_hours,
        "travel_hours": travel_time,
        "start_time": minutes_to_time(
            start
        ),
        "end_time": minutes_to_time(
            end
        ),
        "opening_hours": place.get(
            "opening_hours",
            {},
        ),
        "website": place.get(
            "website",
            "",
        ),
        "is_food_stop": True,
        "food_preference": place.get(
            "food_preference",
            "",
        ),
    }


def build_daily_itinerary(
    attractions: list[dict[str, Any]],
    start_date: str,
    end_date: str,
    max_activity_hours: float = 8.0,
    default_start_hour: int = 9,
    restaurants: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:

    attractions = list(
        attractions or []
    )

    restaurants = list(
        restaurants or []
    )

    # If there is absolutely nothing to schedule,
    # return an empty itinerary.
    if not attractions and not restaurants:
        return []

    try:
        start = date.fromisoformat(
            str(start_date)
        )

        end = date.fromisoformat(
            str(end_date)
        )

    except ValueError:
        return []

    if end < start:
        return []

    # Copies are used so the original lists are
    # not modified.
    remaining_attractions = attractions.copy()
    remaining_restaurants = restaurants.copy()

    itinerary = []

    current_day = start

    # ==================================================
    # IMPORTANT:
    # Always iterate through EVERY calendar day.
    #
    # Previously this loop stopped as soon as all
    # activities/restaurants were consumed, which meant
    # a 4-day trip could incorrectly produce only 3 days.
    # ==================================================

    while current_day <= end:

        daily_activities = []

        activity_hours = 0.0
        travel_hours = 0.0

        current_time = (
            default_start_hour * 60
        )

        # --------------------------------------------------
        # Maximum two attraction stops per day.
        # This leaves room for food and travel.
        # --------------------------------------------------

        attraction_count = 0

        still_remaining_attractions = []

        for attraction in remaining_attractions:

            if attraction_count >= 2:
                still_remaining_attractions.append(
                    attraction
                )
                continue

            duration = float(
                attraction.get(
                    "duration_hours",
                    2.0,
                )
                or 2.0
            )

            # Do not exceed the daily activity limit.
            if (
                activity_hours + duration
                > max_activity_hours
            ):
                still_remaining_attractions.append(
                    attraction
                )
                continue

            scheduled = _schedule_place(
                attraction,
                current_time,
                current_day,
                duration,
            )

            # If the attraction is closed or cannot
            # fit into today's schedule, keep it for
            # a future day.
            if scheduled is None:
                still_remaining_attractions.append(
                    attraction
                )
                continue

            scheduled["is_food_stop"] = False

            daily_activities.append(
                scheduled
            )

            activity_hours += duration

            travel_hours += scheduled[
                "travel_hours"
            ]

            current_time = (
                parse_time(
                    scheduled["end_time"]
                )
                or current_time
            )

            attraction_count += 1

            # --------------------------------------------------
            # Add lunch after the first attraction.
            # --------------------------------------------------

            if (
                attraction_count == 1
                and remaining_restaurants
            ):

                restaurant = (
                    remaining_restaurants[0]
                )

                food_duration = 1.0

                if (
                    activity_hours
                    + food_duration
                    <= max_activity_hours
                ):

                    food_stop = _schedule_place(
                        restaurant,
                        current_time,
                        current_day,
                        food_duration,
                    )

                    if food_stop:

                        daily_activities.append(
                            food_stop
                        )

                        activity_hours += (
                            food_duration
                        )

                        travel_hours += (
                            food_stop[
                                "travel_hours"
                            ]
                        )

                        current_time = (
                            parse_time(
                                food_stop[
                                    "end_time"
                                ]
                            )
                            or current_time
                        )

                        remaining_restaurants.pop(
                            0
                        )

        # --------------------------------------------------
        # If no attraction was scheduled but restaurants
        # remain, add a food stop.
        # --------------------------------------------------

        if (
            not daily_activities
            and remaining_restaurants
        ):

            restaurant = (
                remaining_restaurants.pop(0)
            )

            food_stop = _schedule_place(
                restaurant,
                current_time,
                current_day,
                1.0,
            )

            if food_stop:

                daily_activities.append(
                    food_stop
                )

                activity_hours += 1.0

                travel_hours += (
                    food_stop[
                        "travel_hours"
                    ]
                )

        # --------------------------------------------------
        # ALWAYS append the current day.
        #
        # This means even a day with no available
        # activities will still appear in the itinerary.
        # --------------------------------------------------

        itinerary.append(
            {
                "date": str(
                    current_day
                ),
                "activities": (
                    daily_activities
                ),
                "activity_hours": round(
                    activity_hours,
                    2,
                ),
                "travel_hours": round(
                    travel_hours,
                    2,
                ),
                "total_hours": round(
                    activity_hours
                    + travel_hours,
                    2,
                ),
            }
        )

        # --------------------------------------------------
        # Carry unscheduled attractions to the next day.
        # --------------------------------------------------

        remaining_attractions = (
            still_remaining_attractions
        )

        # Move to the next calendar day.
        current_day += timedelta(
            days=1
        )

    return itinerary


def minutes_to_time(
    minutes: int,
) -> str:

    minutes = minutes % (
        24 * 60
    )

    hour = minutes // 60
    minute = minutes % 60

    suffix = (
        "AM"
        if hour < 12
        else "PM"
    )

    display_hour = hour % 12

    if display_hour == 0:
        display_hour = 12

    return (
        f"{display_hour}:"
        f"{minute:02d} "
        f"{suffix}"
    )