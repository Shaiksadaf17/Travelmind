import streamlit as st
import re
import os
import smtplib
from pathlib import Path
from dotenv import load_dotenv
from email.message import EmailMessage
from html import escape

# Load TravelMind's root .env file so SMTP credentials are available.
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from ui.forms import render_trip_form, validate_trip_input
from database.users import get_user_by_name
from database.history import get_saved_trips
from database.trips import mark_trip_as_saved
from agent.graph import travel_graph
from database.itineraries import mark_itinerary_as_final, mark_itinerary_as_saved



# ==================================================
# EMAIL HELPERS
# ==================================================

def build_travel_plan_email(state):
    """Build a clean text + HTML transcript of the final TravelMind plan."""

    selected_plan = state.get("selected_plan") or {}
    itinerary = state.get("daily_itinerary") or []
    explanations = state.get("explanations") or []
    conflicts = state.get("conflicts") or []

    origin = state.get("origin", "")
    destination = state.get("destination", "")
    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")
    travellers = state.get("travellers", "")
    budget = float(state.get("budget", 0) or 0)
    food_preference = state.get(
        "food_preference",
        "No Food Preference",
    )

    plan_name = selected_plan.get(
        "name",
        "Travel Plan",
    )
    total_cost = float(
        selected_plan.get("total_cost", 0) or 0
    )
    score = float(
        selected_plan.get("score", 0) or 0
    )

    flight = selected_plan.get("flight") or {}
    hotel = selected_plan.get("hotel") or {}
    attractions = selected_plan.get("attractions") or []
    restaurants = selected_plan.get("restaurants") or []

    # ------------------------------
    # Plain-text transcript
    # ------------------------------

    lines = [
        "TRAVELMIND — FINAL TRAVEL PLAN",
        "=" * 55,
        "",
        f"Plan: {plan_name}",
        f"Route: {origin} → {destination}",
        f"Dates: {start_date} → {end_date}",
        f"Travellers: {travellers}",
        f"Budget: £{budget:.2f}",
        f"Food preference: {food_preference}",
        f"Total cost: £{total_cost:.2f}",
        f"Planning score: {score:.2f}/100",
        "",
    ]

    if flight:
        lines.extend([
            "FLIGHT",
            "-" * 30,
            f"Airline: {flight.get('airline', 'Unknown')}",
            f"Route: {flight.get('origin', '')} → {flight.get('destination', '')}",
            f"Departure: {flight.get('departure', '')}",
            f"Arrival: {flight.get('arrival', '')}",
            f"Price: £{float(flight.get('total_price', 0) or 0):.2f}",
            f"Stops: {flight.get('stops', 0)}",
            "",
        ])

    if hotel:
        lines.extend([
            "ACCOMMODATION",
            "-" * 30,
            f"Hotel: {hotel.get('name', 'Hotel')}",
            f"Rating: {hotel.get('rating', 'N/A')}/5",
            f"Address: {hotel.get('address', '')}",
            f"Price: £{float(hotel.get('total_price', 0) or 0):.2f}",
            "",
        ])

    if attractions:
        lines.extend([
            "ATTRACTIONS",
            "-" * 30,
        ])
        for attraction in attractions:
            if isinstance(attraction, dict):
                lines.append(
                    f"- {attraction.get('name', 'Attraction')} "
                    f"({attraction.get('category', 'Attraction')})"
                )
            else:
                lines.append(f"- {attraction}")
        lines.append("")

    if restaurants:
        lines.extend([
            "RESTAURANTS & CAFÉS",
            "-" * 30,
        ])
        for restaurant in restaurants:
            if isinstance(restaurant, dict):
                rating = restaurant.get("rating", "")
                rating_text = (
                    f" — ⭐ {float(rating):.1f}/5"
                    if rating
                    else ""
                )
                lines.append(
                    f"- {restaurant.get('name', 'Restaurant')}"
                    f"{rating_text}"
                )
            else:
                lines.append(f"- {restaurant}")
        lines.append("")

    if explanations:
        lines.extend([
            "WHY THIS PLAN?",
            "-" * 30,
        ])
        for explanation in explanations:
            lines.append(f"- {explanation}")
        lines.append("")

    if conflicts:
        lines.extend([
            "PLANNING WARNINGS",
            "-" * 30,
        ])
        for conflict in conflicts:
            if isinstance(conflict, dict):
                lines.append(
                    f"- {conflict.get('message', 'Planning warning')}"
                )
            else:
                lines.append(f"- {conflict}")
        lines.append("")

    if itinerary:
        lines.extend([
            "DAILY ITINERARY",
            "-" * 30,
        ])

        for day in itinerary:
            lines.append(
                f"\n{day.get('date', 'Day')}"
            )

            activities = day.get(
                "activities",
                [],
            )

            if not activities:
                lines.append(
                    "  No activities scheduled."
                )
                continue

            for activity in activities:
                if isinstance(activity, dict):
                    lines.append(
                        f"  {activity.get('start_time', '')} – "
                        f"{activity.get('end_time', '')}: "
                        f"{activity.get('name', 'Activity')}"
                    )

            lines.append(
                f"  Activity time: "
                f"{float(day.get('activity_hours', 0) or 0):.2f}h"
            )
            lines.append(
                f"  Travel time: "
                f"{float(day.get('travel_hours', 0) or 0):.2f}h"
            )

    lines.extend([
        "",
        "=" * 55,
        "Generated by TravelMind — Intelligent Agentic Travel Planner",
    ])

    plain_text = "\n".join(lines)

    # ------------------------------
    # HTML transcript
    # ------------------------------

    def esc(value):
        return escape(str(value))

    html_parts = [
        "<html><body>",
        "<h1>✈️ TravelMind — Final Travel Plan</h1>",
        f"<h2>{esc(plan_name)}</h2>",
        "<ul>",
        f"<li><b>Route:</b> {esc(origin)} → {esc(destination)}</li>",
        f"<li><b>Dates:</b> {esc(start_date)} → {esc(end_date)}</li>",
        f"<li><b>Travellers:</b> {esc(travellers)}</li>",
        f"<li><b>Budget:</b> £{budget:.2f}</li>",
        f"<li><b>Food preference:</b> {esc(food_preference)}</li>",
        f"<li><b>Total cost:</b> £{total_cost:.2f}</li>",
        f"<li><b>Planning score:</b> {score:.2f}/100</li>",
        "</ul>",
    ]

    if flight:
        html_parts.extend([
            "<h2>✈️ Flight</h2>",
            "<ul>",
            f"<li><b>Airline:</b> {esc(flight.get('airline', 'Unknown'))}</li>",
            f"<li><b>Route:</b> {esc(flight.get('origin', ''))} → {esc(flight.get('destination', ''))}</li>",
            f"<li><b>Departure:</b> {esc(flight.get('departure', ''))}</li>",
            f"<li><b>Arrival:</b> {esc(flight.get('arrival', ''))}</li>",
            f"<li><b>Price:</b> £{float(flight.get('total_price', 0) or 0):.2f}</li>",
            f"<li><b>Stops:</b> {esc(flight.get('stops', 0))}</li>",
            "</ul>",
        ])

    if hotel:
        html_parts.extend([
            "<h2>🏨 Accommodation</h2>",
            "<ul>",
            f"<li><b>{esc(hotel.get('name', 'Hotel'))}</b></li>",
            f"<li>Rating: ⭐ {esc(hotel.get('rating', 'N/A'))}/5</li>",
            f"<li>Address: {esc(hotel.get('address', ''))}</li>",
            f"<li>Price: £{float(hotel.get('total_price', 0) or 0):.2f}</li>",
            "</ul>",
        ])

    if attractions:
        html_parts.append("<h2>📍 Attractions</h2><ul>")
        for attraction in attractions:
            if isinstance(attraction, dict):
                html_parts.append(
                    f"<li><b>{esc(attraction.get('name', 'Attraction'))}</b> "
                    f"— {esc(attraction.get('category', 'Attraction'))}</li>"
                )
            else:
                html_parts.append(f"<li>{esc(attraction)}</li>")
        html_parts.append("</ul>")

    if restaurants:
        html_parts.append("<h2>🍽️ Restaurants & Cafés</h2><ul>")
        for restaurant in restaurants:
            if isinstance(restaurant, dict):
                rating = restaurant.get("rating", "")
                rating_text = (
                    f" — ⭐ {float(rating):.1f}/5"
                    if rating
                    else ""
                )
                html_parts.append(
                    f"<li><b>{esc(restaurant.get('name', 'Restaurant'))}</b>"
                    f"{rating_text}</li>"
                )
            else:
                html_parts.append(f"<li>{esc(restaurant)}</li>")
        html_parts.append("</ul>")

    if explanations:
        html_parts.append("<h2>💡 Why this plan?</h2><ul>")
        for explanation in explanations:
            html_parts.append(
                f"<li>{esc(explanation)}</li>"
            )
        html_parts.append("</ul>")

    if itinerary:
        html_parts.append("<h2>📅 Daily Itinerary</h2>")

        for day in itinerary:
            html_parts.append(
                f"<h3>{esc(day.get('date', 'Day'))}</h3>"
            )

            activities = day.get(
                "activities",
                [],
            )

            if not activities:
                html_parts.append(
                    "<p>No activities scheduled.</p>"
                )
                continue

            html_parts.append("<ul>")

            for activity in activities:
                if isinstance(activity, dict):
                    html_parts.append(
                        f"<li><b>"
                        f"{esc(activity.get('start_time', ''))} – "
                        f"{esc(activity.get('end_time', ''))}"
                        f"</b> "
                        f"{esc(activity.get('name', 'Activity'))}</li>"
                    )

            html_parts.append("</ul>")

            html_parts.append(
                f"<p>Activity time: "
                f"{float(day.get('activity_hours', 0) or 0):.2f}h<br>"
                f"Travel time: "
                f"{float(day.get('travel_hours', 0) or 0):.2f}h<br>"
                f"Total time: "
                f"{float(day.get('total_hours', 0) or 0):.2f}h</p>"
            )

    html_parts.extend([
        "<hr>",
        "<p><b>Generated by TravelMind</b><br>",
        "Your Intelligent Agentic Travel Planner</p>",
        "</body></html>",
    ])

    html_text = "".join(html_parts)

    return plain_text, html_text


