# Dublin Bikes Project

## Title Page
* **Product**: Dublin Bikes Project
* **Version**: 1.0.0
* **Date**: May 2026
* **Course**: COMP30830 Software Engineering, University College Dublin
* **Team**: Group 13

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Features](#2-features)
- [3. Architecture Overview](#3-architecture-overview)
- [4. Getting Started](#4-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation (Docker - Recommended)](#installation-docker---recommended)
  - [Installation (Local)](#installation-local)
  - [Configuration](#configuration)
- [5. Deployment (Free Tier)](#5-deployment-free-tier)
  - [5.1 Database — Aiven for MySQL](#51-database--aiven-for-mysql)
  - [5.2 Web app — Vercel](#52-web-app--vercel)
  - [5.3 Data collection — GitHub Actions](#53-data-collection--github-actions)
- [6. Usage](#6-usage)
- [7. Repository Structure](#7-repository-structure)
- [8. Development Guidelines](#8-development-guidelines)

---

## 1. Introduction
The **Dublin Bikes Project** is a web application for Dublin's public bike-sharing scheme, developed
by a student group as part of a software engineering module in Computer Science at University College
Dublin.

It shows live availability at every station and predicts how many bikes and empty stands a station
will have over the next 24 hours, by combining a trained neural network with current weather data.

## 2. Features

### **Core Functionality**
- **Real-Time Interactive Map**: Displays all bike stations with their current availability (bikes and empty stands).
- **Machine Learning Predictions**: Predicts future station availability based on historical data, time features, and live weather conditions fetched via Open-Meteo API.
- **Smart Weather Integration**: Provides nearby weather information with an intelligent in-memory caching mechanism to ensure high availability and responsiveness.
- **User Accounts & Authentication**: Secure signup, login, and session management.
- **Favorites System**: Logged-in users can save and quickly access their favorite stations.
- **Geolocation**: Automatically retrieves device location to center the map and find the closest stations.

## 3. Architecture Overview

| Layer | Service |
|---|---|
| Access / TLS | Vercel edge network — TLS and CDN included |
| Application | Flask on the Vercel Python runtime (`main.py`) |
| Database | Aiven for MySQL 8, over a TLS-only connection |
| Data collection | GitHub Actions, every 30 minutes |

**Application layer.** Business logic is organised with Flask Blueprints — `main.py` (map, stations,
weather), `auth.py` (accounts, sessions, favourites) and `machine_learning.py` (predictions). Sessions
are cookie-based and signed with `SECRET_KEY`.

**Prediction layer.** Two trained models — a standardiser followed by a multi-layer perceptron —
blend time features with live Open-Meteo weather to forecast available bikes and empty stands, either
for a single moment or across the next 24 hours.

**Data persistence.** MySQL stores station metadata, historical availability and weather samples,
hashed user credentials, and the user↔station favourites relation.

> **Note on dependencies:** the models are *trained* with scikit-learn but *served* with NumPy alone.
> `machine_learning/export_models.py` converts each trained `.joblib` pipeline into a small `.npz` of
> weights, which `app/mlp.py` evaluates directly — a standardisation followed by a few matrix
> multiplications. That keeps scikit-learn, SciPy and pandas out of the deployment, shrinking it from
> 229 MB to 84 MB (the hosting limit is 250 MB) and removing seconds from every cold start.
> Predictions are bit-identical to the original pipeline; `export_models.py` verifies that on every
> export. Re-run it after retraining a model.

## 4. Getting Started

### **Prerequisites**
- **Docker** and **Docker Compose** (Highly Recommended for local deployment)
- Python 3.12 and Conda (For local development only)
- API Keys: OpenWeather, Google Maps, JCDecaux

### **Installation (Docker - Recommended)**
1. Clone the repository:
   ```bash
   git clone https://github.com/alisonmeng/dublin-bikes.git
   cd dublin-bikes
   ```

2. Create a `.env` file in the project root directory (see [Configuration](#configuration)).

3. Build and launch the application using Docker Compose:
   - **For local testing/development**:
     ```bash
     docker-compose -f docker-compose.local.yml up --build -d
     ```
   - **For production**:
     ```bash
     docker-compose up --build -d
     ```

4. Create the tables and seed the station list (first run only):
   ```bash
   python database/init_db.py
   python database/bulk_bike_insert.py
   ```

### **Installation (Local)**
1. Set up your Conda environment:
   ```bash
   conda activate <your-conda-env>
   conda env update --file environment.yml --prune
   ```
2. Create your `.env` file.
3. Ensure you have a MySQL instance running that matches your `.env` configuration, then run
   `python database/init_db.py` followed by `python database/bulk_bike_insert.py`.

### **Configuration**
Create a `.env` file in the root directory with the following variables:

```env
# Flask
SECRET_KEY="a_long_random_string_used_to_sign_session_cookies"

# Database
DB_USER="your_db_username"
DB_PASSWORD="your_db_password"
DB_PORT="3306"
DB_NAME="your_db_name"
DB_URI="db"

# APIs
BIKE_KEY="your_jcdecaux_key"
WEATHER_KEY="your_open_weather_key"
MAP_KEY="your_google_maps_browser_key"
MAP_ID="your_google_maps_map_id"
```

| Variable | Required | Used by | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | Flask sessions | Any long random string. **Must** be set in production — sessions are the only authentication mechanism, so a guessable key means forgeable logins. |
| `DB_USER` / `DB_PASSWORD` | yes | SQLAlchemy | Aiven issues `avnadmin` and a generated password. |
| `DB_URI` | yes | SQLAlchemy | Database **host**. `db` under Docker Compose; the `…aivencloud.com` hostname when hosted. |
| `DB_PORT` | yes | SQLAlchemy | `3306` locally; Aiven assigns a non-standard port. |
| `DB_NAME` | yes | SQLAlchemy | `defaultdb` on Aiven. |
| `DATABASE_URL` | no | SQLAlchemy | Full DSN. When set, it overrides the five `DB_*` variables above. |
| `DB_SSL_CA` | hosted only | SQLAlchemy | Path to the CA certificate, e.g. `certs/aiven-ca.pem`. Enables TLS with certificate verification; Aiven refuses plaintext connections. |
| `BIKE_KEY` | yes | JCDecaux API | Live station availability. |
| `WEATHER_KEY` | yes | OpenWeather API | Current weather. The *prediction* routes use Open-Meteo, which needs no key. |
| `MAP_KEY` | yes | Google Maps JS | Sent to the browser, so it is public by design — restrict it by HTTP referrer in Google Cloud Console. |
| `MAP_ID` | yes | Google Maps JS | Map style ID; required for Advanced Markers. |

## 5. Deployment (Free Tier)

The hosted setup uses three services, each on a permanently free plan:

| Piece | Service | Free tier |
|---|---|---|
| Web app | Vercel (Hobby) | Never sleeps, HTTPS and custom domains included |
| Database | Aiven for MySQL (Free plan) | MySQL 8, 1 CPU / 5 GB storage, single node, no backups |
| Data collection | GitHub Actions | Unlimited minutes on a public repository |

### 5.1 Database — Aiven for MySQL

1. Create a free MySQL service at [console.aiven.io](https://console.aiven.io).
2. From the service overview, copy the host, port, user, password and database name, and download
   the **CA certificate** into `certs/aiven-ca.pem`. That certificate is public — it is safe to commit,
   and it is what lets the client verify it is really talking to your database.
3. Put those values in your local `.env`, then create the schema and seed the stations:
   ```bash
   python database/init_db.py           # station, availability, current, users, user_favorites
   python database/bulk_bike_insert.py  # seeds `station` from JCDecaux
   ```

Only the `station` table is required for the site to function — the map reads live availability
directly from JCDecaux. The `availability` and `current` tables accumulate history for retraining.

### 5.2 Web app — Vercel

`main.py` at the repository root is the Vercel entrypoint; `vercel.json` sets the function's memory
and timeout and excludes training data and test files from the bundle.

1. Import the GitHub repository at [vercel.com/new](https://vercel.com/new).
2. Add every variable from the [Configuration](#configuration) table (plus `DB_SSL_CA`) under
   **Settings → Environment Variables**.
3. Deploy. Subsequent pushes to `main` deploy automatically.

Or from the CLI:
```bash
npx vercel link
npx vercel env add SECRET_KEY production
npx vercel --prod
```

### 5.3 Data collection — GitHub Actions

`.github/workflows/scrape.yml` runs `database/scrape_to_db.py` every 30 minutes: it upserts the station
list, appends a row per station to `availability`, and appends the current OpenWeather reading to
`current`. Both writes use `ON DUPLICATE KEY UPDATE`, so re-runs and overlapping schedules are
harmless.

Add `SECRET_KEY`, `DB_*`, `BIKE_KEY` and `WEATHER_KEY` under **Settings → Secrets and variables →
Actions**, then trigger a first run manually from the Actions tab (`Run workflow`) to confirm the
connection works.

Two caveats: GitHub disables scheduled workflows after 60 days without repository activity, and cron
runs can be delayed when the platform is busy. Neither affects the live site — only how much history
accumulates.

## 6. Usage
- **Hosted**: open the Vercel deployment URL.
- **Docker**: navigate to `http://localhost`. Nginx will serve the application.
- **Local**: run the application from the root folder:
  ```bash
  python run.py
  ```
  Then access the app at `http://127.0.0.1:5000`.

Key routes:

| Route | Purpose |
|---|---|
| `/` | Interactive map |
| `/api/bikes` | Live availability, proxied from JCDecaux (5 min cache) |
| `/api/weather` | Current Dublin weather (10 min cache) |
| `/db/stations` | Station metadata from the database |
| `/predict/bike/24h?station_id=&date=&time=` | 24-hour available-bike forecast |
| `/predict/stand/24h?station_id=&date=&time=` | 24-hour empty-stand forecast |
| `/auth/login`, `/auth/register`, `/account` | Accounts and favourites |

## 7. Repository Structure

```text
dublin-bikes/
├── app/                    # Core application logic
│   ├── __init__.py         # Flask app factory setup
│   ├── connection.py       # SQLAlchemy database connection (TLS + serverless aware)
│   ├── mlp.py              # NumPy-only inference for the trained models
│   ├── routes/             # Backend API logic & Blueprints
│   │   ├── main.py         # Core map and business logic
│   │   ├── auth.py         # User lifecycle and favorites logic
│   │   └── machine_learning.py # ML Prediction service integration
│   ├── static/             # Frontend assets (CSS, JS, Images)
│   └── templates/          # Frontend templates (Jinja2)
├── certs/                  # Public CA certificate for the managed database
├── database/               # SQL scripts, schema init, and the scraper
├── machine_learning/       # Training notebook, datasets, trained models
│   ├── export_models.py    # Converts trained .joblib pipelines to served .npz
│   └── output_model/       # .joblib (trained) and .npz (served) models
├── tests/                  # Backend unit, integration and non-functional tests
├── nginx/                  # Nginx configuration & proxy settings (Docker only)
├── .github/workflows/      # Scheduled data collection
├── docker-compose.yml      # Main Docker Compose configuration
├── docker-compose.local.yml# Local testing Docker Compose config
├── Dockerfile              # Containerization definition for Flask web app
├── vercel.json             # Vercel function configuration
├── main.py                 # Entry point for Vercel
├── environment.yml         # Conda environment dependencies
├── requirements.txt        # Runtime dependencies (app + Vercel)
├── requirements-dev.txt    # Training / notebook / test-only dependencies
└── run.py                  # Entry point for local execution
```

## 8. Development Guidelines

**Coding Standards:**
A summary of the coding best practices:

**Fundamental Design Principles**
*   **Keep functions short and files numerous:** Avoid creating "god classes" or excessively long files. Break logic down into many short functions and modular files.
*   **Maximize Cohesion:** Design modules and functions to focus on a single, well-defined task or responsibility, making them easier to test and maintain.
*   **Ensure Decoupling:** Minimize interdependencies between modules so the system remains flexible and easier to change.
*   **Practice Information Hiding:** Do not use global variables whenever possible. Restrict access to data and components strictly through well-defined interfaces.
*   **Separation of Concerns:** Keep your architecture clean by strictly separating logic (e.g., Python code) from presentation layers (e.g., HTML using Jinja2 templates).

**Naming Conventions and Coding Styles**
*   **Use descriptive, explicit naming:** Choose meaningful names that reflect the variable or function's purpose. Avoid single-letter variables (except for basic loop counters). Function names should typically start with a verb (e.g., `calculate_total`).
*   **Python (PEP 8) styling:** Use `snake_case` for variables and functions, `PascalCase` for class definitions, and `UPPER_SNAKE_CASE` for constants.
*   **JavaScript styling:** Use `camelCase` for variables and functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants, and `kebab-case` for filenames.
*   **Make variable types explicit:** In Python, define the expected input and return types using type hinting (e.g., `def add(a: int) -> int:`) to improve code clarity and catch errors early with static tools like mypy.

**Documentation and Commenting**
*   **Explain the "why", not just the "what":** Comments should clarify the intent of the code, any unusual behavior, edge-case handling, and architectural decisions.
*   **Use standard documentation blocks:** Comment all functions, classes, and modules detailing their arguments, return values, and exceptions raised. Use PEP 257 standards for Python and JSDoc for JavaScript.
*   **Flag incomplete code:** Mark unfinished segments clearly using standard markers like `TODO`.

**Version Control (Git) Practices**
*   **Commit early and often:** Work in small chunks and commit frequently to avoid massive merge conflicts and effectively track changes.
*   **Make single-purpose commits:** Do not bundle multiple unrelated features or bug fixes into a single commit.
*   **Use branches properly:** Never edit production code directly. Use feature branches to isolate environments for every change, no matter how small, and merge them via Pull Requests.
*   **Exclude generated files:** Always use a `.gitignore` file to ensure you do not commit system-generated, temporary, or easily re-generated files to your repository.

**Error Handling and Logging**
*   **Handle errors gracefully:** Employ `try-catch` blocks in JS and route aborts (e.g., `abort(404)`) in Python to deal with unexpected inputs or failures.

**Web Development & Architecture**
*   **Protect your API and Secret Keys:** **Never** commit API keys or secret keys to code repositories. Store them as environment variables and restrict their usage via IP addresses or specific websites.
*   **Use Flask Contexts securely:** Utilize Flask's `g` variable to temporarily store data (like database connections) within a single request, and `session` dictionaries for retaining data across multiple requests.
