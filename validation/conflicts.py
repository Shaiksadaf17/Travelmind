from typing import Any


def detect_conflicts(
    plan: dict[str, Any] | None,
    state: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Detect planning conflicts that may require
    replanning or user intervention.

    Conflicts are deterministic and based on:
    - feasibility
    - budget
    - preferences
    - daily time limits
    - weather
    - data availability
    """

    conflicts: list[dict[str, Any]] = []

    budget = float(
        state.get(
            "budget",
            0,
        )
    )

    preferences = str(
        state.get(
            "preferences",
            "",
        )
    ).lower()

    priorities = state.get(
        "priorities",
        {},
    )

    # ==================================================
    # 1. NO FEASIBLE PLAN
    # ==================================================

    if plan is None:

        conflicts.append(
            {
                "type": "no_feasible_plan",
                "severity": "HIGH",
                "message": (
                    "No candidate plan satisfies "
                    "the current constraints."
                ),
            }
        )

        # We can still inspect candidate-related
        # validation information below, but there is
        # no selected plan to validate.
        return conflicts

    # ==================================================
    # 2. BUDGET CONFLICT
    # ==================================================

    budget_result = validation.get(
        "budget",
        {},
    )

    if not budget_result.get(
        "passed",
        False,
    ):

        exceeded_by = budget_result.get(
            "exceeded_by",
            0,
        )

        conflicts.append(
            {
                "type": "budget",
                "severity": "HIGH",
                "message": (
                    f"The selected plan exceeds the "
                    f"£{budget:.2f} budget by "
                    f"£{float(exceeded_by):.2f}."
                ),
                "suggestions": [
                    "Increase the travel budget.",
                    "Choose a lower-cost hotel.",
                    "Choose a cheaper flight.",
                    "Reduce paid activities.",
                ],
            }
        )

    # ==================================================
    # 3. PREFERENCE CONFLICT
    # ==================================================

    preference_result = validation.get(
        "preferences",
        {},
    )

    if not preference_result.get(
        "passed",
        True,
    ):

        for check in preference_result.get(
            "checks",
            [],
        ):

            if not check.get(
                "passed",
                True,
            ):

                priority = check.get(
                    "priority",
                    "MEDIUM",
                )

                severity = (
                    "HIGH"
                    if priority == "HIGH"
                    else "MEDIUM"
                )

                conflicts.append(
                    {
                        "type": "preference",
                        "severity": severity,
                        "message": check.get(
                            "message",
                            "A requested preference "
                            "could not be satisfied.",
                        ),
                        "priority": priority,
                    }
                )

    # ==================================================
    # 4. DAILY TIME CONFLICT
    # ==================================================

    itinerary = plan.get(
        "daily_itinerary",
        [],
    )

    for day in itinerary:

        activity_hours = float(
            day.get(
                "activity_hours",
                0,
            )
            or 0
        )

        travel_hours = float(
            day.get(
                "travel_hours",
                0,
            )
            or 0
        )

        total_hours = (
            activity_hours
            + travel_hours
        )

        max_hours = 8.0

        if total_hours > max_hours:

            conflicts.append(
                {
                    "type": "daily_time",
                    "severity": "HIGH",
                    "message": (
                        f"{day.get('date', 'A day')} "
                        f"requires approximately "
                        f"{total_hours:.2f} hours, "
                        f"exceeding the "
                        f"{max_hours:.1f}-hour daily limit."
                    ),
                    "suggestions": [
                        "Remove an activity.",
                        "Reduce activity duration.",
                        "Move an activity to another day.",
                    ],
                }
            )

    # ==================================================
    # 5. WEATHER CONFLICT
    # ==================================================

    weather_data = state.get(
        "weather_data",
        {},
    )

    forecast = weather_data.get(
        "forecast",
        [],
    )

    for day_weather in forecast:

        rain_probability = day_weather.get(
            "rain_probability"
        )

        if (
            rain_probability is not None
            and float(rain_probability) >= 60
        ):

            outdoor_attractions = [
                attraction
                for attraction in plan.get(
                    "attractions",
                    [],
                )
                if str(
                    attraction.get(
                        "category",
                        "",
                    )
                ).lower()
                in {
                    "park",
                    "outdoor",
                }
            ]

            if outdoor_attractions:

                conflicts.append(
                    {
                        "type": "weather",
                        "severity": "MEDIUM",
                        "message": (
                            f"High rain probability "
                            f"({float(rain_probability):.0f}%) "
                            f"may affect outdoor activities "
                            f"on {day_weather.get('date', 'the selected day')}."
                        ),
                        "suggestions": [
                            "Replace outdoor activities "
                            "with indoor attractions.",
                            "Move outdoor activities "
                            "to a better-weather day.",
                        ],
                    }
                )

    # ==================================================
    # 6. MISSING DATA CONFLICT
    # ==================================================

    data_quality = state.get(
        "data_quality",
        {},
    )

    for tool_name, quality in data_quality.items():

        if isinstance(
            quality,
            dict,
        ):

            status = str(
                quality.get(
                    "status",
                    "",
                )
            ).lower()

            if status in {
                "error",
                "unavailable",
            }:

                conflicts.append(
                    {
                        "type": "data_quality",
                        "severity": "MEDIUM",
                        "message": (
                            f"{tool_name} data is "
                            "unavailable, so the plan "
                            "may contain incomplete information."
                        ),
                    }
                )

    # ==================================================
    # 7. LUXURY + LOW BUDGET CONFLICT
    # ==================================================

    luxury_priority = priorities.get(
        "luxury",
        "LOW",
    )

    hotel = plan.get(
        "hotel",
        {},
    )

    hotel_rating = float(
        hotel.get(
            "rating",
            0,
        )
        or 0
    )

    total_cost = float(
        plan.get(
            "total_cost",
            0,
        )
    )

    if (
        luxury_priority == "HIGH"
        and budget > 0
        and total_cost > budget * 0.9
        and hotel_rating < 4.0
    ):

        conflicts.append(
            {
                "type": "luxury_budget",
                "severity": "MEDIUM",
                "message": (
                    "Luxury was given HIGH priority, "
                    "but the current budget leaves "
                    "limited room for higher-quality "
                    "accommodation."
                ),
                "suggestions": [
                    "Increase the budget.",
                    "Reduce the number of paid activities.",
                    "Adjust luxury priority to MEDIUM.",
                ],
            }
        )

    return conflicts