def send_travel_plan_email(
    recipient_email: str,
    state: dict,
):
    """
    Send the final TravelMind transcript using SMTP.

    Required .env variables:
        SMTP_HOST
        SMTP_PORT
        SMTP_USERNAME
        SMTP_PASSWORD
        SMTP_FROM_EMAIL

    For Gmail, use an App Password rather than your normal password.
    """

    smtp_host = os.getenv(
        "SMTP_HOST"
    )
    smtp_port = int(
        os.getenv(
            "SMTP_PORT",
            "587",
        )
    )
    smtp_username = os.getenv(
        "SMTP_USERNAME"
    )
    smtp_password = os.getenv(
        "SMTP_PASSWORD"
    )
    smtp_from = os.getenv(
        "SMTP_FROM_EMAIL",
        smtp_username,
    )

    missing = []

    if not smtp_host:
        missing.append("SMTP_HOST")

    if not smtp_username:
        missing.append("SMTP_USERNAME")

    if not smtp_password:
        missing.append("SMTP_PASSWORD")

    if not smtp_from:
        missing.append("SMTP_FROM_EMAIL")

    if missing:
        raise ValueError(
            "Email configuration is missing from .env: "
            + ", ".join(missing)
        )

    plain_text, html_text = build_travel_plan_email(
        state
    )

    destination = state.get(
        "destination",
        "Trip",
    )

    msg = EmailMessage()

    msg["Subject"] = (
        f"✈️ Your TravelMind Plan — {destination}"
    )
    msg["From"] = smtp_from
    msg["To"] = recipient_email

    msg.set_content(
        plain_text
    )

    msg.add_alternative(
        html_text,
        subtype="html",
    )

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=30,
    ) as server:

        server.starttls()

        server.login(
            smtp_username,
            smtp_password,
        )

        server.send_message(
            msg
        )



# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="TravelMind",
    page_icon="✈️",
    layout="wide",
)


# ==================================================
# PAGE HEADER
# ==================================================

st.title("✈️ TravelMind")

st.subheader(
    "Your Intelligent Agentic Travel Planner"
)

st.write(
    "Plan, evaluate, optimise and refine your "
    "trip with an AI travel agent."
)

st.divider()


# ==================================================
# SESSION STATE
# ==================================================

if "trip_state" not in st.session_state:
    st.session_state.trip_state = None

if "plan_generated" not in st.session_state:
    st.session_state.plan_generated = False

if "show_replan_form" not in st.session_state:
    st.session_state.show_replan_form = False

if "saved_trip" not in st.session_state:
    st.session_state.saved_trip = None

if "show_save_dialog" not in st.session_state:
    st.session_state.show_save_dialog = False


# ==================================================
# INITIAL TRIP FORM
# ==================================================

trip = render_trip_form()


# ==================================================
# TRAVEL HISTORY
# ==================================================

existing_user = None
saved_trips = []

if trip["name"].strip():

    existing_user = get_user_by_name(
        trip["name"]
    )

    if existing_user:

        saved_trips = get_saved_trips(
            existing_user["user_id"]
        )


# ==================================================
# MAIN ACTION BUTTONS
# ==================================================

