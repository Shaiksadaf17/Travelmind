from datetime import datetime
from typing import Any


# ==================================================
# OPENING HOURS CHECK
# ==================================================

def is_attraction_open(
    attraction: dict[str, Any],
    date: str,
) -> bool:
    """
    Check whether an attraction has opening hours
    for the requested date.

    Supports the dictionary format returned by
    the real Google Maps / SerpApi data.
    """

    opening_hours = attraction.get(
        "opening_hours",
        {},
    )

    # No opening-hours information
    if not opening_hours:
        return False

    # --------------------------------------------------
    # Handle real Google Maps dictionary format
    # --------------------------------------------------

    if isinstance(opening_hours, dict):

        try:
            requested_date = datetime.strptime(
                date,
                "%Y-%m-%d",
            )

            day_name = requested_date.strftime(
                "%A"
            ).lower()

        except ValueError:
            return False

        day_hours = opening_hours.get(
            day_name
        )

        if not day_hours:
            return False

        # Explicitly closed
        if day_hours.lower() == "closed":
            return False

        return True

    # --------------------------------------------------
    # Handle old string format
    # --------------------------------------------------

    if isinstance(opening_hours, str):

        if opening_hours.lower() == "all day":
            return True

        try:
            start_time, end_time = (
                opening_hours.split("-")
            )

            datetime.strptime(
                start_time.strip(),
                "%H:%M",
            )

            datetime.strptime(
                end_time.strip(),
                "%H:%M",
            )

            return True

        except ValueError:
            return False

    return False