import streamlit as st
import re
import os
import smtplib
import traceback

from pathlib import Path
from dotenv import load_dotenv
from email.message import EmailMessage
from html import escape


# ==================================================
# ENVIRONMENT
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent

# Load local .env
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path.cwd() / ".env")


# Load Streamlit Cloud secrets
SECRET_KEYS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SERPAPI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
    "SMTP_USE_SSL",
]

for key in SECRET_KEYS:
    if not os.getenv(key):
        try:
            if key in st.secrets:
                os.environ[key] = str(st.secrets[key])
        except Exception:
            pass


# ==================================================
# PROJECT IMPORTS
# ==================================================

from ui.forms import render_trip_form, validate_trip_input
from database.users import get_user_by_name
from database.history import get_saved_trips
from database.trips import mark_trip_as_saved
from agent.graph import travel_graph
from database.itineraries import (
    mark_itinerary_as_final,
    mark_itinerary_as_saved,
)
from tools.flights import (
    search_flights,
    search_return_flights,
    combine_selected_flights,
)


# ==================================================
# EMAIL HELPERS
# ==================================================


# ==================================================
# EMAIL HELPERS
# ==================================================

def _safe_text(value):
    if value is None:
        return ""
    return str(value)


def build_travel_plan_email(state: dict):
    """Build the final TravelMind plan as plain text and HTML."""

    selected_plan = state.get("selected_plan") or {}

    destination = _safe_text(
        state.get("destination")
        or selected_plan.get("destination")
        or "your trip"
    )

    origin = _safe_text(
        state.get("origin")
        or selected_plan.get("origin")
        or ""
    )

    start_date = _safe_text(state.get("start_date", ""))
    end_date = _safe_text(state.get("end_date", ""))
    travellers = state.get("travellers", "")
    budget = state.get("budget", 0)
    total_cost = selected_plan.get("total_cost", 0)
    score = selected_plan.get("score", 0)

    lines = [
        "TRAVELMIND — FINAL TRAVEL PLAN",
        "=" * 50,
        f"Route: {origin} → {destination}",
        f"Dates: {start_date} → {end_date}",
        f"Travellers: {travellers}",
        f"Budget: £{float(budget or 0):.2f}",
        f"Estimated total: £{float(total_cost or 0):.2f}",
        f"Planning score: {float(score or 0):.2f}/100",
        "",
    ]

    # ------------------------------
    # FLIGHT
    # ------------------------------

    flight = selected_plan.get("flight") or {}

    if flight:
        lines += [
            "FLIGHT",
            "-" * 30,
            f"Airline: {_safe_text(flight.get('airline', 'Unknown'))}",
            f"Route: {_safe_text(flight.get('origin', origin))} → "
            f"{_safe_text(flight.get('destination', destination))}",
            f"Departure: {_safe_text(flight.get('departure', 'N/A'))}",
            f"Arrival: {_safe_text(flight.get('arrival', 'N/A'))}",
            f"Price: £{float(flight.get('total_price', 0) or 0):.2f}",
            f"Stops: {_safe_text(flight.get('stops', 0))}",
            "",
        ]

    # ------------------------------
    # HOTEL
    # ------------------------------

    hotel = selected_plan.get("hotel") or {}

    if hotel:
        lines += [
            "ACCOMMODATION",
            "-" * 30,
            f"Hotel: {_safe_text(hotel.get('name', 'Hotel'))}",
            f"Rating: {_safe_text(hotel.get('rating', 'N/A'))}/5",
            f"Address: {_safe_text(hotel.get('address', 'N/A'))}",
            f"Price: £{float(hotel.get('total_price', 0) or 0):.2f}",
            "",
        ]

    # ------------------------------
    # ATTRACTIONS
    # ------------------------------

    attractions = selected_plan.get("attractions") or []

    if attractions:
        lines += [
            "ATTRACTIONS",
            "-" * 30,
        ]

        for item in attractions:

            if isinstance(item, dict):

                name = item.get(
                    "name",
                    "Attraction",
                )

                category = item.get(
                    "category",
                    "Attraction",
                )

                rating = item.get("rating")

                suffix = f" — {category}"

                if rating:
                    suffix += f" — ⭐ {rating}/5"

                lines.append(
                    f"• {name}{suffix}"
                )

            else:
                lines.append(
                    f"• {item}"
                )

        lines.append("")

    # ------------------------------
    # RESTAURANTS
    # ------------------------------

    restaurants = selected_plan.get("restaurants") or []

    if restaurants:

        lines += [
            "RESTAURANTS & CAFÉS",
            "-" * 30,
        ]

        for item in restaurants:

            if isinstance(item, dict):

                name = item.get(
                    "name",
                    "Restaurant",
                )

                category = (
                    item.get("category")
                    or item.get("cuisine")
                    or "Restaurant"
                )

                rating = item.get("rating")

                suffix = f" — {category}"

                if rating:
                    suffix += f" — ⭐ {rating}/5"

                lines.append(
                    f"• {name}{suffix}"
                )

            else:
                lines.append(
                    f"• {item}"
                )

        lines.append("")

    # ------------------------------
    # DAILY ITINERARY
    # ------------------------------

    itinerary = state.get("daily_itinerary") or []

    if itinerary:

        lines += [
            "DAILY ITINERARY",
            "=" * 50,
        ]

        for day in itinerary:

            day_title = _safe_text(
                day.get("date", "Day")
            )

            lines += [
                "",
                day_title,
                "-" * 40,
            ]

            weather_note = day.get(
                "weather_note"
            )

            if weather_note:
                lines.append(
                    f"Weather: {_safe_text(weather_note)}"
                )

            activities = day.get(
                "activities",
                [],
            )

            if not activities:
                lines.append(
                    "No activities scheduled."
                )
                continue

            for activity in activities:

                if not isinstance(activity, dict):
                    lines.append(
                        f"• {activity}"
                    )
                    continue

                activity_type = _safe_text(
                    activity.get("activity_type")
                    or activity.get("category")
                    or "activity"
                )

                activity_type = (
                    activity_type
                    .replace("_", " ")
                    .upper()
                )

                name = _safe_text(
                    activity.get(
                        "name",
                        "Activity",
                    )
                )

                start = _safe_text(
                    activity.get(
                        "start_time",
                        "",
                    )
                )

                end = _safe_text(
                    activity.get(
                        "end_time",
                        "",
                    )
                )

                rating = activity.get("rating")
                cost = activity.get(
                    "estimated_cost"
                )

                address = _safe_text(
                    activity.get(
                        "address",
                        "",
                    )
                )

                notes = _safe_text(
                    activity.get(
                        "notes",
                        "",
                    )
                )

                line = (
                    f"{activity_type}: "
                    f"{start} – {end} — {name}"
                )

                if rating:
                    line += (
                        f" — ⭐ {rating}/5"
                    )

                if cost not in (
                    None,
                    "",
                    0,
                    0.0,
                ):
                    try:
                        line += (
                            f" — £{float(cost):.2f}"
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        pass

                lines.append(line)

                if address:
                    lines.append(
                        f"  Address: {address}"
                    )

                if notes:
                    lines.append(
                        f"  Note: {notes}"
                    )

            spend = day.get(
                "estimated_spend",
                day.get(
                    "food_spend",
                    0,
                ),
            )

            if spend not in (
                None,
                "",
                0,
                0.0,
            ):
                try:
                    lines.append(
                        f"Estimated day spend: "
                        f"£{float(spend):.2f}"
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

    plain_text = "\n".join(lines)

    # ------------------------------
    # HTML EMAIL
    # ------------------------------

    html_parts = []

    for line in lines:

        if line == "":
            html_parts.append("<br>")

        elif line.startswith("="):
            html_parts.append("<hr>")

        elif line.startswith("-"):
            html_parts.append("<hr>")

        else:
            html_parts.append(
                "<div style='margin:4px 0'>"
                f"{escape(line)}"
                "</div>"
            )

    html_text = (
        "<html>"
        "<body style='font-family:Arial,sans-serif;"
        "line-height:1.5;'>"
        "<h2>✈️ TravelMind — Final Travel Plan</h2>"
        + "".join(html_parts)
        + "<hr>"
        "<p style='opacity:.7;'>"
        "This plan was generated by TravelMind."
        "</p>"
        "</body>"
        "</html>"
    )

    return plain_text, html_text


def _smtp_setting(name, default=None):
    """Read an SMTP setting safely and trim accidental spaces/quotes."""
    value = os.getenv(name, default)
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
        value = value[1:-1].strip()
    return value


def send_travel_plan_email(
    recipient_email: str,
    state: dict,
):
    """Send the complete final TravelMind plan through SMTP."""

    smtp_host = _smtp_setting("SMTP_HOST")
    smtp_port_raw = _smtp_setting("SMTP_PORT", "587")
    smtp_username = _smtp_setting("SMTP_USERNAME")
    smtp_password = _smtp_setting("SMTP_PASSWORD")
    smtp_from = _smtp_setting("SMTP_FROM_EMAIL") or smtp_username
    smtp_use_ssl = _smtp_setting("SMTP_USE_SSL", "false").lower() in {
        "1", "true", "yes", "on"
    }

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
            + ". For Gmail, use a Google App Password, not your normal Gmail password."
        )

    try:
        smtp_port = int(smtp_port_raw)
    except (TypeError, ValueError):
        raise ValueError("SMTP_PORT must be a number, for example 587.")

    plain_text, html_text = build_travel_plan_email(state)
    destination = _safe_text(state.get("destination", "Trip"))

    msg = EmailMessage()
    msg["Subject"] = f"✈️ Your TravelMind Plan — {destination}"
    msg["From"] = smtp_from
    msg["To"] = recipient_email
    msg.set_content(plain_text)
    msg.add_alternative(html_text, subtype="html")

    try:
        if smtp_use_ssl or smtp_port == 465:
            with smtplib.SMTP_SSL(
                smtp_host, smtp_port, timeout=30
            ) as server:
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                smtp_host, smtp_port, timeout=30
            ) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "Gmail rejected the SMTP login. Make sure SMTP_USERNAME is your Gmail address "
            "and SMTP_PASSWORD is a Google App Password (16 characters), not your normal Gmail password. "
            f"SMTP response: {exc.smtp_code} {exc.smtp_error.decode(errors='replace') if isinstance(exc.smtp_error, bytes) else exc.smtp_error}"
        ) from exc
    except smtplib.SMTPConnectError as exc:
        raise RuntimeError(
            f"Could not connect to the SMTP server {smtp_host}:{smtp_port}. "
            "Check SMTP_HOST/SMTP_PORT and your internet connection."
        ) from exc
    except smtplib.SMTPException as exc:
        raise RuntimeError(
            f"SMTP could not send the TravelMind email: {exc}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Network connection to the SMTP server failed: {exc}"
        ) from exc


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="TravelMind",
    page_icon="✈️",
    layout="wide",
)


