from typing import Any


def validate_preferences(
    plan: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate important user preferences.
    """

    preferences = (
        state.get("preferences", "")
        .lower()
    )

    priorities = state.get(
        "priorities",
        {},
    )

    checks = []

    # -----------------------------------------------
    # Vegetarian
    # -----------------------------------------------

    if "vegetarian" in preferences:

        vegetarian_restaurants = [
            restaurant
            for restaurant in plan.get(
                "restaurants",
                [],
            )
            if restaurant.get(
                "vegetarian",
                False,
            )
        ]

        passed = len(
            vegetarian_restaurants
        ) > 0

        checks.append(
            {
                "preference": "vegetarian",
                "priority": priorities.get(
                    "vegetarian",
                    "MEDIUM",
                ),
                "passed": passed,
                "message": (
                    "Vegetarian restaurants available."
                    if passed
                    else
                    "No vegetarian restaurant found."
                ),
            }
        )

    # -----------------------------------------------
    # Museums
    # -----------------------------------------------

    if "museum" in preferences:

        museums = [
            attraction
            for attraction in plan.get(
                "attractions",
                [],
            )
            if "museum"
            in attraction.get(
                "category",
                "",
            ).lower()
        ]

        passed = len(museums) > 0

        checks.append(
            {
                "preference": "museums",
                "priority": "MEDIUM",
                "passed": passed,
                "message": (
                    "Museum activity included."
                    if passed
                    else
                    "No museum activity included."
                ),
            }
        )

    passed = (
        all(
            check["passed"]
            for check in checks
        )
        if checks
        else True
    )

    return {
        "passed": passed,
        "checks": checks,
    }