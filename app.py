import shap
import json
import numpy as np
import pandas as pd
import joblib
from flask import Flask, render_template, request, Response
import warnings
warnings.filterwarnings(
    "ignore",
    message="X has feature names, but RandomForestClassifier was fitted without feature names"
)


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


# ==================== Explainability (Console) ====================

baseline_explainer = None
enhanced_rf_explainer = None
enhanced_xgb_explainer = None


def _init_explainers():
    global baseline_explainer, enhanced_rf_explainer, enhanced_xgb_explainer
    if shap is None:
        print("⚠️ SHAP not installed. Explainability console output disabled.")
        return

    try:
        if baseline_model is not None:
            baseline_explainer = shap.TreeExplainer(baseline_model)
        if "rf_best" in globals() and rf_best is not None:
            enhanced_rf_explainer = shap.TreeExplainer(rf_best)
        if "xgb_best" in globals() and xgb_best is not None:
            enhanced_xgb_explainer = shap.TreeExplainer(xgb_best)

        print("✓ SHAP explainers ready")
    except Exception as e:
        print(f"⚠️ SHAP explainers init failed: {e}")


def _get_pos_class_shap(explainer, X_df):
    exp = explainer(X_df)
    vals = exp.values
    base = exp.base_values

    # Some SHAP versions return a list per class
    if isinstance(vals, list):
        vals = vals[1]
        if isinstance(base, list):
            base = base[1]

    vals = np.asarray(vals)
    p = int(X_df.shape[1])

    # Handle 3D outputs:
    # either (n, classes, p) or (n, p, classes)
    if vals.ndim == 3:
        if vals.shape[1] == 2 and vals.shape[2] == p:
            pos_vals = vals[:, 1, :]          # (n, p)
        elif vals.shape[2] == 2 and vals.shape[1] == p:
            pos_vals = vals[:, :, 1]          # (n, p)
        else:
            # fallback: try to pick the axis that equals 2 as classes
            if vals.shape[-1] == 2:
                pos_vals = vals[..., 1]
            else:
                pos_vals = vals[:, 1, :]
    else:
        pos_vals = vals

    v = np.asarray(pos_vals[0], dtype=float)

    # base_values can be scalar, (n,), (n,2), (2,), etc.
    b = np.asarray(base, dtype=float)
    if b.ndim == 0:
        base_scalar = float(b)
    else:
        b = b.reshape(-1)
        base_scalar = float(b[1] if b.size == 2 else b[0])

    return v, base_scalar


def _print_feature_breakdown(title, feature_list, shap_vals):
    shap_vals = np.array(shap_vals, dtype=float)
    abs_vals = np.abs(shap_vals)
    total = float(abs_vals.sum()) if float(abs_vals.sum()) != 0 else 1.0

    rows = []
    for f, v, a in zip(feature_list, shap_vals, abs_vals):
        pct = (a / total) * 100.0
        rows.append((f, float(v), float(pct)))

    rows.sort(key=lambda x: abs(x[1]), reverse=True)

    print("\n" + "=" * 72)
    print(title)
    print("-" * 72)
    print(f"{'Feature':30s} {'Contribution':>14s} {'Impact%':>10s}")
    print("-" * 72)
    for f, v, pct in rows:
        print(f"{str(f)[:30]:30s} {v:14.6f} {pct:9.2f}%")
    print("-" * 72)
    top = ", ".join([r[0] for r in rows[:5]])
    print(f"Top drivers: {top}")
    print("=" * 72 + "\n")

# New Inserted Code:


def _shap_to_json(feature_list, shap_vals):
    shap_vals = np.asarray(shap_vals, dtype=float)
    abs_vals = np.abs(shap_vals)
    total = float(abs_vals.sum()) if float(abs_vals.sum()) != 0 else 1.0

    rows = []
    for f, v, a in zip(feature_list, shap_vals, abs_vals):
        rows.append({
            "feature": str(f),
            "contribution": float(v),
            "impact_percent": float((a / total) * 100.0)
        })

    rows.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    return rows


# No meta feature redistribution needed in this version
def _redistribute_meta_feature(shap_vals, cols, base_cols, meta_col):
    shap_vals = np.asarray(shap_vals, dtype=float)
    cols = list(cols)

    if meta_col not in cols:
        keep_idx = [cols.index(c) for c in base_cols if c in cols]
        return shap_vals[keep_idx]

    meta_idx = cols.index(meta_col)

    # indices for the 16 original/base features in the current cols
    base_idx = [cols.index(c) for c in base_cols if c in cols]

    base_vals = shap_vals[base_idx].copy()
    meta_val = float(shap_vals[meta_idx])

    # distribute meta influence proportional to absolute base influence
    weights = np.abs(base_vals)
    total = float(weights.sum())

    if total <= 0:
        # fallback: equal distribution if all base contributions are ~0
        weights = np.ones_like(base_vals, dtype=float) / max(len(base_vals), 1)
    else:
        weights = weights / total

    # add redistributed meta contribution (keeps sign of meta_val)
    base_vals = base_vals + (meta_val * weights)

    return base_vals


def _impact_to_100(items):
    # enforce sum to exactly 100 (reduce rounding confusion)
    total = sum(x["impact_percent"] for x in items)
    if total == 0:
        return items

    scale = 100.0 / total
    for x in items:
        x["impact_percent"] *= scale

    # final tiny correction on the first item to hit exactly 100.0
    total2 = sum(x["impact_percent"] for x in items)
    if items:
        items[0]["impact_percent"] += (100.0 - total2)

    return items


_init_explainers()


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


@app.route("/dashboard")
def dashboard():
    return render_template("prediction-dashboard.html")


@app.route("/upload")
def upload():
    return render_template("csv-reader.html")


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

        # ✅ PASTE STEP 3 HERE (console explainability block)
        # ==================== Console Explainability Output (ADD) ====================

        try:
            if shap is not None:
                # Baseline SHAP -> result JSON
                if baseline_model and baseline_explainer is not None:
                    b_vals, _ = _get_pos_class_shap(baseline_explainer, df)
                    result["baseline_explainability"] = {
                        "method": "shap",
                        "items": _shap_to_json(feature_names, b_vals)
                    }

                # Enhanced SHAP -> FINAL BLEND explainability in 16-feature baseline format (NO rf_oof_proba)
                if artifact and rf_feature_model and enhanced_rf_explainer is not None and enhanced_xgb_explainer is not None:
                    rf_vals, _ = _get_pos_class_shap(
                        enhanced_rf_explainer, df_hybrid)
                    xgb_vals, _ = _get_pos_class_shap(
                        enhanced_xgb_explainer, df_hybrid)

                    cols = list(df_hybrid.columns)

                    # 1) remove rf_oof_proba by redistributing its contribution into the 16 original features
                    rf_16 = _redistribute_meta_feature(
                        rf_vals, cols, feature_names, hybrid_feature_name)
                    xgb_16 = _redistribute_meta_feature(
                        xgb_vals, cols, feature_names, hybrid_feature_name)

                    # 2) blend the 16-feature contributions (final decision)
                    blend_16 = (blend_weight * np.asarray(rf_16)) + \
                        ((1 - blend_weight) * np.asarray(xgb_16))

                    # 3) baseline-style JSON output (16 features only)
                    items_16 = _shap_to_json(feature_names, blend_16)
                    items_16 = _impact_to_100(items_16)

                    result["enhanced_explainability_16"] = {
                        "method": "shap",
                        "blend_weight": float(blend_weight),
                        "items": items_16
                    }

        except Exception as ee:
            print(f"⚠️ SHAP JSON output failed: {ee}")

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
