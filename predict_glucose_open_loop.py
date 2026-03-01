#!/usr/bin/env python3
"""
Open-loop glucose forecasting using autoregressive linear regression.

- Reads Dexcom CSV files from V0/data/glucose
- Uses first 80% (time-ordered) of each subject for training windows
- Uses remaining 20% for open-loop prediction
- Saves metrics + predictions + SVG visualization

No heavy dependencies required (only numpy + stdlib).
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np


TIMESTAMP_COL = "Timestamp (YYYY-MM-DDThh:mm:ss)"
EVENT_TYPE_COL = "Event Type"
GLUCOSE_COL = "Glucose Value (mmol/L)"


@dataclass
class SubjectSeries:
    subject_id: str
    times: List[datetime]
    values: List[float]


@dataclass
class ForecastResult:
    subject_id: str
    times: List[datetime]
    actual: List[float]
    pred: List[float]
    mae: float
    rmse: float


def parse_subject_id(path: str) -> str:
    base = os.path.basename(path)
    # e.g. Clarity_Export_SC008.csv -> SC008
    parts = base.replace(".csv", "").split("_")
    return parts[-1] if parts else base


def load_subject_series(path: str) -> SubjectSeries:
    times: List[datetime] = []
    vals: List[float] = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get(EVENT_TYPE_COL) != "EGV":
                continue
            ts = (row.get(TIMESTAMP_COL) or "").strip()
            gv = (row.get(GLUCOSE_COL) or "").strip()
            if not ts or not gv:
                continue
            try:
                dt = datetime.fromisoformat(ts)
                g = float(gv)
            except Exception:
                continue
            times.append(dt)
            vals.append(g)

    # sort by timestamp (safety)
    paired = sorted(zip(times, vals), key=lambda x: x[0])
    times = [p[0] for p in paired]
    vals = [p[1] for p in paired]

    return SubjectSeries(subject_id=parse_subject_id(path), times=times, values=vals)


def build_windows(values: List[float], end_idx: int, window: int) -> Tuple[np.ndarray, np.ndarray]:
    """Build X,y from values[0:end_idx], where each X row uses previous `window` points."""
    X, y = [], []
    for i in range(window, end_idx):
        X.append(values[i - window : i])
        y.append(values[i])
    if not X:
        return np.empty((0, window)), np.empty((0,))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def fit_ridge_linear(X: np.ndarray, y: np.ndarray, l2: float = 1.0) -> Tuple[np.ndarray, float]:
    """Fit y = Xw + b with ridge regularization (closed form)."""
    if X.shape[0] == 0:
        raise ValueError("No training samples available")

    Xb = np.hstack([X, np.ones((X.shape[0], 1))])
    reg = np.eye(Xb.shape[1]) * l2
    reg[-1, -1] = 0.0  # don't regularize bias

    theta = np.linalg.solve(Xb.T @ Xb + reg, Xb.T @ y)
    w = theta[:-1]
    b = float(theta[-1])
    return w, b


def open_loop_predict(values: List[float], split_idx: int, window: int, w: np.ndarray, b: float) -> List[float]:
    """Predict from split_idx to end using recursive (open-loop) forecasting."""
    history = list(values[:split_idx])
    preds: List[float] = []

    for _ in range(split_idx, len(values)):
        x = np.array(history[-window:], dtype=float)
        yhat = float(np.dot(x, w) + b)
        preds.append(yhat)
        history.append(yhat)

    return preds


def mae_rmse(actual: List[float], pred: List[float]) -> Tuple[float, float]:
    a = np.array(actual, dtype=float)
    p = np.array(pred, dtype=float)
    err = a - p
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    return mae, rmse


def save_metrics(path: str, results: List[ForecastResult]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "n_test", "mae", "rmse"])
        for r in results:
            w.writerow([r.subject_id, len(r.actual), f"{r.mae:.4f}", f"{r.rmse:.4f}"])

        overall_mae = np.mean([r.mae for r in results]) if results else float("nan")
        overall_rmse = np.mean([r.rmse for r in results]) if results else float("nan")
        w.writerow([])
        w.writerow(["OVERALL_MEAN", "", f"{overall_mae:.4f}", f"{overall_rmse:.4f}"])


def save_predictions(path: str, results: List[ForecastResult]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "timestamp", "actual_mmolL", "pred_mmolL"])
        for r in results:
            for t, a, p in zip(r.times, r.actual, r.pred):
                w.writerow([r.subject_id, t.isoformat(), f"{a:.4f}", f"{p:.4f}"])


def make_svg_plot(path: str, results: List[ForecastResult], max_subjects: int = 6) -> None:
    """Minimal dependency-free SVG plot for first N subjects."""
    show = results[:max_subjects]
    if not show:
        with open(path, "w", encoding="utf-8") as f:
            f.write("<svg xmlns='http://www.w3.org/2000/svg' width='1000' height='200'></svg>")
        return

    width, height = 1400, 240 * len(show)
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 40
    panel_h = 200

    all_vals = [v for r in show for v in (r.actual + r.pred)]
    y_min, y_max = min(all_vals), max(all_vals)
    y_pad = max(0.5, 0.05 * (y_max - y_min + 1e-6))
    y_min -= y_pad
    y_max += y_pad

    def ymap(v: float, y0: float) -> float:
        return y0 + panel_h - (v - y_min) / (y_max - y_min + 1e-9) * panel_h

    def poly_points(vals: List[float], y0: float) -> str:
        n = len(vals)
        if n <= 1:
            return ""
        x0 = pad_l
        x1 = width - pad_r
        pts = []
        for i, v in enumerate(vals):
            x = x0 + (x1 - x0) * (i / (n - 1))
            y = ymap(v, y0)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    lines = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<style>text{font-family:Arial,sans-serif;font-size:12px}.title{font-size:16px;font-weight:bold}</style>",
        "<text x='20' y='20' class='title'>Open-loop glucose forecast (actual=blue, pred=red dashed)</text>",
    ]

    for idx, r in enumerate(show):
        y0 = 30 + idx * 240
        # panel
        lines.append(f"<rect x='{pad_l}' y='{y0}' width='{width-pad_l-pad_r}' height='{panel_h}' fill='white' stroke='#ddd'/>")

        # y ticks
        for k in range(5):
            v = y_min + (y_max - y_min) * k / 4
            y = ymap(v, y0)
            lines.append(f"<line x1='{pad_l}' y1='{y:.1f}' x2='{width-pad_r}' y2='{y:.1f}' stroke='#f0f0f0'/>")
            lines.append(f"<text x='5' y='{y+4:.1f}'>{v:.1f}</text>")

        # series
        lines.append(
            f"<polyline fill='none' stroke='#1f77b4' stroke-width='1.5' points='{poly_points(r.actual, y0)}'/>"
        )
        lines.append(
            f"<polyline fill='none' stroke='#d62728' stroke-width='1.5' stroke-dasharray='5,4' points='{poly_points(r.pred, y0)}'/>"
        )

        # labels
        lines.append(
            f"<text x='{pad_l+4}' y='{y0+16}'>"
            f"{r.subject_id} | test n={len(r.actual)} | MAE={r.mae:.3f} | RMSE={r.rmse:.3f}</text>"
        )

    lines.append("</svg>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Open-loop glucose forecasting")
    parser.add_argument("--glucose-dir", default="data/glucose", help="Folder with Clarity_Export_*.csv")
    parser.add_argument("--out-dir", default="outputs/glucose_forecast", help="Output directory")
    parser.add_argument("--window", type=int, default=12, help="AR window length (12 ~= 1 hour at 5-min sampling)")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio (default 0.8)")
    parser.add_argument("--min-points", type=int, default=200, help="Skip subjects with fewer points")
    parser.add_argument("--ridge", type=float, default=1.0, help="Ridge L2")
    args = parser.parse_args()

    glucose_dir = os.path.abspath(args.glucose_dir)
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(glucose_dir, "*.csv")))
    if not files:
        raise SystemExit(f"No csv files found in {glucose_dir}")

    subjects: List[SubjectSeries] = []
    for f in files:
        s = load_subject_series(f)
        if len(s.values) >= args.min_points:
            subjects.append(s)

    if not subjects:
        raise SystemExit("No subject had enough points after filtering")

    # Build pooled training windows from first 80% of each subject
    X_all, y_all = [], []
    split_indices: Dict[str, int] = {}

    for s in subjects:
        split = int(len(s.values) * args.train_ratio)
        split = max(split, args.window + 1)
        split = min(split, len(s.values) - 1)
        split_indices[s.subject_id] = split

        X, y = build_windows(s.values, split, args.window)
        if len(X) > 0:
            X_all.append(X)
            y_all.append(y)

    if not X_all:
        raise SystemExit("No training windows could be built")

    X_train = np.vstack(X_all)
    y_train = np.concatenate(y_all)

    w, b = fit_ridge_linear(X_train, y_train, l2=args.ridge)

    results: List[ForecastResult] = []
    for s in subjects:
        split = split_indices[s.subject_id]
        pred = open_loop_predict(s.values, split, args.window, w, b)
        actual = s.values[split:]
        times = s.times[split:]
        mae, rmse = mae_rmse(actual, pred)
        results.append(ForecastResult(s.subject_id, times, actual, pred, mae, rmse))

    # sort by RMSE for quick inspection
    results.sort(key=lambda r: r.rmse)

    metrics_csv = os.path.join(out_dir, "metrics.csv")
    pred_csv = os.path.join(out_dir, "predictions.csv")
    plot_svg = os.path.join(out_dir, "open_loop_forecast.svg")

    save_metrics(metrics_csv, results)
    save_predictions(pred_csv, results)
    make_svg_plot(plot_svg, results, max_subjects=6)

    overall_mae = np.mean([r.mae for r in results])
    overall_rmse = np.mean([r.rmse for r in results])

    print("Done.")
    print(f"Subjects used: {len(results)}")
    print(f"Training windows: {len(y_train)}")
    print(f"Overall MAE: {overall_mae:.4f}")
    print(f"Overall RMSE: {overall_rmse:.4f}")
    print(f"Saved: {metrics_csv}")
    print(f"Saved: {pred_csv}")
    print(f"Saved: {plot_svg}")


if __name__ == "__main__":
    main()
