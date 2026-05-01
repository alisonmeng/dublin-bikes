# Dublin Bikes Project - Group 13 of COMP30830

## Title Page
* **Product**: Dublin Bikes Project
* **Version**: 1.0.0
* **Date**: May 2026

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Features](#2-features)
- [3. Architecture Overview](#3-architecture-overview)
- [4. Getting Started](#4-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation (Docker - Recommended)](#installation-docker---recommended)
  - [Installation (Local)](#installation-local)
  - [Configuration](#configuration)
- [5. Usage](#5-usage)
- [6. Repository Structure](#6-repository-structure)
- [7. Development Guidelines](#7-development-guidelines)

---

## 1. Introduction
Welcome to the **Dublin Bikes Project**, developed by Group 13 for COMP30830. 
This is a modern web application designed to provide users with real-time availability and machine learning-powered predictions for Dublin Bikes stations. The system is built upon a scalable microservices architecture using Flask, Nginx, MySQL, and Docker.

## 2. Features

### **Core Functionality**
- **Real-Time Interactive Map**: Displays all bike stations with their current availability (bikes and empty stands).
- **Machine Learning Predictions**: Predicts future station availability based on historical data, time features, and live weather conditions fetched via Open-Meteo API.
- **Smart Weather Integration**: Provides nearby weather information with an intelligent in-memory caching mechanism to ensure high availability and responsiveness.
- **User Accounts & Authentication**: Secure signup, login, and session management.
- **Favorites System**: Logged-in users can save and quickly access their favorite stations.
- **Geolocation**: Automatically retrieves device location to center the map and find the closest stations.

## 3. Architecture Overview
The system adopts a decoupled, containerized architecture:

1. **Access Layer (Nginx)**: Acts as a reverse proxy, handling HTTPS requests, serving static assets, and routing API calls to the backend.
2. **Application Layer (Flask)**: Implements business logic using Blueprints (`main.py`, `auth.py`, `machine_learning.py`). Handles user authentication (session-based) and interactions.
3. **Prediction Layer**: Employs a pre-trained Multi-Layer Perceptron (MLP) model (`.joblib`) for real-time predictions, blending time variables with real-time weather data.
4. **Data Persistence (MySQL)**: Securely stores station data, hashed user credentials, and favorite relationships.

## 4. Getting Started

### **Prerequisites**
- **Docker** and **Docker Compose** (Highly Recommended for deployment)
- Python and Conda (For local development only)
- API Keys: Open-Weather-API, Google Maps, JCDecaux

### **Installation (Docker - Recommended)**
1. Clone the repository:
   ```bash
   git clone https://github.com/kksskkkksskkkks/COMP30830_Project/tree/main
   cd COMP30830_Project
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

### **Installation (Local)**
1. Set up your Conda environment:
   ```bash
   conda activate <your-conda-env>
   conda env update --file environment.yml --prune
   ```
2. Create your `.env` file.
3. Ensure you have a local MySQL instance running that matches your `.env` configuration.

### **Configuration**
Create a `.env` file in the root directory with the following variables:

```env
# Database
DB_USER="your_db_username"
DB_PASSWORD="your_db_password"
DB_PORT="3306"
DB_NAME="your_db_name"
DB_URI="db"

# APIs
BIKE_KEY="your_jcdecaux_key"
NAME="dublin
MAP_KEY="your_google_maps_key"
STATIONS_URI="https://api.jcdecaux.com/vls/v1/stations"
WEATHER_KEY="your_open_weather_key"
WEATHER_URI="https://api.openweathermap.org/data/2.5/weather"
CITY_NAME="Dublin"
```

## 5. Usage
- **Docker**: Open your web browser and navigate to `http://localhost`. Nginx will serve the application.
- **Local**: Run the application from the root folder:
  ```bash
  python run.py
  ```
  Then access the app at `http://127.0.0.1:5000`.

## 6. Repository Structure

```text
COMP30830_Project/
├── app/                    # Core application logic
│   ├── __init__.py         # Flask app factory setup
│   ├── connection.py       # SQLAlchemy database connection
│   ├── routes/             # Backend API logic & Blueprints
│   │   ├── main.py         # Core map and business logic
│   │   ├── auth.py         # User lifecycle and favorites logic
│   │   └── machine_learning.py # ML Prediction service integration
│   ├── static/             # Frontend assets (CSS, JS, Images)
│   └── templates/          # Frontend templates (Jinja2)
├── database/               # SQL scripts & database init configs
├── machine_learning/       # Model training scripts, raw datasets
├── tests/                  # Backend unit and integration tests
├── nginx/                  # Nginx configuration & proxy settings
├── docker-compose.yml      # Main Docker Compose configuration
├── docker-compose.local.yml# Local testing Docker Compose config
├── Dockerfile              # Containerization definition for Flask web app
├── environment.yml         # Conda environment dependencies
├── requirements.txt        # Docker environment dependencies
└── run.py                  # Entry point for local execution
```

## 7. Development Guidelines

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
