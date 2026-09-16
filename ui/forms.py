import streamlit as st
from datetime import date, timedelta


# ==================================================
# TRAVELMIND CITY OPTIONS
# ==================================================

TOP_30_CITIES = [
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


def city_selector(label: str, key: str, placeholder: str):
    return st.selectbox(
        label,
        options=TOP_30_CITIES,
        index=None,
        placeholder=placeholder,
        key=key,
    )


def render_trip_form():
    st.subheader("✈️ Tell us about your trip")

    # --------------------------------------------------
    # 1. TRAVELLER
    # 2. ROUTE
    # 3. DATES
    # 4. TRIP SIZE + BUDGET
    # --------------------------------------------------

    name = st.text_input(
        "👤 Name",
        placeholder="Enter your name",
        key="trip_name",
    )

    st.markdown("#### 🗺️ Route")

    col1, col2 = st.columns(2)

    with col1:
        origin = city_selector(
            "🛫 Origin",
            "trip_origin",
            "Select departure city...",
        )

    with col2:
        destination = city_selector(
            "🛬 Destination",
            "trip_destination",
            "Select destination city...",
        )

    st.markdown("#### 📅 Travel Dates")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today(),
            min_value=date.today(),
            key="trip_start_date",
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=max(date.today(), start_date + timedelta(days=1)),
            min_value=start_date,
            key="trip_end_date",
        )

    st.markdown("#### 👥 Trip Details")

    col1, col2 = st.columns(2)

    with col1:
        travellers = st.number_input(
            "Travellers",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            key="trip_travellers",
        )

    with col2:
        budget = st.number_input(
            "Budget (£)",
            min_value=1.0,
            value=800.0,
            step=50.0,
            key="trip_budget",
        )

    st.markdown("#### 🍽️ Preferences")

    food_preference = st.selectbox(
        "Food Preference",
        [
            "No Food Preference",
            "Vegetarian",
            "Non-Vegetarian",
            "Vegan",
        ],
        key="trip_food_preference",
    )

    # Kept as an empty string for compatibility with the existing
    # planner/state/database schema. There is no separate "Other Preferences"
    # input in the UI anymore.
    preferences = ""

    st.markdown("#### 🎯 Preference Priorities")
    st.caption(
        "Tell TravelMind which requirements matter most when it makes trade-offs."
    )

    col1, col2 = st.columns(2)

    with col1:
        budget_priority = st.selectbox(
            "💷 Budget Priority",
            ["HIGH", "MEDIUM", "LOW"],
            key="trip_budget_priority",
        )

        food_priority = st.selectbox(
            "🍽️ Food Priority",
            ["HIGH", "MEDIUM", "LOW"],
            key="trip_food_priority",
        )

    with col2:
        location_priority = st.selectbox(
            "📍 Central Location Priority",
            ["HIGH", "MEDIUM", "LOW"],
            key="trip_location_priority",
        )

        luxury_priority = st.selectbox(
            "✨ Luxury Priority",
            ["HIGH", "MEDIUM", "LOW"],
            key="trip_luxury_priority",
        )

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
            # Backward compatibility with older scoring code.
            "vegetarian": food_priority,
            "central_location": location_priority,
            "luxury": luxury_priority,
        },
    }


def validate_trip_input(trip):
    errors = []

    if not trip["name"].strip():
        errors.append("Please enter your name.")

    if not trip["origin"].strip():
        errors.append("Please select your origin city.")

    if not trip["destination"].strip():
        errors.append("Please select your destination city.")

    if trip["origin"].strip() and trip["destination"].strip():
        if trip["origin"].strip().casefold() == trip["destination"].strip().casefold():
            errors.append("Origin and destination cannot be the same city.")

    if (
        trip.get("start_date")
        and trip.get("end_date")
        and trip["end_date"] < trip["start_date"]
    ):
        errors.append("End date cannot be before start date.")

    if trip["budget"] <= 0:
        errors.append("Budget must be greater than £0.")

    if trip["travellers"] < 1:
        errors.append("At least one traveller is required.")

    return errors

