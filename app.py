# app.py file

# Pdf Report Imports
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
from unittest import result
from zoneinfo import ZoneInfo
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import shap
import json
import numpy as np
import pandas as pd
import joblib
from flask import Flask, render_template, request, Response, send_file
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


# ==================== Helper Functions for PDF Report ====================

LABEL_MAP = {
    "age": "Age",
    "marital": "Marital Status",
    "education": "Highest Educational Attainment",
    "job": "Job",
    "contact": "Phone Type",
    "balance": "Balance",
    "housing": "Housing",
    "default": "Default",
    "loan": "Loan",
    "day": "Day",
    "duration": "Duration",
    "month": "Month",
    "campaign": "Campaign",
    "pdays": "Days Since Contact",
    "previous": "Previous Contacts",
    "poutcome": "Previous Outcome",
}

INPUT_ORDER = [
    "age", "job", "marital", "education",
    "contact",
    "balance", "housing", "default", "loan",
    "day", "month", "duration", "campaign",
    "pdays", "previous", "poutcome"
]

VALUE_MAP = {
    "job": {
        0: "Admin",
        1: "Blue-collar",
        2: "Entrepreneur",
        3: "Housemaid",
        4: "Management",
        5: "Retired",
        6: "Self-employed",
        7: "Services",
        8: "Student",
        9: "Technician",
        10: "Unemployed",
        11: "Unknown"
    },

    "marital": {
        0: "Divorced",
        1: "Married",
        2: "Single"
    },

    "education": {
        0: "Primary",
        1: "Secondary",
        2: "Tertiary",
        3: "Unknown"
    },

    "contact": {
        0: "Cellular",
        1: "Telephone",
        2: "Unknown"
    },

    "housing": {
        0: "No",
        1: "Yes"
    },
    "default": {
        0: "No",
        1: "Yes"
    },
    "loan": {
        0: "No",
        1: "Yes"
    },

    "month": {
        0: "April",
        1: "August",
        2: "December",
        3: "February",
        4: "January",
        5: "July",
        6: "June",
        7: "March",
        8: "May",
        9: "November",
        10: "October",
        11: "September"
    },

    "poutcome": {
        0: "Failure",
        1: "Other",
        2: "Success",
        3: "Unknown"
    }
}


def _display_input_value(key, raw):
    if raw is None or raw == "":
        return ""

    try:
        n = int(raw)
    except:
        return str(raw)

    m = VALUE_MAP.get(key)
    if not m:
        return str(raw)

    return m.get(n, str(raw))


def _run_inference_and_explain(data):
    df = pd.DataFrame([data])

    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))

    df = df[feature_names]

    result = {}
    df_hybrid = None

    if artifact and rf_feature_model:
        rf_oof_proba = rf_feature_model.predict_proba(df)[:, 1]
        df_hybrid = df.copy()
        df_hybrid[hybrid_feature_name] = rf_oof_proba

        rf_prob = float(rf_best.predict_proba(df_hybrid)[0][1])
        xgb_prob = float(xgb_best.predict_proba(df_hybrid)[0][1])

        final_prob = (blend_weight * rf_prob) + ((1 - blend_weight) * xgb_prob)
        prediction = int(final_prob >= threshold)

        result["enhanced_model"] = {
            "loan_status": "Approved" if prediction else "Rejected",
            "risk_percentage": round((100 - (final_prob * 100)), 2),
            "rf_probability": round(rf_prob * 100, 2),
            "xgb_probability": round(xgb_prob * 100, 2),
            "confidence_score": round(max(final_prob, 1 - final_prob) * 100, 2),
            "model_type": "enhanced_blend"
        }

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

    if shap is not None:
        if baseline_model and baseline_explainer is not None:
            b_vals, _ = _get_pos_class_shap(baseline_explainer, df)
            items = _shap_to_json(feature_names, b_vals)
            items = _impact_to_100(items)
            result["baseline_explainability"] = {
                "method": "shap", "items": items}

        if artifact and rf_feature_model and df_hybrid is not None and enhanced_rf_explainer is not None and enhanced_xgb_explainer is not None:
            rf_vals, _ = _get_pos_class_shap(enhanced_rf_explainer, df_hybrid)
            xgb_vals, _ = _get_pos_class_shap(
                enhanced_xgb_explainer, df_hybrid)

            cols = list(df_hybrid.columns)

            rf_16 = _redistribute_meta_feature(
                rf_vals, cols, feature_names, hybrid_feature_name)
            xgb_16 = _redistribute_meta_feature(
                xgb_vals, cols, feature_names, hybrid_feature_name)

            blend_16 = (blend_weight * np.asarray(rf_16)) + \
                ((1 - blend_weight) * np.asarray(xgb_16))
            items_16 = _shap_to_json(feature_names, blend_16)
            items_16 = _impact_to_100(items_16)

            result["enhanced_explainability_16"] = {
                "method": "shap",
                "blend_weight": float(blend_weight),
                "items": items_16
            }

    return convert_numpy_types(result), df


