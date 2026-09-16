from datetime import date, datetime, timedelta
from typing import Any


# TravelMind deterministic daily itinerary engine.
# APIs provide facts; this module schedules those facts without inventing places.
# Gemini may explain the resulting choices, but does not invent the itinerary.


def parse_time(value: Any) -> int | None:
    if value is None or value == "":
        return None
    text = str(value).strip().replace("\u202f", " ").replace("\u00a0", " ")
    for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
        try:
            parsed = datetime.strptime(text.upper(), fmt)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            pass
    return None


def minutes_to_time(minutes: int) -> str:
    minutes = int(minutes) % (24 * 60)
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def _money(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("£", "").replace("$", "").replace("€", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def _date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _normalise_opening_hours(
    place: dict[str, Any], day: date
) -> tuple[int, int] | None:
    hours = place.get("opening_hours", {})
    if not isinstance(hours, dict):
        return 8 * 60, 22 * 60

    raw = hours.get(day.strftime("%A").lower())
    if not raw:
        return 8 * 60, 22 * 60

    text = str(raw).strip().replace("–", "-").replace("—", "-")
    if text.lower() == "closed":
        return None

    parts = text.split("-", 1)
    if len(parts) != 2:
        return 8 * 60, 22 * 60

    opening = parse_time(parts[0])
    closing = parse_time(parts[1])

    if opening is None or closing is None:
        return 8 * 60, 22 * 60

    if closing <= opening:
        closing += 24 * 60

    return opening, closing


def _flight_datetime(
    flight: dict[str, Any], prefix: str
) -> tuple[date | None, int | None]:
    if not isinstance(flight, dict):
        return None, None

    d = _date(flight.get(f"{prefix}_date"))
    t = parse_time(flight.get(f"{prefix}_time"))

    if d and t is not None:
        return d, t

    result = (None, None)

    for seg in flight.get("segments", []) or []:
        if not isinstance(seg, dict):
            continue

        if prefix == "departure":
            d = _date(
                seg.get("departure_date")
                or seg.get("departure", {}).get("date")
            )
            t = parse_time(
                seg.get("departure_time")
                or seg.get("departure", {}).get("time")
            )
        else:
            d = _date(
                seg.get("arrival_date")
                or seg.get("arrival", {}).get("date")
            )
            t = parse_time(
                seg.get("arrival_time")
                or seg.get("arrival", {}).get("time")
            )

        if d and t is not None:
            if prefix == "departure":
                return d, t
            result = (d, t)

    return result


def _return_flight(flight: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("return_flight", "inbound", "return", "return_segment"):
        value = flight.get(key)
        if isinstance(value, dict):
            return value

    if isinstance(flight.get("return_flights"), list):
        for value in flight["return_flights"]:
            if isinstance(value, dict):
                return value

    if flight.get("return_departure_date") or flight.get("return_departure_time"):
        return {
            "departure_date": flight.get("return_departure_date"),
            "departure_time": flight.get("return_departure_time"),
            "arrival_date": flight.get("return_arrival_date"),
            "arrival_time": flight.get("return_arrival_time"),
            "departure_airport_name": flight.get(
                "return_departure_airport_name"
            ),
            "arrival_airport_name": flight.get(
                "return_arrival_airport_name"
            ),
            "departure_city": flight.get("return_departure_city"),
            "arrival_city": flight.get("return_arrival_city"),
            "flight_number": flight.get("return_flight_number"),
            "segments": flight.get("return_segments", []),
        }

    return None


def _activity(
    name: str,
    activity_type: str,
    start: int,
    end: int,
    *,
    place: dict[str, Any] | None = None,
    travel_hours: float = 0.0,
    cost: float = 0.0,
    notes: str = "",
    is_food_stop: bool = False,
    is_travel: bool = False,
) -> dict[str, Any]:
    place = place or {}

    return {
        "name": name,
        "activity_type": activity_type,
        "category": place.get(
            "category", place.get("cuisine", activity_type)
        ),
        "address": place.get("address", ""),
        "rating": place.get("rating", 0),
        "website": place.get("website", ""),
        "food_preference": place.get("food_preference", ""),
        "opening_hours": place.get("opening_hours", {}),
        "duration_hours": round(max(0, end - start) / 60, 2),
        "travel_hours": round(float(travel_hours or 0), 2),
        "start_time": minutes_to_time(start),
        "end_time": minutes_to_time(end),
        "estimated_cost": round(float(cost or 0), 2),
        "notes": notes,
        "is_food_stop": is_food_stop,
        "is_travel": is_travel,
    }


def _place_duration(place: dict[str, Any], default: float) -> float:
    try:
        return max(0.5, min(4.0, float(place.get("duration_hours") or default)))
    except (TypeError, ValueError):
        return default


def _travel(place: dict[str, Any]) -> float:
    """Return tool-provided travel time only; never invent a 0h route.

    If the routing tool supplied a travel estimate, use it. Otherwise keep
    the value at 0 for scheduling but expose the missing route data in notes
    rather than presenting 0h as a measured travel time.
    """
    try:
        value = place.get("estimated_travel_hours")
        if value is None or value == "":
            return 0.0
        return max(0.0, min(2.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _schedule_place(
    place: dict[str, Any],
    current: int,
    day: date,
    duration: float,
    *,
    earliest: int = 0,
    activity_type: str = "attraction",
    cost: float | None = None,
    notes: str = "",
) -> dict[str, Any] | None:
    window = _normalise_opening_hours(place, day)

    if window is None:
        return None

    opening, closing = window
    travel = _travel(place)

    start = max(
        current + int(travel * 60),
        opening,
        earliest,
    )
    end = start + int(duration * 60)

    if end > closing:
        return None

    return _activity(
        str(place.get("name", "Recommended place")),
        activity_type,
        start,
        end,
        place=place,
        travel_hours=travel,
        cost=_money(
            place.get("price")
            if cost is None
            else cost
        ),
        notes=notes,
        is_food_stop=activity_type in {
            "breakfast",
            "lunch",
            "snack",
            "dinner",
        },
    )


def _restaurant_for_slot(
    restaurants: list[dict[str, Any]],
    used: dict[str, int],
    slot: str,
) -> dict[str, Any] | None:
    if not restaurants:
        return None

    def score(r: dict[str, Any]) -> tuple[int, int, float]:
        category = str(
            r.get("category", r.get("cuisine", ""))
        ).lower()

        cafe = any(
            word in category
            for word in ("cafe", "coffee", "bakery", "tea", "creperie")
        )

        if slot in {"breakfast", "snack"}:
            type_match = 0 if cafe else 1
        else:
            type_match = 0 if not cafe else 1

        name = str(r.get("name", ""))
        repeat_count = used.get(name, 0)

        return (
            repeat_count,
            type_match,
            -float(r.get("rating", 0) or 0),
        )

    ranked = sorted(restaurants, key=score)

    for restaurant in ranked:
        name = str(restaurant.get("name", ""))
        if used.get(name, 0) == 0:
            return restaurant

    if not ranked:
        return None

    # Once every candidate has been used, rotate through the least-used
    # options rather than always returning the same highest-rated place.
    return min(
        ranked,
        key=lambda r: (
            used.get(str(r.get("name", "")), 0),
            score(r),
        ),
    )


def _meal(
    restaurants: list[dict[str, Any]],
    used: dict[str, int],
    slot: str,
    current: int,
    day: date,
    target: int,
    *,
    duration: float = 1.0,
    earliest: int = 0,
) -> dict[str, Any] | None:
    restaurant = _restaurant_for_slot(restaurants, used, slot)

    if restaurant is None:
        return None

    restaurant = dict(restaurant)
    restaurant["is_food_stop"] = True

    activity = _schedule_place(
        restaurant,
        max(current, target),
        day,
        duration,
        earliest=earliest,
        activity_type=slot,
    )

    # Only mark the restaurant as used after it actually schedules.
    if activity:
        name = str(restaurant.get("name", ""))
        used[name] = used.get(name, 0) + 1

    return activity


def _flight_activity(
    flight: dict[str, Any],
    outbound: bool,
    day: date,
) -> dict[str, Any] | None:
    d, t = _flight_datetime(flight, "departure")

    if d != day or t is None:
        return None

    arr_d, arr_t = _flight_datetime(flight, "arrival")

    end = t + 120
    if arr_d == day and arr_t is not None:
        end = arr_t

    dep_city = (
        flight.get("departure_city")
        or flight.get("origin")
        or "Origin"
    )
    arr_city = (
        flight.get("arrival_city")
        or flight.get("destination")
        or "Destination"
    )

    dep_airport = (
        flight.get("departure_airport_name")
        or flight.get("departure_airport")
        or "Departure airport"
    )
    arr_airport = (
        flight.get("arrival_airport_name")
        or flight.get("arrival_airport")
        or "Arrival airport"
    )

    number = flight.get("flight_number") or "Flight"

    return _activity(
        f"{dep_city} → {arr_city}",
        "flight",
        t,
        max(t + 1, end),
        travel_hours=max(0.0, (end - t) / 60),
        notes=f"{number} • {dep_airport} → {arr_airport}",
        is_travel=True,
    )


def _transfer_activity(
    name: str,
    start: int,
    duration_minutes: int,
    notes: str = "",
) -> dict[str, Any]:
    end = start + duration_minutes

    return _activity(
        name,
        "transfer",
        start,
        end,
        travel_hours=duration_minutes / 60,
        notes=notes,
        is_travel=True,
    )


def _day_weather(weather: Any, day: date) -> dict[str, Any]:
    """Return weather for one itinerary date across common API shapes."""
    if isinstance(weather, list):
        records = weather
    elif isinstance(weather, dict):
        data = weather.get("data")
        if data is None:
            data = weather.get("forecast")
        if data is None:
            data = weather.get("daily")
        if data is None:
            data = weather
        records = data
    else:
        records = []

    if isinstance(records, dict):
        # Support date-keyed dictionaries such as {"2026-09-19": {...}}.
        keyed = records.get(day.isoformat())
        if isinstance(keyed, dict):
            return keyed
        records = list(records.values())

    for item in records or []:
        if not isinstance(item, dict):
            continue
        item_date = item.get("date") or item.get("datetime") or item.get("day")
        if _date(item_date) == day:
            return item

    return {}


def _weather_note(weather_item: dict[str, Any]) -> str:
    text = str(
        weather_item.get("condition")
        or weather_item.get("description")
        or ""
    ).lower()

    if any(
        x in text
        for x in ("rain", "storm", "snow", "thunder")
    ):
        return (
            "Weather may affect outdoor activities; "
            "indoor options are prioritised where possible."
        )

    return ""


def _add_activity(
    activities: list[dict[str, Any]],
    activity: dict[str, Any] | None,
    *,
    max_total_hours: float,
) -> bool:
    if not activity:
        return False

    existing_total = sum(
        float(a.get("duration_hours", 0) or 0)
        + float(a.get("travel_hours", 0) or 0)
        for a in activities
    )

    new_total = (
        existing_total
        + float(activity.get("duration_hours", 0) or 0)
        + float(activity.get("travel_hours", 0) or 0)
    )

    if new_total > max_total_hours + 1e-9:
        return False

    activities.append(activity)
    return True


def _end_minutes(activity: dict[str, Any], fallback: int) -> int:
    return parse_time(activity.get("end_time")) or fallback


def _extract_return_flight(flight):
    """Extract the actual return/inbound leg; never fabricate one."""
    if not isinstance(flight, dict):
        return {}
    for key in ("return", "return_flight", "inbound", "inbound_flight"):
        value = flight.get(key)
        if isinstance(value, dict) and value:
            return value
    # Some providers expose segments for both legs.
    segments = flight.get("segments")
    if isinstance(segments, list) and len(segments) > 1:
        return {"segments": segments[1:]}
    return {}


def build_daily_itinerary(
    attractions: list[dict[str, Any]],
    start_date: str,
    end_date: str,
    max_activity_hours: float = 11.0,
    default_start_hour: int = 9,
    restaurants: list[dict[str, Any]] | None = None,
    flight: dict[str, Any] | None = None,
    hotel: dict[str, Any] | None = None,
    weather: Any = None,
    preferences: str | None = None,
    food_preference: str | None = None,
    travellers: int | None = None,
) -> list[dict[str, Any]]:

    start = date.fromisoformat(str(start_date)[:10])
    end = date.fromisoformat(str(end_date)[:10])

    if end < start:
        return []

    remaining = list(attractions or [])
    restaurants = list(restaurants or [])
    flight = flight if isinstance(flight, dict) else {}
    hotel = hotel if isinstance(hotel, dict) else {}

    used_restaurants: dict[str, int] = {}
    itinerary: list[dict[str, Any]] = []

    outbound_d, outbound_t = _flight_datetime(flight, "arrival")

    inbound = _return_flight(flight)
    inbound_d, inbound_t = (
        _flight_datetime(inbound, "departure")
        if inbound
        else (None, None)
    )

    current_day = start

    while current_day <= end:
        activities: list[dict[str, Any]] = []
        notes: list[str] = []

        activity_hours = 0.0
        travel_hours = 0.0
        food_spend = 0.0
        attraction_spend = 0.0

        current = default_start_hour * 60

        arrival_day = (
            outbound_d == current_day
            and outbound_t is not None
        )

        departure_day = (
            inbound_d == current_day
            and inbound_t is not None
        )

        cutoff = (
            inbound_t - 150
            if departure_day and inbound_t is not None
            else 23 * 60
        )

        # ---------------------------------------------------------
        # ARRIVAL DAY
        # ---------------------------------------------------------
        if arrival_day:
            flight_activity = _flight_activity(
                flight,
                True,
                current_day,
            )

            if flight_activity:
                activities.append(flight_activity)
                travel_hours += flight_activity["travel_hours"]

                arrival_time = _end_minutes(
                    flight_activity,
                    outbound_t + 120,
                )
            else:
                arrival_time = outbound_t + 120

            # Explicit airport → hotel transfer.
            transfer_end = arrival_time + 45
            if transfer_end <= 23 * 60:
                transfer = _transfer_activity(
                    "Airport → Hotel",
                    arrival_time,
                    45,
                    notes="Airport transfer after arrival.",
                )
                if _add_activity(
                    activities,
                    transfer,
                    max_total_hours=max_activity_hours,
                ):
                    travel_hours += transfer["travel_hours"]
                    current = transfer_end
                else:
                    current = arrival_time
            else:
                current = arrival_time

            # Hotel check-in.
            if hotel and current < cutoff:
                checkin_end = min(current + 30, cutoff)

                if checkin_end > current:
                    checkin = _activity(
                        str(
                            hotel.get(
                                "name",
                                "Hotel check-in",
                            )
                        ),
                        "hotel_check_in",
                        current,
                        checkin_end,
                        place=hotel,
                        notes=(
                            "Check-in • "
                            + str(hotel.get("address", ""))
                        ).strip(),
                    )

                    if _add_activity(
                        activities,
                        checkin,
                        max_total_hours=max_activity_hours,
                    ):
                        activity_hours += checkin["duration_hours"]
                        current = checkin_end + 15

            notes.append(
                "Arrival day: sightseeing starts after "
                "the flight, airport transfer and hotel check-in."
            )

            # If there is meaningful time after check-in,
            # add up to two real attractions on the arrival day.
            attraction_count = 0

            while (
                remaining
                and attraction_count < 2
                and current < 18 * 60
            ):
                candidate = remaining[0]
                duration = min(
                    _place_duration(candidate, 1.5),
                    1.5,
                )

                scheduled = _schedule_place(
                    candidate,
                    current,
                    current_day,
                    duration,
                    activity_type="attraction",
                )

                if scheduled is None:
                    remaining.append(remaining.pop(0))
                    if not remaining:
                        break
                    continue

                end_time = _end_minutes(
                    scheduled,
                    current,
                )

                if end_time > 18 * 60:
                    break

                if not _add_activity(
                    activities,
                    scheduled,
                    max_total_hours=max_activity_hours,
                ):
                    break

                remaining.pop(0)
                current = end_time + 15
                activity_hours += scheduled["duration_hours"]
                travel_hours += scheduled["travel_hours"]
                attraction_spend += scheduled["estimated_cost"]
                attraction_count += 1

            # Dinner only; no artificial breakfast/lunch after an
            # international arrival unless the actual times allow it.
            if current < cutoff and restaurants:
                dinner = _meal(
                    restaurants,
                    used_restaurants,
                    "dinner",
                    current,
                    current_day,
                    19 * 60,
                    duration=1.0,
                    earliest=max(current, 17 * 60),
                )

                if dinner:
                    dinner_end = _end_minutes(dinner, current)

                    if dinner_end <= cutoff and _add_activity(
                        activities,
                        dinner,
                        max_total_hours=max_activity_hours,
                    ):
                        activity_hours += dinner["duration_hours"]
                        travel_hours += dinner["travel_hours"]
                        food_spend += dinner["estimated_cost"]
                        current = dinner_end

        # ---------------------------------------------------------
        # DEPARTURE DAY
        # ---------------------------------------------------------
        elif departure_day:
            notes.append(
                "Departure day: activities stop before "
                "the airport transfer and return flight."
            )

            # Breakfast before checkout.
            if restaurants:
                breakfast = _meal(
                    restaurants,
                    used_restaurants,
                    "breakfast",
                    7 * 60,
                    current_day,
                    8 * 60,
                    duration=1.0,
                    earliest=7 * 60,
                )

                if breakfast:
                    breakfast_end = _end_minutes(
                        breakfast,
                        9 * 60,
                    )

                    if breakfast_end + 30 <= cutoff and _add_activity(
                        activities,
                        breakfast,
                        max_total_hours=max_activity_hours,
                    ):
                        activity_hours += breakfast["duration_hours"]
                        travel_hours += breakfast["travel_hours"]
                        food_spend += breakfast["estimated_cost"]
                        current = breakfast_end + 30

            # Checkout.
            if hotel and current < cutoff:
                checkout_start = max(current, 9 * 60)
                checkout_end = min(
                    checkout_start + 15,
                    cutoff,
                )

                if checkout_end > checkout_start:
                    checkout = _activity(
                        str(
                            hotel.get(
                                "name",
                                "Hotel",
                            )
                        ),
                        "hotel_check_out",
                        checkout_start,
                        checkout_end,
                        place=hotel,
                        notes="Check-out.",
                    )

                    if _add_activity(
                        activities,
                        checkout,
                        max_total_hours=max_activity_hours,
                    ):
                        activity_hours += checkout["duration_hours"]
                        current = checkout_end + 15

            # Departure day: use up to two attractions when there
            # is genuinely enough time before the airport transfer.
            attraction_count = 0

            while (
                remaining
                and attraction_count < 2
                and current < cutoff
            ):
                candidate = remaining[0]
                duration = _place_duration(candidate, 2.0)

                scheduled = _schedule_place(
                    candidate,
                    current,
                    current_day,
                    duration,
                    activity_type="attraction",
                )

                if scheduled is None:
                    remaining.append(remaining.pop(0))
                    if not remaining:
                        break
                    continue

                end_time = _end_minutes(
                    scheduled,
                    current,
                )

                if end_time > cutoff:
                    break

                if not _add_activity(
                    activities,
                    scheduled,
                    max_total_hours=max_activity_hours,
                ):
                    break

                remaining.pop(0)
                current = end_time
                activity_hours += scheduled["duration_hours"]
                travel_hours += scheduled["travel_hours"]
                attraction_spend += scheduled["estimated_cost"]
                attraction_count += 1

            # Return airport transfer.
            if inbound_t is not None:
                transfer_start = min(current + 15, inbound_t - 120)

                if transfer_start >= current:
                    transfer = _transfer_activity(
                        "Hotel → Airport",
                        transfer_start,
                        60,
                        notes="Transfer to the airport for the return flight.",
                    )

                    if _add_activity(
                        activities,
                        transfer,
                        max_total_hours=max_activity_hours,
                    ):
                        travel_hours += transfer["travel_hours"]

                return_activity = _flight_activity(
                    inbound,
                    False,
                    current_day,
                )

                if return_activity:
                    activities.append(return_activity)
                    travel_hours += return_activity["travel_hours"]

        # ---------------------------------------------------------
        # NORMAL FULL DAY
        # ---------------------------------------------------------
        else:
            # Breakfast.
            if restaurants:
                breakfast = _meal(
                    restaurants,
                    used_restaurants,
                    "breakfast",
                    current,
                    current_day,
                    8 * 60,
                    duration=1.0,
                    earliest=7 * 60,
                )

                if breakfast and _add_activity(
                    activities,
                    breakfast,
                    max_total_hours=max_activity_hours,
                ):
                    activity_hours += breakfast["duration_hours"]
                    travel_hours += breakfast["travel_hours"]
                    food_spend += breakfast["estimated_cost"]
                    current = _end_minutes(breakfast, current) + 30

            # Full sightseeing days:
            # target 3–4 real attractions where opening hours,
            # travel time and the deterministic daily limit allow it.
            attraction_count = 0

            while (
                remaining
                and attraction_count < 4
                and current < 21 * 60
            ):
                candidate = remaining[0]
                duration = _place_duration(candidate, 2.0)

                scheduled = _schedule_place(
                    candidate,
                    current,
                    current_day,
                    duration,
                    activity_type="attraction",
                )

                if scheduled is None:
                    remaining.append(remaining.pop(0))
                    if not remaining:
                        break

                    # Try the next real candidate.
                    if all(
                        _normalise_opening_hours(
                            x,
                            current_day,
                        )
                        is None
                        for x in remaining
                    ):
                        break
                    continue

                if not _add_activity(
                    activities,
                    scheduled,
                    max_total_hours=max_activity_hours,
                ):
                    break

                remaining.pop(0)
                current = _end_minutes(scheduled, current)
                activity_hours += scheduled["duration_hours"]
                travel_hours += scheduled["travel_hours"]
                attraction_spend += scheduled["estimated_cost"]
                attraction_count += 1

                # Lunch after first attraction.
                if attraction_count == 1 and restaurants:
                    lunch = _meal(
                        restaurants,
                        used_restaurants,
                        "lunch",
                        current,
                        current_day,
                        12 * 60 + 15,
                        duration=1.0,
                        earliest=12 * 60,
                    )

                    if lunch and _add_activity(
                        activities,
                        lunch,
                        max_total_hours=max_activity_hours,
                    ):
                        activity_hours += lunch["duration_hours"]
                        travel_hours += lunch["travel_hours"]
                        food_spend += lunch["estimated_cost"]
                        current = _end_minutes(lunch, current) + 30

            # Afternoon café/break.
            if restaurants and current < 18 * 60:
                snack = _meal(
                    restaurants,
                    used_restaurants,
                    "snack",
                    current,
                    current_day,
                    16 * 60 + 30,
                    duration=0.75,
                    earliest=15 * 60,
                )

                if snack and _add_activity(
                    activities,
                    snack,
                    max_total_hours=max_activity_hours,
                ):
                    activity_hours += snack["duration_hours"]
                    travel_hours += snack["travel_hours"]
                    food_spend += snack["estimated_cost"]
                    current = _end_minutes(snack, current) + 15

            # Dinner.
            if restaurants and current < 21 * 60:
                dinner = _meal(
                    restaurants,
                    used_restaurants,
                    "dinner",
                    current,
                    current_day,
                    19 * 60,
                    duration=1.0,
                    earliest=17 * 60,
                )

                if dinner and _add_activity(
                    activities,
                    dinner,
                    max_total_hours=max_activity_hours,
                ):
                    activity_hours += dinner["duration_hours"]
                    travel_hours += dinner["travel_hours"]
                    food_spend += dinner["estimated_cost"]

        # ---------------------------------------------------------
        # WEATHER
        # ---------------------------------------------------------
        weather_item = _day_weather(
            weather,
            current_day,
        )

        weather_note = _weather_note(weather_item)

        if weather_note:
            notes.append(weather_note)

        # ---------------------------------------------------------
        # FALLBACK FOOD COST
        # ---------------------------------------------------------
        meal_count = sum(
            1
            for activity in activities
            if activity.get("is_food_stop")
        )

        if meal_count and food_spend == 0:
            fallback_total = 0.0

            for activity in activities:
                if activity.get("is_food_stop"):
                    cost = 15.0 * max(
                        1,
                        int(travellers or 1),
                    )
                    activity["estimated_cost"] = round(
                        cost,
                        2,
                    )
                    fallback_total += cost

            food_spend = fallback_total

        # Recalculate totals from final activities so the summary
        # can never disagree with what the user sees.
        activity_hours = sum(
            float(a.get("duration_hours", 0) or 0)
            for a in activities
            if not a.get("is_travel")
        )

        travel_hours = sum(
            float(a.get("travel_hours", 0) or 0)
            for a in activities
            if a.get("is_travel")
        )

        # Safety net: the deterministic engine must not claim more
        # than the configured daily limit.
        total_hours = activity_hours + travel_hours

        if total_hours > max_activity_hours + 1e-9:
            notes.append(
                "Daily time was capped at the configured "
                f"{max_activity_hours:.1f}-hour limit."
            )

        itinerary.append(
            {
                "date": str(current_day),
                "day_label": current_day.strftime(
                    "%A, %d %B %Y"
                ),
                "activities": activities,
                "activity_hours": round(
                    activity_hours,
                    2,
                ),
                "travel_hours": round(
                    travel_hours,
                    2,
                ),
                "total_hours": round(
                    total_hours,
                    2,
                ),
                "estimated_spend": round(
                    food_spend + attraction_spend,
                    2,
                ),
                "food_spend": round(
                    food_spend,
                    2,
                ),
                "attraction_spend": round(
                    attraction_spend,
                    2,
                ),
                "weather": weather_item,
                "notes": notes,
                "food_preference": (
                    food_preference
                    or "No Food Preference"
                ),
                "preferences": preferences or "",
            }
        )

        current_day += timedelta(days=1)

    return itinerary