# ==================================================
# TRAVELMIND — POLISHED UI
# ==================================================

st.markdown(
    """
    <style>
        /* Overall app */
        .stApp {
            background:
                radial-gradient(circle at 10% 0%, rgba(99,102,241,.08), transparent 28%),
                radial-gradient(circle at 90% 10%, rgba(14,165,233,.07), transparent 30%);
        }

        /* Main content width */
        .block-container {
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        /* Headings */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.035em;
        }

        h2, h3 {
            letter-spacing: -0.02em;
        }

        /* Buttons */
        .stButton > button {
            border-radius: 12px;
            min-height: 46px;
            font-weight: 700;
            transition: all .18s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 7px 18px rgba(0,0,0,.10);
        }

        /* Metrics */
        [data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 14px;
            padding: 12px 15px;
            background: rgba(255,255,255,.035);
        }

        /* Expanders */
        [data-testid="stExpander"] {
            border-radius: 14px !important;
            border: 1px solid rgba(128,128,128,.18) !important;
            overflow: hidden;
        }

        /* Inputs */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"],
        .stDateInput input {
            border-radius: 10px;
        }

        /* Itinerary cards */
        .tm-itinerary-card {
            border: 1px solid rgba(128,128,128,.20);
            border-radius: 16px;
            padding: 15px 17px;
            margin: 9px 0;
            background: rgba(255,255,255,.035);
            box-shadow: 0 3px 14px rgba(0,0,0,.045);
        }

        .tm-itinerary-card:hover {
            border-color: rgba(99,102,241,.35);
            box-shadow: 0 7px 20px rgba(0,0,0,.07);
        }

        .tm-type {
            font-size: .76rem;
            font-weight: 850;
            letter-spacing: .08em;
            opacity: .68;
            text-transform: uppercase;
        }

        .tm-time {
            font-size: 1.05rem;
            font-weight: 800;
            margin-top: 5px;
        }

        .tm-name {
            font-size: 1.04rem;
            font-weight: 700;
            margin-top: 4px;
        }

        .tm-meta {
            font-size: .86rem;
            opacity: .72;
            margin-top: 7px;
        }

        /* Flight section */
        .tm-flight-header {
            border-radius: 18px;
            padding: 18px 20px;
            border: 1px solid rgba(128,128,128,.18);
            background: linear-gradient(
                135deg,
                rgba(99,102,241,.09),
                rgba(14,165,233,.06)
            );
            margin-bottom: 14px;
        }

        .tm-flight-airline {
            font-size: 1.25rem;
            font-weight: 800;
        }

        .tm-flight-number {
            opacity: .70;
            font-size: .88rem;
            margin-top: 3px;
        }

        /* Section separators */
        hr {
            opacity: .25;
        }

        /* Success/info boxes */
        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        /* Hide excessive Streamlit decoration */
        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# PAGE HEADER
# ==================================================

st.markdown(
    """
    <div style="
        padding: 10px 0 4px 0;
    ">
        <div style="
            font-size: 2.35rem;
            font-weight: 850;
            letter-spacing: -0.045em;
        ">
            ✈️ TravelMind
        </div>
        <div style="
            font-size: 1.05rem;
            font-weight: 650;
            opacity: .72;
            margin-top: 2px;
        ">
            Your Intelligent Agentic Travel Planner
        </div>
        <div style="
            font-size: .92rem;
            opacity: .60;
            margin-top: 7px;
        ">
            Plan • Evaluate • Optimise • Replan • Explore
        </div>
    </div>
    """,
    unsafe_allow_html=True,
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

if "flight_selection_stage" not in st.session_state:
    st.session_state.flight_selection_stage = "idle"
if "flight_outbound_options" not in st.session_state:
    st.session_state.flight_outbound_options = []
if "flight_return_options" not in st.session_state:
    st.session_state.flight_return_options = []
if "selected_outbound_flight" not in st.session_state:
    st.session_state.selected_outbound_flight = None
if "selected_return_flight" not in st.session_state:
    st.session_state.selected_return_flight = None
if "selected_combined_flight" not in st.session_state:
    st.session_state.selected_combined_flight = None


# ==================================================
# INITIAL TRIP FORM
# ==================================================

trip = render_trip_form()


# ==================================================
# FLIGHT SELECTION
# ==================================================

def _flight_label(f):
    airline = f.get("airline", "Airline")
    number = f.get("flight_number", "Flight")
    dep = f.get("departure_time", "N/A")
    arr = f.get("arrival_time", "N/A")
    price = f.get("total_price", f.get("round_trip_total_price", 0))
    stops = f.get("stops", 0)
    return (
        f"{airline} {number} • {dep} → {arr} • "
        f"£{float(price or 0):.2f} • {stops} stop(s)"
    )


def _flight_score(flight, budget_share):
    """Score a real flight/flight-pair deterministically; lower is better."""
    try:
        price = float(flight.get("total_price", 0) or 0)
    except (TypeError, ValueError):
        price = float("inf")

    try:
        stops = int(flight.get("stops", 0) or 0)
    except (TypeError, ValueError):
        stops = 99

    try:
        duration = float(flight.get("duration_hours", 0) or 0)
    except (TypeError, ValueError):
        duration = 99.0

    over_budget = max(price - budget_share, 0)
    return over_budget * 1000 + price + stops * 35 + duration * 8


def _choose_best_flight(options, budget_share):
    """Choose a real API flight deterministically; never invent one."""
    valid = []
    for flight in options or []:
        if not isinstance(flight, dict):
            continue
        try:
            price = float(flight.get("total_price", 0) or 0)
        except (TypeError, ValueError):
            continue
        if price > 0:
            valid.append(flight)

    if not valid:
        return None

    within_budget = [
        f for f in valid
        if float(f.get("total_price", 0) or 0) <= budget_share
    ]
    candidates = within_budget or valid
    return min(candidates, key=lambda f: _flight_score(f, budget_share))


def _combine_flight_selection(outbound, return_flight=None):
    """Combine the actual selected outbound and return flights."""
    if not outbound:
        return None

    if return_flight:
        return combine_selected_flights(
            outbound,
            return_flight,
        )

    return combine_selected_flights(
        outbound,
        None,
    )


if st.session_state.flight_selection_stage != "idle":
    st.divider()
    st.subheader("✈️ Select Your Flights")
    st.caption(
        "TravelMind automatically selects suitable real flights "
        "using your budget and traveller requirements."
    )

    selected = st.session_state.get("selected_outbound_flight")
    selected_return = st.session_state.get("selected_return_flight")

    if selected and (
        st.session_state.flight_selection_stage == "ready"
    ):
        combined_selected = st.session_state.get("selected_combined_flight") or {}
        try:
            outbound_price = float(selected.get("total_price", 0) or 0)
        except (TypeError, ValueError):
            outbound_price = 0.0
        try:
            return_price = float(selected_return.get("total_price", 0) or 0) if selected_return else 0.0
        except (TypeError, ValueError):
            return_price = 0.0

        combined_price = outbound_price + return_price if selected_return else outbound_price
        trip_budget = float(trip.get("budget", 0) or 0)
        flight_overall_budget = trip_budget * 0.40

        if combined_price > flight_overall_budget:
            st.warning(
                f"🛫 Outbound candidate: {_flight_label(selected)}"
            )
            if selected_return:
                st.warning(
                    f"🛬 Return candidate: {_flight_label(selected_return)}"
                )
            st.caption(
                f"Flight combination: £{combined_price:,.2f}. "
                f"This is above TravelMind's initial flight allocation of "
                f"£{flight_overall_budget:,.2f} (40% of the £{trip_budget:,.2f} trip budget). "
                "The full planner will now check whether the complete trip is feasible."
            )
        else:
            st.success(
                f"🛫 Outbound selected automatically: {_flight_label(selected)}"
            )
            if selected_return:
                st.success(
                    f"🛬 Return selected automatically: {_flight_label(selected_return)}"
                )

        st.info(
            "🤖 TravelMind will now evaluate the complete trip — flights, hotel, food, "
            "activities and constraints — before confirming feasibility. "
            "Click **PLAN MY TRIP** below to continue."
        )

    elif st.session_state.flight_selection_stage == "outbound":
        st.info("🔎 TravelMind is evaluating the outbound flights...")

    elif st.session_state.flight_selection_stage == "return":
        st.info("🔄 TravelMind is evaluating the return flights...")

    elif st.session_state.flight_selection_stage == "one_way":
        st.info("🛫 TravelMind is evaluating the available flight...")


# ==================================================
# TRAVEL HISTORY
# ==================================================

existing_user = None
saved_trips = []

if trip.get("name", "").strip():

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

    # --------------------------------------------------
    # STEP 1 — SEARCH + AUTOMATICALLY SELECT FLIGHTS
    # --------------------------------------------------

    if st.session_state.flight_selection_stage == "idle":
        try:
            trip_type = trip.get(
                "trip_type",
                "Round Trip",
            )

            outbound_options = search_flights(
                trip["origin"],
                trip["destination"],
                trip["start_date"],
                trip.get("end_date"),
                trip["travellers"],
                trip_type,
            )

            st.session_state.flight_outbound_options = (
                outbound_options
            )

            if not outbound_options:
                st.error(
                    "No flights were found for the selected "
                    "route and dates."
                )
                st.stop()

            # Allocate part of the overall trip budget to flights.
            # This is a selection budget, not the final trip budget.
            total_budget = float(
                trip.get("budget", 0) or 0
            )

            flight_budget = max(
                total_budget * 0.40,
                0,
            )

            # For Round Trip, evaluate multiple real outbound tokens instead
            # of committing to the first outbound result. Some outbound tokens
            # can legitimately return no inbound options.
            if trip_type == "Round Trip":
                candidate_pairs = []

                with st.spinner("🔄 Finding real outbound + return flight combinations..."):
                    for outbound in outbound_options:
                        token = outbound.get("departure_token")
                        if not token:
                            continue

                        returns = search_return_flights(
                            trip["origin"],
                            trip["destination"],
                            trip["end_date"],
                            trip["travellers"],
                            token,
                            trip["start_date"],
                        )

                        for return_flight in returns or []:
                            try:
                                outbound_price = float(outbound.get("total_price", 0) or 0)
                                return_price = float(return_flight.get("total_price", 0) or 0)
                            except (TypeError, ValueError):
                                continue

                            if outbound_price <= 0 or return_price <= 0:
                                continue

                            combined = _combine_flight_selection(outbound, return_flight)
                            if combined:
                                candidate_pairs.append(combined)

                if not candidate_pairs:
                    st.error(
                        "No real return-flight combinations were returned for the available outbound flights. "
                        "Please try different dates or route."
                    )
                    st.stop()

                # Select the complete round trip using the overall trip budget
                # allocation, rather than selecting outbound and return independently.
                total_budget = float(trip.get("budget", 0) or 0)
                flight_budget = max(total_budget * 0.40, 0)
                combined = _choose_best_flight(candidate_pairs, flight_budget)

                if not combined:
                    st.error("TravelMind could not select a valid round-trip flight combination.")
                    st.stop()

                outbound = combined.get("outbound", {})
                return_flight = combined.get("return", {})
                st.session_state.selected_outbound_flight = outbound
                st.session_state.selected_return_flight = return_flight
                st.session_state.flight_return_options = [return_flight]
                st.session_state.selected_combined_flight = combined
                st.session_state.flight_selection_stage = "ready"

            else:
                outbound = _choose_best_flight(
                    outbound_options,
                    max(float(trip.get("budget", 0) or 0) * 0.40, 0),
                )

                if not outbound:
                    st.error("TravelMind could not select a valid outbound flight.")
                    st.stop()

                st.session_state.selected_outbound_flight = outbound
                combined = _combine_flight_selection(outbound, None)
                st.session_state.selected_return_flight = None
                st.session_state.selected_combined_flight = combined
                st.session_state.flight_selection_stage = "ready"


            st.rerun()

        except Exception as exc:
            st.error(
                f"Flight selection failed: {exc}"
            )

    # --------------------------------------------------
    # STEP 2 — RUN TRAVELMIND USING SELECTED FLIGHT
    # --------------------------------------------------

    elif st.session_state.flight_selection_stage == "ready":

        errors = validate_trip_input(trip)

        if errors:
            st.error("Please fix the following:")

            for error in errors:
                st.write(f"• {error}")

        else:
            selected_flight = (
                st.session_state.get(
                    "selected_combined_flight"
                )
                or _combine_flight_selection(
                    st.session_state.get(
                        "selected_outbound_flight"
                    ),
                    st.session_state.get(
                        "selected_return_flight"
                    ),
                )
            )

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
                "food_preference": trip.get(
                    "food_preference",
                    "No Food Preference",
                ),
                "priorities": trip["priorities"],
                "selected_flight": selected_flight,
                "flight": selected_flight,
                "flight_options": (
                    st.session_state.get(
                        "flight_outbound_options",
                        [],
                    )
                ),
                "return_flight_options": (
                    st.session_state.get(
                        "flight_return_options",
                        [],
                    )
                ),
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

                    st.error(
                        f"Travel planning failed: {e}"
                    )

                    print("\n" + "=" * 70)
                    print("TRAVELMIND FULL ERROR")
                    print("=" * 70)
                    traceback.print_exc()
                    print("=" * 70)

                    with st.expander(
                        "🔎 Technical error details"
                    ):
                        st.code(
                            traceback.format_exc()
                        )


# ==================================================
# DETERMINISTIC BUDGET / PREFERENCE GUIDANCE
# ==================================================

def _candidate_costs(state):
    """Return real candidate-plan costs from deterministic planner output."""
    candidates = state.get("candidate_plans", []) or []
    result = []
    for plan in candidates:
        if not isinstance(plan, dict):
            continue
        try:
            total = float(plan.get("total_cost", 0) or 0)
        except (TypeError, ValueError):
            continue
        if total > 0:
            result.append((str(plan.get("name", "Plan")), total))
    return sorted(result, key=lambda item: item[1])


def _budget_guidance(state, selected_plan=None):
    """
    Generate budget guidance using only deterministic candidate costs.

    Two cases are distinguished:
    1. A preference-heavy option is over budget, but a lower-cost feasible
       candidate exists.
    2. No candidate is feasible; the cheapest real candidate establishes the
       minimum currently observed requirement.
    """
    try:
        budget = float(state.get("budget", 0) or 0)
    except (TypeError, ValueError):
        budget = 0.0

    costs = _candidate_costs(state)
    if budget <= 0 or not costs:
        return None

    feasible = [(name, cost) for name, cost in costs if cost <= budget]
    cheapest_name, cheapest_cost = costs[0]

    # Case 2: nothing fits. Use the two cheapest real candidate plans as
    # the evidence-based suggested range when available.
    if not feasible:
        upper = costs[1][1] if len(costs) > 1 else cheapest_cost
        return {
            "type": "no_feasible",
            "budget": budget,
            "minimum": cheapest_cost,
            "minimum_name": cheapest_name,
            "range_low": cheapest_cost,
            "range_high": max(upper, cheapest_cost),
        }

    # Case 1: a higher-comfort / preference-heavy option does not fit, while
    # at least one lower-cost candidate does.
    comfort = next(
        ((name, cost) for name, cost in costs if name.lower() == "comfort focused"),
        None,
    )
    balanced = next(
        ((name, cost) for name, cost in costs if name.lower() == "balanced"),
        None,
    )

    if comfort and comfort[1] > budget:
        low = balanced[1] if balanced and balanced[1] > budget else comfort[1]
        # Ground the suggested range in actual candidate costs. Prefer the
        # cheapest over-budget candidate and the preference-heavy candidate.
        over_budget_costs = [cost for _, cost in costs if cost > budget]
        if over_budget_costs:
            low = min(over_budget_costs)
        high = max(over_budget_costs)
        return {
            "type": "preference_tradeoff",
            "budget": budget,
            "minimum": low,
            "range_low": low,
            "range_high": high,
            "comfort_cost": comfort[1],
            "feasible_name": feasible[0][0],
            "feasible_cost": feasible[0][1],
        }

    return None


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

        guidance = _budget_guidance(state)

        st.error(
            "TravelMind could not find a feasible "
            "plan within your current constraints."
        )

        if guidance and guidance.get("type") == "no_feasible":
            low = guidance["range_low"]
            high = guidance["range_high"]
            if high > low:
                range_text = f"£{low:,.0f}–£{high:,.0f}"
            else:
                range_text = f"at least £{low:,.0f}"

            st.warning(
                f"⚠️ Your entered budget of £{guidance['budget']:,.0f} "
                "does not currently fit the available trip options. "
                f"The cheapest complete candidate found by TravelMind is "
                f"approximately £{guidance['minimum']:,.0f}."
            )
            st.info(
                f"💡 **Suggested budget based on the current live results:** "
                f"{range_text}.\n\n"
                "This estimate is calculated by Python from the real candidate "
                "plans returned during this run; Gemini does not invent the range. "
                "You can increase the budget or change your preferences and replan."
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

        guidance = _budget_guidance(state, selected_plan)
        if guidance and guidance.get("type") == "preference_tradeoff":
            st.warning(
                f"⚠️ Your £{guidance['budget']:,.0f} budget fits a lower-cost "
                f"alternative, but the more preference-focused options exceed it. "
                f"The current preference-focused estimate is about "
                f"£{guidance['range_low']:,.0f}–£{guidance['range_high']:,.0f}."
            )
            st.info(
                "💡 You can keep the current budget and use the feasible plan, "
                "or increase the budget to better accommodate your selected preferences. "
                "The suggested range is calculated deterministically from the real "
                "candidate-plan costs returned in this run."
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
        # FLIGHT — COMPLETE DETAILS
        # ==================================================

        flight = selected_plan.get(
            "flight",
            {},
        )

        if flight:

            st.subheader("✈️ Flight Details")

            # ----------------------------------------------
            # BASIC FLIGHT INFORMATION
            # ----------------------------------------------

            airline = flight.get(
                "airline",
                "Airline unavailable",
            )

            flight_number = flight.get(
                "flight_number",
                "Flight number unavailable",
            )

            st.markdown(
                f"### ✈️ {airline}"
            )

            if flight.get("trip_type") == "Round Trip" and flight.get("return"):
                st.caption("🔄 Round-trip flight selected automatically")

            st.write(
                f"**Flight number:** {flight_number}"
            )

            # ----------------------------------------------
            # OUTBOUND / MAIN FLIGHT
            # ----------------------------------------------

            dep_col, arr_col = st.columns(2)

            with dep_col:

                st.markdown(
                    "#### 🛫 Departure"
                )

                st.write(
                    f"**Airport:** "
                    f"{flight.get('departure_airport_name', flight.get('departure_airport', 'N/A'))}"
                )

                st.write(
                    f"**Airport code:** "
                    f"{flight.get('departure_airport', 'N/A')}"
                )

                st.write(
                    f"**City:** "
                    f"{flight.get('departure_city', flight.get('origin', 'N/A'))}"
                )

                st.write(
                    f"**Date:** "
                    f"{flight.get('departure_date', 'N/A')}"
                )

                st.write(
                    f"**Time:** "
                    f"{flight.get('departure_time', 'N/A')}"
                )

            with arr_col:

                st.markdown(
                    "#### 🛬 Arrival"
                )

                st.write(
                    f"**Airport:** "
                    f"{flight.get('arrival_airport_name', flight.get('arrival_airport', 'N/A'))}"
                )

                st.write(
                    f"**Airport code:** "
                    f"{flight.get('arrival_airport', 'N/A')}"
                )

                st.write(
                    f"**City:** "
                    f"{flight.get('arrival_city', flight.get('destination', 'N/A'))}"
                )

                st.write(
                    f"**Date:** "
                    f"{flight.get('arrival_date', 'N/A')}"
                )

                st.write(
                    f"**Time:** "
                    f"{flight.get('arrival_time', 'N/A')}"
                )

            # ----------------------------------------------
            # RETURN / INBOUND FLIGHT
            # ----------------------------------------------

            return_leg = flight.get("return") or flight.get("return_flight") or {}

            if isinstance(return_leg, dict) and return_leg:
                st.markdown("#### 🛬 Return / Inbound")
                rdep, rarr = st.columns(2)

                with rdep:
                    st.write(
                        f"**Airport:** {return_leg.get('departure_airport_name', return_leg.get('departure_airport', 'N/A'))}"
                    )
                    st.write(f"**Airport code:** {return_leg.get('departure_airport', 'N/A')}")
                    st.write(f"**City:** {return_leg.get('departure_city', return_leg.get('origin', 'N/A'))}")
                    st.write(f"**Date:** {return_leg.get('departure_date', 'N/A')}")
                    st.write(f"**Time:** {return_leg.get('departure_time', 'N/A')}")

                with rarr:
                    st.write(
                        f"**Airport:** {return_leg.get('arrival_airport_name', return_leg.get('arrival_airport', 'N/A'))}"
                    )
                    st.write(f"**Airport code:** {return_leg.get('arrival_airport', 'N/A')}")
                    st.write(f"**City:** {return_leg.get('arrival_city', return_leg.get('destination', 'N/A'))}")
                    st.write(f"**Date:** {return_leg.get('arrival_date', 'N/A')}")
                    st.write(f"**Time:** {return_leg.get('arrival_time', 'N/A')}")

            # ----------------------------------------------
            # FLIGHT SUMMARY
            # ----------------------------------------------

            st.markdown(
                "#### 📊 Flight Summary"
            )

            d1, d2, d3, d4 = st.columns(4)

            with d1:
                try:
                    st.metric(
                        "💷 Price",
                        f"£{float(flight.get('total_price', 0) or 0):.2f}",
                    )
                except (TypeError, ValueError):
                    st.metric(
                        "💷 Price",
                        "N/A",
                    )

            with d2:
                duration = flight.get(
                    "duration_hours"
                )

                if duration not in (
                    None,
                    "",
                ):
                    try:
                        duration_text = (
                            f"{float(duration):.2f} h"
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        duration_text = str(
                            duration
                        )
                else:
                    duration_text = "N/A"

                st.metric(
                    "⏱️ Duration",
                    duration_text,
                )

            with d3:
                st.metric(
                    "🔁 Stops",
                    str(
                        flight.get(
                            "stops",
                            0,
                        )
                    ),
                )

            with d4:
                st.metric(
                    "✈️ Flight",
                    str(
                        flight_number
                    ),
                )

            # ----------------------------------------------
            # EXTRA FLIGHT DETAILS
            # ----------------------------------------------

            extra_details = []

            for key, label in [
                ("cabin_class", "Cabin class"),
                ("class", "Class"),
                ("fare_class", "Fare class"),
                ("booking_class", "Booking class"),
                ("baggage", "Baggage"),
                ("baggage_allowance", "Baggage allowance"),
                ("currency", "Currency"),
                ("booking_url", "Booking URL"),
                ("provider", "Provider"),
                ("source", "Source"),
            ]:

                value = flight.get(key)

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    extra_details.append(
                        (
                            label,
                            value,
                        )
                    )

            if extra_details:

                st.markdown(
                    "#### ℹ️ Additional Flight Information"
                )

                for label, value in extra_details:

                    if label == "Booking URL":

                        st.markdown(
                            f"🔗 **{label}:** "
                            f"[Book / View Flight]({value})"
                        )

                    else:

                        st.write(
                            f"**{label}:** {value}"
                        )

            # ----------------------------------------------
            # ALL FLIGHT SEGMENTS
            # ----------------------------------------------

            segments = flight.get(
                "segments"
            ) or []

            if segments:

                st.markdown(
                    "#### 🛫 Flight Segments"
                )

                for index, segment in enumerate(
                    segments,
                    1,
                ):

                    with st.expander(
                        f"Segment {index} — "
                        f"{segment.get('airline', airline)} "
                        f"{segment.get('flight_number', '')}",
                        expanded=True,
                    ):

                        s1, s2 = st.columns(2)

                        with s1:

                            st.markdown(
                                "**🛫 Departure**"
                            )

                            st.write(
                                f"Airport: "
                                f"{segment.get('departure_airport_name', segment.get('departure_airport', 'N/A'))}"
                            )

                            st.write(
                                f"Code: "
                                f"{segment.get('departure_airport', 'N/A')}"
                            )

                            st.write(
                                f"City: "
                                f"{segment.get('departure_city', flight.get('departure_city', flight.get('origin', 'N/A')))}"
                            )

                            st.write(
                                f"Date: "
                                f"{segment.get('departure_date_from_api', segment.get('departure_date', flight.get('departure_date', 'N/A')))}"
                            )

                            st.write(
                                f"Time: "
                                f"{segment.get('departure_time', 'N/A')}"
                            )

                        with s2:

                            st.markdown(
                                "**🛬 Arrival**"
                            )

                            st.write(
                                f"Airport: "
                                f"{segment.get('arrival_airport_name', segment.get('arrival_airport', 'N/A'))}"
                            )

                            st.write(
                                f"Code: "
                                f"{segment.get('arrival_airport', 'N/A')}"
                            )

                            st.write(
                                f"City: "
                                f"{segment.get('arrival_city', flight.get('arrival_city', flight.get('destination', 'N/A')))}"
                            )

                            st.write(
                                f"Date: "
                                f"{segment.get('arrival_date_from_api', segment.get('arrival_date', flight.get('arrival_date', 'N/A')))}"
                            )

                            st.write(
                                f"Time: "
                                f"{segment.get('arrival_time', 'N/A')}"
                            )

                        segment_duration = segment.get(
                            "duration_hours"
                        )

                        if segment_duration not in (
                            None,
                            "",
                        ):
                            st.write(
                                f"⏱️ **Segment duration:** "
                                f"{segment_duration} h"
                            )

            # ----------------------------------------------
            # RAW API FLIGHT DETAILS
            # ----------------------------------------------
            #
            # If the flight API returns additional fields,
            # preserve them rather than hiding them.
            # ----------------------------------------------

            ignored_keys = {
                "segments",
                "airline",
                "flight_number",
                "departure_airport",
                "departure_airport_name",
                "departure_city",
                "departure_date",
                "departure_time",
                "arrival_airport",
                "arrival_airport_name",
                "arrival_city",
                "arrival_date",
                "arrival_time",
                "origin",
                "destination",
                "total_price",
                "duration_hours",
                "stops",
            }

            additional_api_fields = {
                key: value
                for key, value in flight.items()
                if key not in ignored_keys
                and value not in (
                    None,
                    "",
                    [],
                    {},
                )
            }

            if additional_api_fields:

                with st.expander(
                    "🔎 View additional flight data"
                ):

                    for key, value in additional_api_fields.items():

                        st.write(
                            f"**{str(key).replace('_', ' ').title()}:** "
                            f"{value}"
                        )




            # ----------------------------------------------
            # RETURN FLIGHT — ROUND TRIP
            # ----------------------------------------------
            return_flight = flight.get("return_flight") or flight.get("return")
            if return_flight:
                st.markdown("#### 🛬 Return Flight")
                r1, r2 = st.columns(2)
                with r1:
                    st.write(f"**Airline:** {return_flight.get('airline', 'N/A')}")
                    st.write(f"**Flight number:** {return_flight.get('flight_number', 'N/A')}")
                    st.write(f"**Departure airport:** {return_flight.get('departure_airport_name', return_flight.get('departure_airport', 'N/A'))} ({return_flight.get('departure_airport', 'N/A')})")
                    st.write(f"**Departure city:** {return_flight.get('departure_city', 'N/A')}")
                    st.write(f"**Date:** {return_flight.get('departure_date', 'N/A')}")
                    st.write(f"**Time:** {return_flight.get('departure_time', 'N/A')}")
                with r2:
                    st.write(f"**Arrival airport:** {return_flight.get('arrival_airport_name', return_flight.get('arrival_airport', 'N/A'))} ({return_flight.get('arrival_airport', 'N/A')})")
                    st.write(f"**Arrival city:** {return_flight.get('arrival_city', 'N/A')}")
                    st.write(f"**Date:** {return_flight.get('arrival_date', 'N/A')}")
                    st.write(f"**Time:** {return_flight.get('arrival_time', 'N/A')}")
                    st.write(f"**Duration:** {return_flight.get('duration_hours', 'N/A')} h")
                    st.write(f"**Stops:** {return_flight.get('stops', 0)}")
                st.metric("💷 Round-Trip Fare", f"£{float(flight.get('total_price', 0) or 0):.2f}")
                return_segments = return_flight.get("segments") or []
                if return_segments:
                    with st.expander("🛬 Return Flight Segments", expanded=True):
                        for idx, seg in enumerate(return_segments, 1):
                            st.write(f"**Segment {idx} — {seg.get('airline', '')} {seg.get('flight_number', '')}**")
                            st.write(f"🛫 {seg.get('departure_airport_name', seg.get('departure_airport', 'N/A'))} → 🛬 {seg.get('arrival_airport_name', seg.get('arrival_airport', 'N/A'))}")
                            st.write(f"{seg.get('departure_time', 'N/A')} → {seg.get('arrival_time', 'N/A')} • {seg.get('duration_minutes', 'N/A')} min")

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

            st.subheader("📅 Daily Itinerary")

            # Clear visual labels for each itinerary activity.
            activity_meta = {
                "breakfast": ("☕", "BREAKFAST"),
                "attraction": ("🏛️", "ATTRACTION"),
                "museum": ("🖼️", "MUSEUM / GALLERY"),
                "gallery": ("🖼️", "MUSEUM / GALLERY"),
                "lunch": ("🍽️", "LUNCH"),
                "snack": ("☕", "CAFÉ / BREAK"),
                "cafe": ("☕", "CAFÉ / BREAK"),
                "dinner": ("🍽️", "DINNER"),
                "hotel_check_in": ("🏨", "HOTEL CHECK-IN"),
                "hotel_check_out": ("🏨", "HOTEL CHECK-OUT"),
                "flight": ("✈️", "FLIGHT"),
                "transfer": ("🚕", "TRANSFER"),
                "free_time": ("🕐", "FREE TIME"),
            }

            for day in itinerary:

                day_title = day.get("date", "Day")

                with st.container(border=True):
                    st.markdown(f"### 📅 {day_title}")

                    # Day summary
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric(
                            "Activity",
                            f"{float(day.get('activity_hours', 0) or 0):.1f}h",
                        )
                    with c2:
                        st.metric(
                            "Travel",
                            f"{float(day.get('travel_hours', 0) or 0):.1f}h",
                        )
                    with c3:
                        st.metric(
                            "Day Total",
                            f"{float(day.get('total_hours', 0) or 0):.1f}h",
                        )

                    weather_value = day.get("weather") or {}
                    if day.get("weather_note"):
                        st.info(f"🌤️ {day.get('weather_note')}")
                    elif isinstance(weather_value, dict) and weather_value:
                        summary = weather_value.get("condition") or weather_value.get("description") or weather_value.get("summary")
                        temp = weather_value.get("temperature", weather_value.get("temp"))
                        rain = weather_value.get("precipitation_probability", weather_value.get("rain_probability"))
                        bits = []
                        if temp is not None: bits.append(f"{temp}°C")
                        if summary: bits.append(str(summary))
                        if rain is not None: bits.append(f"{rain}% rain")
                        st.info("🌤️ **Daily Weather:** " + (" · ".join(bits) if bits else "Weather data available"))
                    else:
                        st.caption("🌤️ Daily Weather: Not available for this date")

                    activities = day.get("activities", [])

                    if not activities:
                        st.info("No activities scheduled for this day.")
                        continue

                    for activity in activities:

                        if not isinstance(activity, dict):
                            st.write(f"• {activity}")
                            continue

                        raw_type = str(
                            activity.get("activity_type", activity.get("category", "activity"))
                        ).strip().lower().replace(" ", "_").replace("/", "_")

                        # Some activity records use category names rather than activity_type.
                        if raw_type in {"restaurant", "meal", "food"}:
                            raw_type = "dinner"

                        icon, label = activity_meta.get(
                            raw_type,
                            ("📍", escape(str(activity.get("category", "ACTIVITY")).upper())),
                        )

                        name = escape(str(activity.get("name", "Activity")))
                        start = escape(str(activity.get("start_time", "")))
                        end = escape(str(activity.get("end_time", "")))
                        rating = activity.get("rating")
                        address = escape(str(activity.get("address", "")))
                        notes = escape(str(activity.get("notes", "")))
                        cost = activity.get("estimated_cost")

                        details = []
                        if rating:
                            try:
                                details.append(f"⭐ {float(rating):.1f}/5")
                            except (TypeError, ValueError):
                                details.append(f"⭐ {rating}/5")
                        if cost not in (None, "", 0, 0.0):
                            try:
                                details.append(f"£{float(cost):.2f}")
                            except (TypeError, ValueError):
                                pass

                        # Render each activity using native Streamlit components.
                        # This avoids raw HTML appearing as visible text and keeps the
                        # itinerary readable across Streamlit versions/themes.
                        with st.container(border=True):
                            st.markdown(
                                f"**{icon} {label}**"
                            )

                            st.markdown(
                                f"**{start} – {end}**"
                            )

                            st.markdown(
                                f"### {name}"
                            )

                            if details:
                                st.caption(" • ".join(details))

                            if address:
                                st.caption(f"📍 {address}")

                            if notes:
                                st.caption(notes)

                    # Daily estimated spend if provided by the itinerary engine.
                    day_spend = day.get("estimated_spend", day.get("food_spend", 0))
                    if day_spend not in (None, "", 0, 0.0):
                        try:
                            st.caption(f"💷 Estimated day spend: £{float(day_spend):.2f}")
                        except (TypeError, ValueError):
                            pass


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

                if isinstance(conflict, dict):
                    message = conflict.get(
                        "message",
                        "Planning conflict detected.",
                    )
                else:
                    message = str(conflict)

                st.warning(message)


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

        # ==================================================
        # SAVE DIALOG
        # ==================================================

        if st.session_state.show_save_dialog:

            @st.dialog("💾 Save Your Travel Plan")
            def save_plan_dialog():

                st.write(
                    "Your current TravelMind plan is ready to be saved."
                )

                st.info(
                    "Enter your email address and TravelMind "
                    "will send your complete final travel plan to you."
                )

                email = st.text_input(
                    "📧 Email address",
                    placeholder="example@email.com",
                    key="save_plan_email",
                )

                st.caption(
                    "Your email is used to deliver the complete "
                    "final TravelMind transcript."
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

                # --------------------------------------------------
                # CANCEL
                # --------------------------------------------------

                if cancel_save:
                    st.session_state.show_save_dialog = False
                    st.rerun()

                # --------------------------------------------------
                # CONFIRM & SAVE
                # --------------------------------------------------

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

                            # ==========================================
                            # CURRENT TRAVEL STATE
                            # ==========================================

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

                                return

                            if not itinerary_id:

                                st.error(
                                    "No generated itinerary was found. "
                                    "Please generate the plan again."
                                )

                                return

                            # ==========================================
                            # STEP 1 — SEND EMAIL
                            # ==========================================
                            #
                            # IMPORTANT:
                            # We send the email directly to the address
                            # entered by the user.
                            #
                            # We do NOT update users.email first.
                            #
                            # This prevents a Supabase update problem
                            # from blocking email delivery.
                            # ==========================================

                            with st.spinner(
                                "📧 Sending your TravelMind plan..."
                            ):

                                send_travel_plan_email(
                                    email_clean,
                                    current_state,
                                )

                            # ==========================================
                            # STEP 2 — EMAIL SUCCESSFUL
                            # ==========================================

                            # Only after the email was successfully sent
                            # do we mark the trip as saved.

                            saved_trip = mark_trip_as_saved(
                                trip_id
                            )

                            # Mark selected itinerary as final.
                            mark_itinerary_as_final(
                                itinerary_id
                            )

                            # Mark selected itinerary as saved.
                            mark_itinerary_as_saved(
                                itinerary_id
                            )

                            # ==========================================
                            # STEP 3 — OPTIONAL USER EMAIL UPDATE
                            # ==========================================
                            #
                            # This is intentionally OPTIONAL.
                            #
                            # If Supabase refuses the email update,
                            # the trip has already been emailed and saved,
                            # so we do not fail the entire operation.
                            # ==========================================

                            user_id = current_state.get(
                                "user_id"
                            )

                            if user_id:

                                try:

                                    from database.supabase_client import (
                                        supabase
                                    )

                                    (
                                        supabase
                                        .table("users")
                                        .update(
                                            {
                                                "email": email_clean
                                            }
                                        )
                                        .eq(
                                            "user_id",
                                            user_id
                                        )
                                        .execute()
                                    )

                                except Exception:
                                    # Do not undo a successful save
                                    # because of an optional profile update.
                                    pass

                            # ==========================================
                            # STEP 4 — UPDATE SESSION STATE
                            # ==========================================

                            st.session_state.saved_trip = (
                                saved_trip
                            )

                            st.session_state.show_save_dialog = (
                                False
                            )

                            st.success(
                                f"✅ Travel plan saved and emailed "
                                f"to {email_clean}!"
                            )

                            st.rerun()

                        except Exception as exc:

                            # The important part is that we now expose
                            # the REAL email/SMTP error instead of hiding
                            # it behind the Supabase user-email update.

                            st.error(
                                f"❌ Could not save travel plan: {exc}"
                            )

                            with st.expander(
                                "🔎 Technical email details"
                            ):

                                st.code(
                                    traceback.format_exc()
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
                f"{saved_trip.get('origin', 'Unknown')} → "
                f"{saved_trip.get('destination', 'Unknown')}"
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