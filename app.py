from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "hour.csv"


def load_data():
    """Load and clean the hourly bike-sharing dataset."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {CSV_PATH}. "
            "Place hour.csv beside app.py."
        )

    data = pd.read_csv(CSV_PATH)

    required_columns = {
        "hr", "weathersit", "season", "holiday", "cnt"
    }
    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"hour.csv is missing these columns: {', '.join(sorted(missing))}"
        )

    for column in required_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=list(required_columns))
    return data


DATA = load_data()


def average_demand(filters):
    """Estimate demand using matching historical rows, with fallbacks."""
    matches = DATA.copy()

    for column, value in filters.items():
        matches = matches[matches[column] == value]

    if matches.empty and "weathersit" in filters:
        # If there is no exact weather match, try the same hour and season.
        fallback = DATA[
            (DATA["hr"] == filters["hr"])
            & (DATA["season"] == filters["season"])
        ]
        matches = fallback

    if matches.empty:
        # Last fallback: use all historical records for that hour.
        matches = DATA[DATA["hr"] == filters["hr"]]

    if matches.empty:
        matches = DATA

    return int(round(matches["cnt"].mean()))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/predict", methods=["POST"])
def predict():
    """Accept prediction conditions and return an estimated rental count."""
    payload = request.get_json(silent=True) or {}

    try:
        hour = int(payload["hour"])
        weather = int(payload["weather"])
        season = int(payload["season"])
        holiday = int(payload["holiday"])
        available_bikes = int(payload["availableBikes"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Please provide valid prediction inputs."}), 400

    if not 0 <= hour <= 23:
        return jsonify({"error": "Hour must be between 0 and 23."}), 400

    if weather not in (1, 2, 3, 4):
        return jsonify({"error": "Weather must be between 1 and 4."}), 400

    if season not in (1, 2, 3, 4):
        return jsonify({"error": "Season must be between 1 and 4."}), 400

    if holiday not in (0, 1) or available_bikes < 0:
        return jsonify({"error": "Holiday must be 0 or 1; available bikes cannot be negative."}), 400

    filters = {
        "hr": hour,
        "weathersit": weather,
        "season": season,
        "holiday": holiday,
    }

    estimated_demand = average_demand(filters)
    difference = estimated_demand - available_bikes

    if difference > 0:
        recommendation = f"Consider adding or moving {difference} bicycles to meet estimated demand."
    elif difference < 0:
        recommendation = f"Estimated supply is higher than demand by {abs(difference)} bicycles."
    else:
        recommendation = "Available bicycles match the estimated demand."

    return jsonify({
        "estimatedDemand": estimated_demand,
        "availableBikes": available_bikes,
        "difference": difference,
        "recommendation": recommendation,
        "method": "Historical average from hour.csv; not a trained ML model."
    })


@app.route("/api/hourly-demand")
def hourly_demand():
    """Return average rentals for each hour, optionally filtered by weather."""
    weather = request.args.get("weather", "all")

    filtered = DATA.copy()

    if weather != "all":
        try:
            weather_value = int(weather)
        except ValueError:
            return jsonify({"error": "Weather must be 'all' or a number from 1 to 4."}), 400

        if weather_value not in (1, 2, 3, 4):
            return jsonify({"error": "Weather must be 'all' or a number from 1 to 4."}), 400

        filtered = filtered[filtered["weathersit"] == weather_value]

    if filtered.empty:
        return jsonify({"hours": [], "averageRentals": []})

    grouped = filtered.groupby("hr")["cnt"].mean().sort_index()

    return jsonify({
        "hours": [int(hour) for hour in grouped.index],
        "averageRentals": [round(float(value), 2) for value in grouped.values]
    })


if __name__ == "__main__":
    app.run(debug=True)