st.divider()

col1, col2 = st.columns(2)

with col1:

    plan_clicked = st.button(
        "✨ PLAN MY TRIP",
        use_container_width=True,
    )

with col2:

    history_clicked = st.button(
        "📋 MY TRAVEL HISTORY",
        use_container_width=True,
        disabled=len(saved_trips) == 0,
    )


# ==================================================
# PLAN MY TRIP
# ==================================================

if plan_clicked:

    errors = validate_trip_input(trip)

    if errors:

        st.error(
            "Please fix the following:"
        )

        for error in errors:

            st.write(
                f"• {error}"
            )

    else:

        initial_state = {
            "name": trip["name"],
            "origin": trip["origin"],
            "destination": trip["destination"],
            "start_date": str(
                trip["start_date"]
            ),
            "end_date": str(
                trip["end_date"]
            ),
            "travellers": trip["travellers"],
            "budget": trip["budget"],
            "preferences": trip["preferences"],
            "food_preference": trip.get("food_preference", "No Food Preference"),
            "priorities": trip["priorities"],
            "replan_count": 0,
            "replan_required": False,
            "user_replan_requested": False,
            "user_replan_changes": {},
        }

        with st.spinner(
            "🤖 TravelMind is planning your trip..."
        ):

            try:

                result = travel_graph.invoke(
                    initial_state
                )

                st.session_state.trip_state = result

                st.session_state.plan_generated = True

                st.session_state.show_replan_form = False

                st.session_state.saved_trip = None

                st.rerun()

            except Exception as e:
                import traceback

                st.error(f"Travel planning failed: {e}")

                print("\n" + "=" * 70)
                print("TRAVELMIND FULL ERROR")
                print("=" * 70)
                traceback.print_exc()
                print("=" * 70)

                # Show the full traceback in the Streamlit UI as well.
                with st.expander("🔎 Technical error details"):
                    st.code(traceback.format_exc())


# ==================================================
# DISPLAY GENERATED PLAN
# ==================================================

