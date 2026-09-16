<div align="center">

# ✈️ TravelMind

### Agentic AI Travel Planner

**Plan smarter. Travel better.**

TravelMind is an **Agentic AI travel planning application** that creates personalised, budget-aware and realistic travel itineraries using **Google Gemini, LangGraph, live travel APIs, deterministic Python validation and Supabase**.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=graphql&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SerpApi](https://img.shields.io/badge/SerpApi-000000?style=for-the-badge&logo=google&logoColor=white)](https://serpapi.com/)
[![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)](https://git-scm.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [How It Works](#-how-it-works)
- [Technology Stack](#️-technology-stack)
- [Architecture](#️-architecture)
- [User Input](#-user-input)
- [Deterministic Planning](#-deterministic-planning)
- [Budget & Conflict Detection](#-budget--conflict-detection)
- [Replanning](#-replanning)
- [Intelligent Daily Itinerary](#-intelligent-daily-itinerary)
- [Weather-Aware Planning](#️-weather-aware-planning)
- [Route Optimisation](#️-route-optimisation)
- [Opening Hours](#-opening-hours)
- [Candidate Plan Evaluation](#-candidate-plan-evaluation)
- [Explainable Planning](#-explainable-planning)
- [Agent Trace](#-agent-trace)
- [Data Quality](#-data-quality)
- [Persistence & Travel History](#-persistence--travel-history)
- [Email Delivery](#-email-delivery)
- [Why No RAG?](#-why-no-rag)
- [Project Structure](#-project-structure)
- [Installation](#️-installation)
- [Deployment](#️-deployment)
- [Testing](#-testing)
- [Security](#-security)
- [Future Improvements](#-future-improvements)
- [Core Engineering Philosophy](#-core-engineering-philosophy)

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🤖 | **Agentic Planning** | Multi-step AI workflow instead of a single LLM response |
| ✈️ | **Flight Planning** | Automatically finds suitable outbound & return flights |
| 🏨 | **Hotel Planning** | Finds and evaluates accommodation options |
| 📍 | **Attractions** | Discovers and schedules real attractions |
| 🍽️ | **Restaurants** | Food-preference-aware restaurant recommendations |
| 🌦️ | **Weather Aware** | Uses weather conditions when building the itinerary |
| 🗺️ | **Route Optimisation** | Groups activities to reduce unnecessary travel |
| 🕐 | **Opening Hours** | Avoids scheduling attractions when they are closed |
| 💷 | **Budget Control** | Deterministically checks trip costs against the budget |
| ⭐ | **Preference Priorities** | Handles Budget, Food, Location and Luxury priorities |
| ⚠️ | **Conflict Detection** | Identifies infeasible combinations of requirements |
| 🔄 | **Replanning** | Adjusts plans when constraints cannot be satisfied |
| 📊 | **Plan Evaluation** | Evaluates candidate plans before selecting a final plan |
| 🔍 | **Explainable Planning** | Provides concise explanations for planning decisions |
| 🧭 | **Agent Trace** | Shows high-level actions performed by the agent |
| 💾 | **Travel History** | Stores explicitly saved travel plans |
| 📧 | **Email Delivery** | Sends the final itinerary to the user's email |

---

## 🧠 How It Works

```text
👤 User
   │
   ▼
📝 Trip Requirements
   │
   ▼
🤖 LangGraph Agent
   │
   ├── ✈️ Flights
   ├── 🏨 Hotels
   ├── 📍 Attractions
   ├── 🍽️ Restaurants
   ├── 🌦️ Weather
   └── 🗺️ Routes
   │
   ▼
🧠 Candidate Plans
   │
   ▼
🧮 Deterministic Validation
   │
   ├── 💷 Budget
   ├── 🕐 Time
   ├── 📍 Location
   ├── 🗓️ Dates
   └── ⭐ Preferences
   │
   ▼
⚠️ Conflict?
   │
   ├── No ───────────────► 📅 Final Itinerary
   │
   └── Yes
          │
          ▼
      🔄 Replanning
          │
          └──────────────► 🧮 Re-evaluation
                                  │
                                  ▼
                           📅 Final Itinerary
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
                 💾 Supabase              📧 Email
```

---

## 🛠️ Technology Stack

### 🤖 AI & Agent Framework

| Technology | Role |
|---|---|
| ![Gemini](https://img.shields.io/badge/-Google_Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white) | LLM reasoning, preference interpretation and explanations |
| ![LangChain](https://img.shields.io/badge/-LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) | LLM and tool integration |
| ![LangGraph](https://img.shields.io/badge/-LangGraph-1C3C3C?style=flat-square&logo=graphql&logoColor=white) | Stateful agent workflow and orchestration |

### 💻 Application

| Technology | Role |
|---|---|
| ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | Core application, planning and validation logic |
| ![Streamlit](https://img.shields.io/badge/-Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white) | Interactive web application |

### 🌐 Live Data

| Technology | Role |
|---|---|
| ![SerpApi](https://img.shields.io/badge/-SerpApi-000000?style=flat-square&logo=google&logoColor=white) | Live travel search data |
| ✈️ Flight APIs | Flight availability and details |
| 🏨 Hotel APIs | Accommodation information |
| 📍 Attraction APIs | Places and activities |
| 🍽️ Restaurant Data | Food and restaurant information |
| 🌦️ Weather APIs | Weather conditions |
| 🗺️ Maps/Route APIs | Distance and travel-time information |

### 💾 Backend

| Technology | Role |
|---|---|
| ![Supabase](https://img.shields.io/badge/-Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white) | Backend platform |
| ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) | Persistent database |
| 📧 SMTP | Email delivery |

### 🧪 Development

| Technology | Role |
|---|---|
| ![Pytest](https://img.shields.io/badge/-Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) | Automated testing |
| 🔐 python-dotenv | Environment configuration |
| ![Git](https://img.shields.io/badge/-Git-F05032?style=flat-square&logo=git&logoColor=white) ![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat-square&logo=github&logoColor=white) | Version control and source management |

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────┐
│                 STREAMLIT UI                │
│                                             │
│  Name • Route • Dates • Travellers • Budget │
│  Food Preference • Preference Priorities   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                LANGGRAPH AGENT              │
│                                             │
│  State → Tools → Planning → Evaluation      │
│              → Replanning → Itinerary       │
└──────────────┬───────────────┬──────────────┘
               │               │
               ▼               ▼
        ┌─────────────┐  ┌───────────────┐
        │ Gemini LLM  │  │ External APIs │
        │ 🧠 Reasoning│  │ 🌐 Live Data  │
        └─────────────┘  └───────────────┘
               │               │
               └───────┬───────┘
                       ▼
              ┌──────────────────┐
              │ Planning Engine  │
              │ 🧮 Python Rules  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Evaluation     │
              └────────┬─────────┘
                       │
                 ┌─────┴─────┐
                 ▼           ▼
             Feasible      Conflict
                 │           │
                 │           ▼
                 │       🔄 Replan
                 │           │
                 └─────┬─────┘
                       ▼
              📅 Daily Itinerary
                       │
              ┌────────┴────────┐
              ▼                 ▼
        💾 Supabase          📧 Email
```

---

## 🎯 User Input

TravelMind keeps the user interface simple.

### 📝 Trip Details
- 👤 Name
- 📍 Origin
- 🌍 Destination
- 📅 Start Date
- 📅 End Date
- 👥 Travellers
- 💷 Budget

### 🍽️ Food Preference
- 🥗 Vegetarian
- 🍗 Non-Vegetarian
- 🌱 Vegan
- 🍽️ No Food Preference

### ⭐ Preference Priorities

Users can prioritise:
- 💷 Budget
- 🍽️ Food
- 📍 Central Location
- ⭐ Luxury

Each can be assigned: **HIGH**, **MEDIUM**, or **LOW**.

### ✈️ Automatic Flight Planning

Users do not manually choose Round Trip vs. One Way — TravelMind automatically searches for suitable flight combinations.

Flight results can include:
- Airline
- Flight number
- Departure/arrival airports
- Dates and times
- Duration
- Stops
- Cabin
- Fare
- Baggage
- Price
- Currency
- Booking information
- Individual flight segments

For round trips, the system uses the relevant outbound flight information to retrieve corresponding return-flight options.

---

## 🧮 Deterministic Planning

One of the key architectural principles is:

> **The LLM reasons; Python validates.**

The LLM is used for:
- 🧠 Understanding
- 🧠 Reasoning
- 🧠 Trade-offs
- 🧠 Explanations

Python handles:
- 🧮 Budget calculations
- 🕐 Time constraints
- 📅 Date validation
- 🕐 Opening hours
- 🔄 Replanning limits
- 📍 Schedule feasibility

For example:

```python
total_cost <= budget
```

This prevents critical decisions from depending entirely on probabilistic LLM output.

---

## 💷 Budget & Conflict Detection

TravelMind checks whether the selected trip can satisfy the user's budget and preferences.

**Example:**
```
Budget: £800
Central Location: HIGH
Luxury: HIGH
```

If the available options cannot satisfy the combination, TravelMind can identify the conflict and suggest alternatives based on available candidate costs.

If no feasible option exists:

> ❌ No feasible trip was found within the current budget.

---

## 🔄 Replanning

TravelMind can re-evaluate a trip when constraints are violated.

```text
Initial Plan
     ↓
Evaluation
     ↓
⚠️ Conflict
     ↓
Replanning
     ↓
New Candidate
     ↓
Evaluation
     ↓
Final Plan
```

The system uses bounded replanning iterations to avoid endless loops.

> **Current UI:** For now, if you want to replan, reload the website and enter the updated requirements again.

---

## 📅 Intelligent Daily Itinerary

TravelMind converts selected travel components into a realistic day-by-day schedule.

**Example:**
```
09:00  🍳 Breakfast
10:00  📍 Attraction
12:30  🍽️ Lunch
14:00  📍 Attraction
16:30  ☕ Café
19:30  🍽️ Dinner
```

The itinerary considers:
- ✈️ Flight times
- 🏨 Hotel check-in/out
- 📍 Location
- 🗺️ Travel time
- 🕐 Opening hours
- 🌦️ Weather
- ⭐ Preferences
- ⏱️ Daily activity limits

---

## 🌦️ Weather-Aware Planning

Weather information can influence the itinerary.

```text
☀️ Suitable Weather → Outdoor Activities

🌧️ Poor Weather → Activity Affected → Rearrange Itinerary → Indoor Alternative
```

---

## 🗺️ Route Optimisation

TravelMind attempts to group nearby activities to reduce unnecessary travel.

```text
Attraction A → Nearby Attraction B → Lunch → Nearby Attraction C
```

...rather than repeatedly crossing the city.

---

## 🕐 Opening Hours

The itinerary engine considers attraction opening hours.

```text
Attraction Closed → Do Not Schedule → Consider Alternative
```

This helps prevent unrealistic schedules.

---

## 📊 Candidate Plan Evaluation

TravelMind can evaluate different combinations of:
- ✈️ Flights
- 🏨 Hotels
- 📍 Attractions
- 🍽️ Restaurants
- 💷 Costs
- 📅 Daily Schedules

Candidate plans can be evaluated against:
- Budget
- Preferences
- Time feasibility
- Route efficiency
- Data completeness
- Constraint violations

---

## 🔍 Explainable Planning

TravelMind provides concise explanations for important decisions.

**Example — Why was this hotel selected?**
> It fits the available budget, provides a suitable location and matches the user's location preference.

The system provides high-level explanations without exposing private chain-of-thought.

---

## 🧭 Agent Trace

The application can show a high-level view of what the agent performed:

- ✅ Requirements understood
- ✅ Flights retrieved
- ✅ Hotels retrieved
- ✅ Attractions found
- ✅ Restaurants found
- ✅ Weather checked
- ✅ Routes evaluated
- ✅ Candidate plan generated
- ✅ Constraints evaluated
- ✅ Replanning performed
- ✅ Final itinerary created

---

## 📊 Data Quality

TravelMind can communicate the quality/status of different data sources:

| Source | Status |
|---|---|
| ✈️ Flights | 🟢 Good |
| 🏨 Hotels | 🟢 Good |
| 📍 Attractions | 🟢 Good |
| 🍽️ Restaurants | 🟡 Limited |
| 🌦️ Weather | 🟢 Good |
| 🗺️ Routes | 🟢 Good |

This helps users understand when external information may be limited.

---

## 💾 Persistence & Travel History

Supabase/PostgreSQL stores the planning lifecycle.

Main tables include:
- `users`
- `trips`
- `planning_runs`
- `queries`
- `tool_results`
- `itinerary_versions`
- `evaluations`
- `agent_trace`

TravelMind distinguishes between:

```text
Planning Activity → Planning Session → Final User Decision → Save Plan → Travel History
```

Only explicitly saved plans become Travel History entries.

---

## 📧 Email Delivery

When the user selects **Save Plan**, TravelMind can send the final itinerary by email.

The email can contain:
- Trip details
- Flights
- Hotel
- Attractions
- Restaurants
- Daily itinerary
- Explanations
- Warnings
- Conflicts

---

## 🚫 Why No RAG?

TravelMind does **not** use Retrieval-Augmented Generation.

The application depends on dynamic information such as:
- ✈️ Flight availability
- 💷 Flight prices
- 🏨 Hotels
- 🍽️ Restaurants
- 🌦️ Weather
- 🗺️ Routes
- 🕐 Opening hours

Therefore, TravelMind uses **live APIs/tools** rather than relying on a static vector database.

```text
User → Agent → Live APIs → Planning → Deterministic Validation → Final Itinerary
```

---

## 📁 Project Structure

```text
TravelMind/
│
├── app.py
│
├── agent/
│   ├── graph.py
│   ├── nodes.py
│   ├── state.py
│   ├── prompts.py
│   └── llm.py
│
├── planning/
│   ├── planner.py
│   ├── daily_itinerary.py
│   └── replanner.py
│
├── tools/
│   ├── flights.py
│   ├── hotels.py
│   ├── attractions.py
│   ├── restaurants.py
│   ├── weather.py
│   └── maps.py
│
├── database/
│   ├── trips.py
│   ├── planning_runs.py
│   ├── queries.py
│   ├── tool_results.py
│   ├── itinerary_versions.py
│   ├── evaluations.py
│   └── agent_trace.py
│
├── ui/
│   └── forms.py
│
├── validation/
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Shaiksadaf17/Travelmind.git
cd Travelmind
```

### 2. Create a virtual environment

```bash
python -m venv travelmind_env
```

### 3. Activate it

**Windows:**
```powershell
.\travelmind_env\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source travelmind_env/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
SERPAPI_API_KEY=your_key
GOOGLE_API_KEY=your_key
GEMINI_API_KEY=your_key

SUPABASE_URL=your_url
SUPABASE_KEY=your_key

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email
SMTP_USE_SSL=false
```

> ⚠️ **Never commit `.env` or API keys to GitHub.**

### ▶️ Run locally

```bash
streamlit run app.py
```

The application will open in your browser.

---

## ☁️ Deployment

TravelMind can be deployed using **Streamlit Community Cloud**.

```text
GitHub → Streamlit Cloud → Repository → main branch → app.py → Configure Secrets → Deploy
```

API keys and credentials should be stored securely using **Streamlit Secrets**.

---

## 🧪 Testing

Run the test suite with:

```bash
pytest
```

Important test areas include:
- Budget validation
- Date validation
- Constraint detection
- Preference handling
- Replanning
- Itinerary generation
- Opening hours
- Flight selection
- Restaurant filtering
- Data quality
- Database operations

---

## 🔐 Security

Never expose or commit:
- `.env`
- `.streamlit/secrets.toml`
- API Keys
- Database Keys
- SMTP Passwords

Use environment variables locally and encrypted secrets in deployment environments.

---

## 🚀 Future Improvements

- 🗺️ Interactive maps
- 🔄 In-app replanning without reload
- 📱 Improved mobile UI
- 🔔 Travel alerts
- ✈️ Flight price monitoring
- 🏨 Hotel price monitoring
- 📅 Calendar integration
- 💳 Advanced cost tracking
- 🌍 More destinations
- 🌦️ Advanced weather optimisation
- 📊 Expanded agent evaluation
- 🔎 Improved observability
- ⚡ Parallel tool execution
- 🧪 Expanded automated testing
- 🔐 User authentication

---

## 🧠 Core Engineering Philosophy

| Component | Role |
|---|---|
| 🧠 **Gemini** | Reasoning & Explanation |
| 🌐 **APIs** | Live Real-World Data |
| 🐍 **Python** | Deterministic Validation |
| 🔄 **LangGraph** | Agent Orchestration |
| ⚡ **Supabase** | Persistence |
| 📊 **Evaluation** | Reliability & Improvement |

TravelMind combines AI reasoning with deterministic software engineering to build a more structured, constraint-aware travel planning experience.

---

<div align="center">

### 👨‍💻 Author
**Shaik Sadaf Patel**

### TravelMind
**✈️ Plan Smarter. Travel Better.**

</div>
