document.addEventListener("DOMContentLoaded", () => {
  const predictionForm = document.getElementById("predictionForm");
  const capacityForm = document.getElementById("capacityForm");
  const weatherFilter = document.getElementById("analysisWeather");

  // Set today's date if the date field is empty.
  const dateInput = document.getElementById("date");

  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().slice(0, 10);
  }

  // ------------------------------
  // DEMAND PREDICTION
  // Sends input values to Flask.
  // ------------------------------
  if (predictionForm) {
    predictionForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const resultHeading = document.getElementById("predictedDemand");
      const advice = document.getElementById("predictionAdvice");
      const status = document.getElementById("dataStatus");

      resultHeading.textContent = "Calculating...";
      advice.textContent = "";
      status.textContent = "";

      const predictionData = {
        hour: Number(document.getElementById("hour").value),
        weather: Number(document.getElementById("weather").value),
        season: Number(document.getElementById("season").value),
        holiday: Number(document.getElementById("holiday").value),
        availableBikes: Number(
          document.getElementById("availableBikes").value
        )
      };

      try {
        const response = await fetch("/api/predict", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(predictionData)
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || "Prediction request failed.");
        }

        resultHeading.textContent =
          `${result.estimatedDemand} bicycles`;

        advice.textContent = result.recommendation;
        status.textContent = result.method;
      } catch (error) {
        resultHeading.textContent = "Prediction unavailable";
        advice.textContent = error.message;
        status.textContent =
          "Check that Flask is running and hour.csv is beside app.py.";
      }
    });
  }

  // ------------------------------
  // DEMAND ANALYSIS CHART
  // Gets chart data from Flask.
  // ------------------------------
  let demandChart = null;

  async function loadDemandChart() {
    const canvas = document.getElementById("demandChart");
    const status = document.getElementById("analysisStatus");

    if (!canvas) return;

    const weather = weatherFilter ? weatherFilter.value : "all";

    if (status) {
      status.textContent = "Loading chart...";
    }

    try {
      const response = await fetch(
        `/api/hourly-demand?weather=${encodeURIComponent(weather)}`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Could not load chart data.");
      }

      if (!result.hours || result.hours.length === 0) {
        if (status) {
          status.textContent =
            "No data is available for this weather selection.";
        }

        if (demandChart) {
          demandChart.destroy();
          demandChart = null;
        }

        return;
      }

      if (demandChart) {
        demandChart.destroy();
      }

      demandChart = new Chart(canvas, {
        type: "line",
        data: {
          labels: result.hours.map((hour) => `${hour}:00`),
          datasets: [{
            label: "Average bicycle rentals",
            data: result.averageRentals,
            borderColor: "#087bd1",
            backgroundColor: "rgba(8, 123, 209, 0.12)",
            fill: true,
            tension: 0.3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: "Average rentals"
              }
            },
            x: {
              title: {
                display: true,
                text: "Hour of day"
              }
            }
          }
        }
      });

      if (status) {
        status.textContent = "Chart data loaded from the Flask backend.";
      }
    } catch (error) {
      if (status) {
        status.textContent =
          `${error.message} Check that Flask is running and hour.csv is beside app.py.`;
      }
    }
  }

  if (weatherFilter) {
    weatherFilter.addEventListener("change", loadDemandChart);
  }

  // ------------------------------
  // CAPACITY PLANNING
  // Calculates the required bicycle supply.
  // ------------------------------
  if (capacityForm) {
    capacityForm.addEventListener("submit", (event) => {
      event.preventDefault();

      const demand = Number(
        document.getElementById("capacityDemand").value
      );

      const available = Number(
        document.getElementById("capacityAvailable").value
      );

      const reserve = Number(
        document.getElementById("reservePercent").value
      );

      const required = Math.ceil(demand * (1 + reserve / 100));
      const difference = required - available;

      const action = document.getElementById("capacityAction");
      const details = document.getElementById("capacityDetails");
      const note = document.getElementById("capacityNote");

          if (difference > 0) {
        action.textContent = `Add ${difference} bicycles`;
      } else if (difference < 0) {
        action.textContent = `Remove ${Math.abs(difference)} bicycles`;
      } else {
        action.textContent = "No change needed";
      }

      details.textContent =
        `Target including reserve: ${required} bicycles. Available: ${available}.`;

      note.textContent =
        "Target = predicted demand plus the selected reserve percentage.";
    });
  }

  // Load the chart when the script starts.
  loadDemandChart();
});