from pathlib import Path
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "hour.csv"

def load_data():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")
    data = pd.read_csv(CSV_PATH)
    required = {"hr", "weathersit", "season", "holiday", "cnt"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    return data.dropna(subset=list(required))

DATA = load_data()

def average_demand(filters):
    filtered = DATA
    for key, value in filters.items():
        filtered = filtered[filtered[key] == value]
        if len(filtered) < 20:
            break
    if len(filtered) == 0:
        return int(DATA["cnt"].mean())
    return int(filtered["cnt"].mean())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        body = request.get_json(force=True)
        hour = int(body.get("hour", 8))
        weather = int(body.get("weather", 1))
        season = int(body.get("season", 1))
        holiday = int(body.get("holiday", 0))
        available = int(body.get("availableBikes", 0))

        estimated = average_demand({
            "hr": hour,
            "weathersit": weather,
            "season": season,
            "holiday": holiday
        })

        diff = estimated - available

        # FIXED LOGIC - Add / Remove
        if diff > 0:
            recommendation = f"Add {diff} bicycles"
        elif diff < 0:
            recommendation = f"Remove {abs(diff)} bicycles"
        else:
            recommendation = "No change needed"

        return jsonify({
            "estimatedDemand": estimated,
            "recommendation": recommendation,
            "method": "Average of matching historic records"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/hourly-demand")
def hourly_demand():
    try:
        weather = request.args.get("weather", "all")
        data = DATA
        if weather != "all":
            data = data[data["weathersit"] == int(weather)]
        grouped = data.groupby("hr")["cnt"].mean().sort_index()
        return jsonify({
            "hours": [int(x) for x in grouped.index],
            "averageRentals": [round(float(x), 1) for x in grouped.values]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)