if st.session_state.plan_generated:

    state = st.session_state.trip_state

    selected_plan = state.get(
        "selected_plan"
    )

    st.divider()

    st.header("🗺️ Your Travel Plan")


    # ==================================================
    # NO FEASIBLE PLAN
    # ==================================================

    if not selected_plan:

        st.error(
            "TravelMind could not find a feasible "
            "plan within your current constraints."
        )

        conflicts = state.get(
            "conflicts",
            [],
        )

        if conflicts:

            st.subheader(
                "⚠️ Planning Conflicts"
            )

            for conflict in conflicts:

                if isinstance(conflict, dict):
                    message = conflict.get(
                        "message",
                        "Planning conflict detected.",
                    )
                else:
                    message = str(conflict)

                st.warning(message)


    # ==================================================
    # FEASIBLE PLAN
    # ==================================================

    else:

        st.success(
            f"✅ {selected_plan.get('name', 'Travel Plan')} "
            "selected successfully."
        )


        # ==================================================
        # PLAN SUMMARY
        # ==================================================

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "💷 Total Cost",
                f"£{float(selected_plan.get('total_cost', 0)):.2f}",
            )

        with col2:

            st.metric(
                "💰 Budget",
                f"£{float(state.get('budget', 0)):.2f}",
            )

        with col3:

            st.metric(
                "⭐ Planning Score",
                f"{float(selected_plan.get('score', 0)):.2f}/100",
            )

        with col4:

            st.metric(
                "👥 Travellers",
                state.get(
                    "travellers",
                    0,
                ),
            )


        st.divider()


        # ==================================================
        # EXPLANATION
        # ==================================================

        explanations = state.get(
            "explanations",
            [],
        )

        if explanations:

            st.subheader(
                "💡 Why this plan?"
            )

            for explanation in explanations:

                st.write(
                    f"• {explanation}"
                )


        # ==================================================
        # FLIGHT
        # ==================================================

        flight = selected_plan.get(
            "flight",
            {},
        )

        if flight:

            st.subheader(
                "✈️ Flight"
            )

            st.write(
                f"**{flight.get('airline', 'Unknown')}**"
            )

            st.write(
                f"{flight.get('origin', '')} → "
                f"{flight.get('destination', '')}"
            )

            st.write(
                f"Departure: "
                f"{flight.get('departure', '')}"
            )

            st.write(
                f"Arrival: "
                f"{flight.get('arrival', '')}"
            )

            st.write(
                f"Price: "
                f"£{float(flight.get('total_price', 0)):.2f}"
            )

            st.write(
                f"Stops: "
                f"{flight.get('stops', 0)}"
            )


        # ==================================================
        # HOTEL
        # ==================================================

        hotel = selected_plan.get(
            "hotel",
            {},
        )

        if hotel:

            st.subheader(
                "🏨 Accommodation"
            )

            st.write(
                f"**{hotel.get('name', 'Hotel')}**"
            )

            if hotel.get("rating"):

                st.write(
                    f"Rating: ⭐ "
                    f"{hotel.get('rating')}/5"
                )

            if hotel.get("address"):

                st.write(
                    f"Address: "
                    f"{hotel.get('address')}"
                )

            st.write(
                f"Price: "
                f"£{float(hotel.get('total_price', 0)):.2f}"
            )


        # ==================================================
        # ATTRACTIONS
        # ==================================================

        attractions = selected_plan.get(
            "attractions",
            [],
        )

        if attractions:

            st.subheader(
                "📍 Attractions"
            )

            for attraction in attractions:

                if not isinstance(attraction, dict):
                    st.write(f"• {attraction}")
                    continue

                attraction_name = attraction.get(
                    "name",
                    "Attraction",
                )

                category = attraction.get(
                    "category",
                    "Attraction",
                )

                rating = attraction.get(
                    "rating"
                )

                st.write(
                    f"• **{attraction_name}** "
                    f"— {category}"
                )

                if rating:

                    st.caption(
                        f"⭐ {rating}/5"
                    )


        # ==================================================
        # RESTAURANTS & CAFÉS
        # ==================================================

        restaurants = selected_plan.get(
            "restaurants",
            [],
        )

        if restaurants:
            st.subheader("🍽️ Restaurants & Cafés")

            food_preference = state.get(
                "food_preference",
                "No Food Preference",
            )

            st.caption(
                f"Food preference: **{food_preference}**"
            )

            for restaurant in restaurants:
                if not isinstance(restaurant, dict):
                    st.write(f"• {restaurant}")
                    continue

                name = restaurant.get(
                    "name",
                    "Restaurant",
                )

                rating = restaurant.get(
                    "rating",
                    0,
                )

                category = restaurant.get(
                    "category",
                    restaurant.get(
                        "cuisine",
                        "Restaurant",
                    ),
                )

                address = restaurant.get(
                    "address",
                    "",
                )

                price = restaurant.get(
                    "price_level",
                    restaurant.get("price", ""),
                )

                if isinstance(price, int):
                    price_display = "£" * max(
                        1,
                        min(price, 4),
                    )
                else:
                    price_display = str(
                        price or ""
                    )

                st.write(
                    f"**🍴 {name}**"
                )

                details = []

                if category:
                    details.append(
                        str(category)
                    )

                if rating:
                    details.append(
                        f"⭐ {float(rating):.1f}/5"
                    )

                if price_display:
                    details.append(
                        price_display
                    )

                if details:
                    st.caption(
                        " • ".join(details)
                    )

                if address:
                    st.caption(
                        f"📍 {address}"
                    )

                if restaurant.get(
                    "website"
                ):
                    st.caption(
                        f"🌐 {restaurant['website']}"
                    )

        # ==================================================
        # DAILY ITINERARY
        # ==================================================


        itinerary = state.get(
            "daily_itinerary",
            [],
        )

        if itinerary:

            st.subheader(
                "📅 Daily Itinerary"
            )

            for day in itinerary:

                with st.expander(
                    f"📅 {day.get('date', 'Day')}"
                ):

                    st.write(
                        f"Activity time: "
                        f"{float(day.get('activity_hours', 0)):.2f} hours"
                    )

                    st.write(
                        f"Travel time: "
                        f"{float(day.get('travel_hours', 0)):.2f} hours"
                    )

                    st.write(
                        f"Total time: "
                        f"{float(day.get('total_hours', 0)):.2f} hours"
                    )

                    activities = day.get(
                        "activities",
                        [],
                    )

                    for activity in activities:

                        if not isinstance(activity, dict):
                            st.write(f"• {activity}")
                            continue

                        st.write(
                            f"**{activity.get('start_time', '')} – "
                            f"{activity.get('end_time', '')}** "
                            f"{activity.get('name', 'Activity')}"
                        )


        # ==================================================
        # DATA QUALITY
        # ==================================================

        data_quality = state.get(
            "data_quality",
            {},
        )

        if data_quality:

            st.subheader(
                "📊 Data Quality"
            )

            for tool_name, quality in data_quality.items():

                if isinstance(quality, dict):
                    status = quality.get("status", "unknown")
                    message = quality.get("message", "")
                elif isinstance(quality, list):
                    status = "available"
                    message = ", ".join(str(item) for item in quality)
                else:
                    status = str(quality)
                    message = ""

                st.write(
                    f"**{tool_name.title()}:** {status}"
                )

                if message:
                    st.caption(message)


        # ==================================================
        # PLANNING CONFLICTS
        # ==================================================

        conflicts = state.get(
            "conflicts",
            [],
        )

        if conflicts:

            st.subheader(
                "⚠️ Planning Warnings"
            )

            for conflict in conflicts:

                st.warning(
                    conflict.get(
                        "message",
                        "Planning conflict detected.",
                    )
                )


        st.divider()


        # ==================================================
        # MODIFY & REPLAN
        # ==================================================

        if st.button(
            "🔄 MODIFY & REPLAN",
            use_container_width=True,
        ):

            st.session_state.show_replan_form = True


        if st.session_state.show_replan_form:

            st.subheader(
                "✏️ Modify Your Trip"
            )

            st.info(
                "Change your requirements and "
                "TravelMind will generate a new plan."
            )

            current_state = (
                st.session_state.trip_state
            )


            # ----------------------------------------------
            # Destination
            # ----------------------------------------------

            new_destination = st.text_input(
                "Destination",
                value=current_state.get(
                    "destination",
                    "",
                ),
                key="replan_destination",
            )


            # ----------------------------------------------
            # Budget
            # ----------------------------------------------

            new_budget = st.number_input(
                "Budget (£)",
                min_value=1.0,
                value=float(
                    current_state.get(
                        "budget",
                        800.0,
                    )
                ),
                step=50.0,
                key="replan_budget",
            )


            # ----------------------------------------------
            # Travellers
            # ----------------------------------------------

            new_travellers = st.number_input(
                "Travellers",
                min_value=1,
                max_value=20,
                value=int(
                    current_state.get(
                        "travellers",
                        1,
                    )
                ),
                step=1,
                key="replan_travellers",
            )


            # ----------------------------------------------
            # Preferences
            # ----------------------------------------------

            new_food_preference = st.selectbox(
                "🍽️ Food Preference",
                [
                    "No Food Preference",
                    "Vegetarian",
                    "Non-Vegetarian",
                    "Vegan",
                ],
                index=[
                    "No Food Preference",
                    "Vegetarian",
                    "Non-Vegetarian",
                    "Vegan",
                ].index(
                    current_state.get(
                        "food_preference",
                        "No Food Preference",
                    )
                    if current_state.get(
                        "food_preference",
                        "No Food Preference",
                    )
                    in [
                        "No Food Preference",
                        "Vegetarian",
                        "Non-Vegetarian",
                        "Vegan",
                    ]
                    else "No Food Preference"
                ),
                key="replan_food_preference",
            )


            new_preferences = st.text_input(
                "Preferences",
                value=current_state.get(
                    "preferences",
                    "",
                ),
                key="replan_preferences",
            )


            # ----------------------------------------------
            # Replan
            # ----------------------------------------------

            if st.button(
                "🚀 REPLAN TRIP",
                use_container_width=True,
            ):

                changes = {
                    "destination": new_destination,
                    "budget": new_budget,
                    "travellers": new_travellers,
                    "preferences": new_preferences,
                    "food_preference": new_food_preference,
                }

                current_state[
                    "user_replan_changes"
                ] = changes

                current_state[
                    "user_replan_requested"
                ] = True


                with st.spinner(
                    "🤖 TravelMind is replanning..."
                ):

                    try:

                        updated_state = (
                            travel_graph.invoke(
                                current_state
                            )
                        )

                        st.session_state.trip_state = (
                            updated_state
                        )

                        st.session_state.show_replan_form = (
                            False
                        )

                        st.session_state.saved_trip = (
                            None
                        )

                        st.success(
                            "✅ Your trip has been replanned!"
                        )

                        st.rerun()

                    except Exception as exc:

                        st.error(
                            f"Replanning failed: {exc}"
                        )


        # ==================================================
    # ==================================================
