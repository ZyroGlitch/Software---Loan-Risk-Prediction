from flask import Flask, render_template, request, Response
import joblib
import pandas as pd
import numpy as np
import json

app = Flask(__name__)


def json_response(data, status=200):
    return Response(
        json.dumps(data, cls=NumpyEncoder),
        status=status,
        mimetype="application/json"
    )

# ==================== Custom JSON Encoder ====================


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NumPy data types"""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# ⚠️ NOTE: app.json_encoder is ignored in Flask 3.0
# Kept here only for backward compatibility
app.json_encoder = NumpyEncoder

# ==================== Model Loading ====================

artifact = None
baseline_model = None

# Load enhanced model
try:
    artifact = joblib.load("model/enhanced_rf_artifact.pkl")

    rf_feature_model = artifact.get("rf_feature_model")
    rf_best = artifact["rf_best"]
    xgb_best = artifact["xgb_best"]
    blend_weight = artifact["blend_weight"]
    feature_names = artifact["feature_names"]
    hybrid_feature_name = artifact.get("hybrid_feature_name", "rf_oof_proba")
    threshold = artifact.get("threshold", 0.5)

    print("✓ Enhanced model loaded")

except Exception as e:
    print(f"✗ Enhanced model failed: {e}")

# Load baseline model (ALWAYS)
try:
    baseline_artifact = joblib.load("model/baseline_rf_artifact.pkl")
    baseline_model = baseline_artifact["rf_baseline_model"]

    # Use same feature order
    if "feature_names" in baseline_artifact:
        feature_names = baseline_artifact["feature_names"]

    print("✓ Baseline model loaded")

except Exception as e:
    print(f"✗ Baseline model failed: {e}")


# ==================== Helper Functions ====================


def convert_numpy_types(obj):
    """Recursively convert NumPy types to native Python types"""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

# ==================== Routes ====================


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/get-started")
def get_started():
    return render_template("get-started.html")


@app.route("/function")
def function():
    return render_template("function.html")


@app.route("/features")
def features():
    return render_template("features.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

# ==================== Prediction API ====================


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        if not data:
            return json_response({"error": "No data provided"}, 400)

        df = pd.DataFrame([data])

        missing = [f for f in feature_names if f not in df.columns]
        if missing:
            return json_response({
                "error": "Missing required fields",
                "missing": missing
            }, 400)

        df = df[feature_names]

        result = {}

        # ================= Enhanced Model =================
        if artifact and rf_feature_model:
            rf_oof_proba = rf_feature_model.predict_proba(df)[:, 1]

            df_hybrid = df.copy()
            df_hybrid[hybrid_feature_name] = rf_oof_proba

            rf_prob = float(rf_best.predict_proba(df_hybrid)[0][1])
            xgb_prob = float(xgb_best.predict_proba(df_hybrid)[0][1])

            final_prob = (blend_weight * rf_prob) + \
                         ((1 - blend_weight) * xgb_prob)

            prediction = int(final_prob >= threshold)

            result["enhanced_model"] = {
                "loan_status": "Approved" if prediction else "Rejected",
                "risk_percentage": round((100 - (final_prob * 100)), 2),
                "rf_probability": round(rf_prob * 100, 2),
                "xgb_probability": round(xgb_prob * 100, 2),
                "confidence_score": round(max(final_prob, 1 - final_prob) * 100, 2),
                "model_type": "enhanced_blend"
            }

        # ================= Baseline Model =================
        if baseline_model:
            baseline_prob = float(baseline_model.predict_proba(df)[0][1])
            baseline_pred = int(baseline_model.predict(df)[0])

            result["baseline_model"] = {
                "loan_status": "Approved" if baseline_pred else "Rejected",
                "risk_percentage": round((100 - (baseline_prob * 100)), 2),
                "rf_probability": round(baseline_prob * 100, 2),
                "confidence_score": round(max(baseline_prob, 1 - baseline_prob) * 100, 2),
                "model_type": "baseline_rf"
            }

        return json_response(convert_numpy_types(result))

    except Exception as e:
        return json_response({
            "error": "Prediction failed",
            "message": str(e)
        }, 500)


# ==================== Health Check ====================


@app.route("/health")
def health():
    status = {
        "enhanced_model_loaded": artifact is not None,
        "baseline_model_loaded": baseline_model is not None,
        "feature_count": len(feature_names)
    }
    return json_response(convert_numpy_types(status))

# ==================== Run Server ====================


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