def _build_pdf_bytes(result, input_data):
    tz = ZoneInfo("Asia/Manila")
    now = datetime.now(tz)
    date_str = now.strftime("%d / %m / %Y")
    time_str = now.strftime("%H:%M")

    decision = None
    if result.get("enhanced_model"):
        decision = result["enhanced_model"]["loan_status"]
    elif result.get("baseline_model"):
        decision = result["baseline_model"]["loan_status"]
    else:
        decision = "None"

    title_text = "ACCEPTED" if decision == "Approved" else "REJECTED" if decision == "Rejected" else "RESULT"

    styles = getSampleStyleSheet()

    # ✅ ADD IT HERE (RIGHT AFTER styles is created)
    styles.add(ParagraphStyle(
        name="H4X",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="H1X",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="H2X",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(name="SmallX",
               parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(
        name="MetaX", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#4B5563")))

    buff = BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm
    )

    story = []

    available_w = doc.width  # full writable width (inside margins)

    header_tbl = Table(
        [[
            Paragraph(f"<b>Date</b>: {date_str}", styles["MetaX"]),
            Paragraph(f"<b>Time</b>: {time_str}", styles["MetaX"]),
        ]],
        colWidths=[available_w - 70, 70],  # ✅ KEY FIX
        hAlign="LEFT"  # ✅ prevents the table from centering
    )

    header_tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),  # ✅ pushes Time to the far right
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(header_tbl)

    status_color = "#16A34A" if decision == "Approved" else "#DC2626" if decision == "Rejected" else "#111827"

    status_word = "Accepted" if decision == "Approved" else "Rejected" if decision == "Rejected" else "Result"

    # ✅ H4-sized, single line, only ONE status word
    story.append(Paragraph(
        f"<b>Loan Report Status:</b> <font color='{status_color}'><b>{status_word}</b></font>",
        styles["H4X"]
    ))
    story.append(Spacer(1, 8))

    baseline = result.get("baseline_model") or {}
    enhanced = result.get("enhanced_model") or {}

    def pct(x):
        try:
            return f"{float(x):.2f}%"
        except:
            return "-"

    summary_data = [
        ["Model", "Loan Status", "Risk Percentage", "Confidence Score"],
        ["Baseline (Random Forest)",
         baseline.get("loan_status", "-"),
         pct(baseline.get("risk_percentage")),
         pct(baseline.get("confidence_score"))],
        ["Optimized (RF + XGBoost)",
         enhanced.get("loan_status", "-"),
         pct(enhanced.get("risk_percentage")),
         pct(enhanced.get("confidence_score"))],
    ]

    summary_col_widths = [
        doc.width * 0.33, doc.width *
        0.22, doc.width * 0.225, doc.width * 0.225
    ]

    summary_tbl = Table(
        summary_data,
        colWidths=summary_col_widths,
        hAlign="LEFT"
    )

    # summary_tbl.setStyle(TableStyle([
    #     ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
    #     ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    #     ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    #     ("FONTSIZE", (0, 0), (-1, -1), 9),

    #     # ✅ LEFT align Risk % and Confidence Score (data rows only)
    #     ("ALIGN", (2, 1), (3, -1), "LEFT"),

    #     # keep others readable
    #     ("ALIGN", (0, 1), (1, -1), "LEFT"),
    #     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

    #     ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    #     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
    #         colors.white,
    #         colors.HexColor("#F9FAFB")
    #     ]),

    #     ("TOPPADDING", (0, 0), (-1, -1), 6),
    #     ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    # ]))

    summary_tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),

        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),

        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),
        ("ALIGN", (2, 1), (3, -1), "LEFT"),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FAFB")]),
    ]))

    story.append(summary_tbl)
    story.append(Spacer(1, 12))

    story.append(
        Paragraph("Feature Contributions & Impacts", styles["H2X"]))

    b_items = (result.get("baseline_explainability") or {}).get("items") or []
    o_items = (result.get("enhanced_explainability_16")
               or {}).get("items") or []

    b_map = {x["feature"]: x for x in b_items}
    o_map = {x["feature"]: x for x in o_items}

    def fnum(x, d=2):
        try:
            return f"{float(x):.{d}f}"
        except:
            return "-"

    hdr_center = ParagraphStyle(
        name="HdrCenter",
        parent=styles["Normal"],
        fontSize=8,
        leading=9,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    hdr_left = ParagraphStyle(
        name="HdrLeft",
        parent=styles["Normal"],
        fontSize=8,
        leading=9,
        textColor=colors.white,
        alignment=TA_LEFT
    )

    cell_center = ParagraphStyle(
        name="CellCenter",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER
    )

    cell_left = ParagraphStyle(
        name="CellLeft",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_LEFT
    )

    shap_rows = [[
        Paragraph("Feature", hdr_left),  # ✅ Feature header LEFT
        Paragraph("Baseline<br/>Contribution", hdr_center),
        Paragraph("Baseline<br/>Impact %", hdr_center),
        Paragraph("Optimized<br/>Contribution", hdr_center),
        Paragraph("Optimized<br/>Impact %", hdr_center),
    ]]

    for f in feature_names:
        bi = b_map.get(f, {})
        oi = o_map.get(f, {})

        shap_rows.append([
            # ✅ Feature column LEFT
            Paragraph(LABEL_MAP.get(f, f), cell_left),
            Paragraph(fnum(bi.get("contribution"), 6),
                      cell_center),   # ✅ rest CENTER
            Paragraph((fnum(bi.get("impact_percent"), 2) + "%")
                      if bi else "-", cell_center),
            Paragraph(fnum(oi.get("contribution"), 6), cell_center),
            Paragraph((fnum(oi.get("impact_percent"), 2) + "%")
                      if oi else "-", cell_center),
        ])

    # shap_tbl = Table(
    #     shap_rows,
    #     colWidths=[52*mm, 42*mm, 22*mm, 42*mm, 22*mm],
    #     repeatRows=1,
    #     hAlign="LEFT"
    # )

    shap_col_widths = [
        doc.width * 0.28, doc.width * 0.22,
        doc.width * 0.12, doc.width * 0.22, doc.width * 0.16
    ]

    shap_tbl = Table(
        shap_rows,
        colWidths=shap_col_widths,
        repeatRows=1,
        hAlign="LEFT"
    )

    shap_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

        ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
    ]))

    story.append(shap_tbl)

    story.append(PageBreak())

    story.append(
        Paragraph("Loan Information Provided by the User", styles["H2X"]))
    story.append(Spacer(1, 6))

    # input_rows = [["Field", "Value"]]
    # for k in INPUT_ORDER:
    #     input_rows.append([LABEL_MAP.get(k, k), str(input_data.get(k, ""))])
    input_rows = [["Field", "Value"]]
    for k in INPUT_ORDER:
        raw_val = input_data.get(k, "")
        display_val = _display_input_value(k, raw_val)  # ✅ decode for PDF only
        input_rows.append([LABEL_MAP.get(k, k), str(display_val)])

    inputs_tbl = Table(input_rows, colWidths=[70*mm, 98*mm])
    inputs_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(inputs_tbl)

    doc.build(story)
    pdf = buff.getvalue()
    buff.close()
    return pdf, now

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
        df_hybrid = None

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
                # if artifact and rf_feature_model and enhanced_rf_explainer is not None and enhanced_xgb_explainer is not None:
                if artifact and rf_feature_model and df_hybrid is not None and enhanced_rf_explainer is not None and enhanced_xgb_explainer is not None:
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


@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json()
        if not data:
            return json_response({"error": "No data provided"}, 400)

        result, _ = _run_inference_and_explain(data)
        pdf_bytes, now = _build_pdf_bytes(result, data)

        filename = "Loan_Risk_Report_" + now.strftime("%Y%m%d_%H%M") + ".pdf"

        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return json_response({
            "error": "Report generation failed",
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
