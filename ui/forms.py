import streamlit as st
from datetime import date


# ============================================================
# TOP 30 TRAVEL CITIES
# ============================================================

TOP_CITIES = [
    "Paris",
    "London",
    "Rome",
    "Barcelona",
    "Amsterdam",
    "Dubai",
    "Istanbul",
    "New York",
    "Tokyo",
    "Singapore",
    "Bangkok",
    "Lisbon",
    "Prague",
    "Vienna",
    "Madrid",
    "Berlin",
    "Copenhagen",
    "Athens",
    "Seoul",
    "Hong Kong",
    "Sydney",
    "Melbourne",
    "Toronto",
    "Los Angeles",
    "San Francisco",
    "Zurich",
    "Budapest",
    "Dublin",
    "Edinburgh",
    "Kuala Lumpur",
]


# ============================================================
# CITY SELECTOR
# ============================================================

def city_selector(
    label: str,
    key: str,
    placeholder: str,
):
    """
    Searchable city selector using the curated
    TravelMind Top 30 city list.
    """

    return st.selectbox(
        label,
        options=TOP_CITIES,
        index=None,
        placeholder=placeholder,
        key=key,
    )


# ============================================================
# TRIP FORM
# ============================================================

def render_trip_form():

    st.subheader("✈️ Tell us about your trip")

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # LEFT COLUMN
    # --------------------------------------------------------

    with col1:

        name = st.text_input(
            "Name",
            placeholder="Enter your name",
        )

        origin = city_selector(
            "Origin",
            "trip_origin",
            "Type a city, then select it...",
        )

        start_date = st.date_input(
            "Start Date",
            value=date.today(),
        )

        travellers = st.number_input(
            "Travellers",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
        )

    # --------------------------------------------------------
    # RIGHT COLUMN
    # --------------------------------------------------------

    with col2:

        destination = city_selector(
            "Destination",
            "trip_destination",
            "Type a city, then select it...",
        )

        end_date = st.date_input(
            "End Date",
            value=date.today(),
        )

        budget = st.number_input(
            "Budget (£)",
            min_value=0.0,
            value=800.0,
            step=50.0,
        )

        food_preference = st.selectbox(
            "🍽️ Food Preference",
            [
                "No Food Preference",
                "Vegetarian",
                "Non-Vegetarian",
                "Vegan",
            ],
        )

        preferences = st.text_input(
            "Other Preferences",
            placeholder=(
                "e.g. Museums, Shopping, Nightlife"
            ),
        )

    # ========================================================
    # PREFERENCE PRIORITIES
    # ========================================================

    st.subheader("🎯 Preference Priorities")

    col1, col2, col3 = st.columns(3)

    with col1:

        budget_priority = st.selectbox(
            "Budget",
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
        )

    with col2:

        food_priority = st.selectbox(
            "Food Preference",
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
        )

    with col3:

        location_priority = st.selectbox(
            "Central Location",
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
        )

    luxury_priority = st.selectbox(
        "Luxury",
        [
            "HIGH",
            "MEDIUM",
            "LOW",
        ],
    )

    # ========================================================
    # RETURN TRIP DATA
    # ========================================================

    return {
        "name": name,

        "origin": origin or "",

        "destination": destination or "",

        "start_date": start_date,

        "end_date": end_date,

        "travellers": travellers,

        "budget": budget,

        "preferences": preferences,

        "food_preference": food_preference,

        "priorities": {
            "budget": budget_priority,

            "food": food_priority,

            # Backward compatibility with older code.
            "vegetarian": food_priority,

            "central_location": location_priority,

            "luxury": luxury_priority,
        },
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_trip_input(trip):

    errors = []

    if not trip["name"].strip():

        errors.append(
            "Please enter your name."
        )

    if not trip["origin"].strip():

        errors.append(
            "Please select your origin city."
        )

    if not trip["destination"].strip():

        errors.append(
            "Please select your destination city."
        )

    if (
        trip.get("start_date")
        and trip.get("end_date")
        and trip["end_date"] < trip["start_date"]
    ):

        errors.append(
            "End date cannot be before start date."
        )

    if trip["budget"] <= 0:

        errors.append(
            "Budget must be greater than £0."
        )

    if trip["travellers"] < 1:

        errors.append(
            "At least one traveller is required."
        )

    # --------------------------------------------------------
    # Origin and destination should be different.
    # --------------------------------------------------------

    if (
        trip["origin"]
        and trip["destination"]
        and trip["origin"] == trip["destination"]
    ):

        errors.append(
            "Origin and destination must be different cities."
        )

    return errors