# SAVE TRAVEL PLAN
# ==================================================

if (
    st.session_state.plan_generated
    and st.session_state.trip_state
    and st.session_state.trip_state.get("selected_plan")
):

    st.divider()

    if st.session_state.saved_trip:

        st.success(
            "✅ This travel plan has already been saved."
        )

    else:

        if st.button(
            "💾 SAVE TRAVEL PLAN",
            use_container_width=True,
            key="save_travel_plan",
        ):
            st.session_state.show_save_dialog = True


        # --------------------------------------------------
        # SAVE DIALOG
        # --------------------------------------------------

        if st.session_state.show_save_dialog:

            @st.dialog("💾 Save Your Travel Plan")
            def save_plan_dialog():

                st.write(
                    "Your current TravelMind plan is ready to be saved."
                )

                st.info(
                    "Enter your email address so the saved plan "
                    "can be associated with your account."
                )

                email = st.text_input(
                    "📧 Email address",
                    placeholder="example@email.com",
                    key="save_plan_email",
                )

                st.caption(
                    "Your email is stored with your TravelMind user "
                    "record. Email delivery will be connected in the "
                    "next step."
                )

                col1, col2 = st.columns(2)

                with col1:

                    confirm_save = st.button(
                        "✅ CONFIRM & SAVE",
                        use_container_width=True,
                        type="primary",
                    )

                with col2:

                    cancel_save = st.button(
                        "Cancel",
                        use_container_width=True,
                    )

                if cancel_save:

                    st.session_state.show_save_dialog = False
                    st.rerun()

                if confirm_save:

                    email_clean = email.strip()

                    # Basic email validation.
                    email_pattern = (
                        r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
                    )

                    if not email_clean:

                        st.error(
                            "Please enter your email address."
                        )

                    elif not re.match(
                        email_pattern,
                        email_clean,
                    ):

                        st.error(
                            "Please enter a valid email address."
                        )

                    else:

                        try:

                            current_state = (
                                st.session_state.trip_state
                            )

                            trip_id = current_state.get(
                                "trip_id"
                            )

                            itinerary_id = current_state.get(
                                "itinerary_id"
                            )

                            if not trip_id:

                                st.error(
                                    "No draft trip was found. "
                                    "Please generate the plan again."
                                )

                            elif not itinerary_id:

                                st.error(
                                    "No generated itinerary was found. "
                                    "Please generate the plan again."
                                )

                            else:

                                # Send the complete final transcript directly
                                # to the email entered by the user.
                                #
                                # We do NOT require updating the users table here.
                                # The email entered at save time is simply the
                                # recipient for this travel-plan delivery.
                                send_travel_plan_email(
                                    email_clean,
                                    current_state,
                                )

                                # Email succeeded — now mark the trip as
                                # explicitly saved.
                                saved_trip = (
                                    mark_trip_as_saved(
                                        trip_id
                                    )
                                )

                                # Mark only the selected itinerary as
                                # final and saved.
                                mark_itinerary_as_final(
                                    itinerary_id
                                )

                                mark_itinerary_as_saved(
                                    itinerary_id
                                )

                                st.session_state.saved_trip = (
                                    saved_trip
                                )

                                st.session_state.show_save_dialog = (
                                    False
                                )

                                st.success(
                                    f"✅ Travel plan saved and emailed to {email_clean}!"
                                )

                                st.rerun()

                        except Exception as exc:

                            st.error(
                                f"Could not save travel plan: {exc}"
                            )

            save_plan_dialog()


# ==================================================
# TRAVEL HISTORY
# ==================================================

if history_clicked:

    st.divider()

    st.subheader(
        "📋 Your Travel History"
    )

    if saved_trips:

        for saved_trip in saved_trips:

            with st.expander(
                f"{saved_trip['origin']} → "
                f"{saved_trip['destination']}"
            ):

                st.write(
                    f"**Dates:** "
                    f"{saved_trip['start_date']} → "
                    f"{saved_trip['end_date']}"
                )

                st.write(
                    f"**Travellers:** "
                    f"{saved_trip['travellers']}"
                )

                st.write(
                    f"**Budget:** "
                    f"£{saved_trip['budget']}"
                )

                st.write(
                    f"**Created:** "
                    f"{saved_trip['created_at']}"
                )

                st.write(
                    f"**Saved:** "
                    f"{saved_trip.get('is_saved', False)}"
                )
