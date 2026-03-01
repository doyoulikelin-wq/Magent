#!/usr/bin/env python3
"""
Predict high-calorie meals ("binge") from meal-history features.
Data source: data/index_corrected.csv with columns [SCxxx, timestamp, calories]

Model: logistic regression (numpy, no sklearn dependency)
Split: per subject, time-ordered 80/20
"""
from __future__ import annotations

import argparse
import csv
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Tuple

import numpy as np


@dataclass
class Meal:
    sid: str
    ts: datetime
    kcal: float


def load_meals(path: str) -> List[Meal]:
    meals: List[Meal] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = row.get("SCxxx", "").strip()
            t = row.get("timestamp", "").strip()
            c = row.get("calories", "").strip()
            if not sid or not t or not c:
                continue
            try:
                ts = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
                kcal = float(c)
            except Exception:
                continue
            meals.append(Meal(sid=sid, ts=ts, kcal=kcal))
    meals.sort(key=lambda m: (m.sid, m.ts))
    return meals


def build_features(meals: List[Meal], threshold: float) -> Tuple[np.ndarray, np.ndarray, List[Tuple[str, datetime, float]]]:
    X, y, meta = [], [], []
    by_sid: Dict[str, List[Meal]] = {}
    for m in meals:
        by_sid.setdefault(m.sid, []).append(m)

    for sid, arr in by_sid.items():
        arr.sort(key=lambda m: m.ts)
        prev_kcals: List[float] = []
        prev_times: List[datetime] = []
        for m in arr:
            hour = m.ts.hour + m.ts.minute / 60.0
            dow = m.ts.weekday()

            # history-only features (available before this meal)
            last_kcal = prev_kcals[-1] if prev_kcals else 0.0
            mean3 = float(np.mean(prev_kcals[-3:])) if prev_kcals else 0.0
            mean7 = float(np.mean(prev_kcals[-7:])) if prev_kcals else 0.0
            std3 = float(np.std(prev_kcals[-3:])) if len(prev_kcals) >= 2 else 0.0
            binge_last3 = float(sum(1 for v in prev_kcals[-3:] if v >= threshold))
            meals_seen = float(len(prev_kcals))

            if prev_times:
                delta_h = (m.ts - prev_times[-1]).total_seconds() / 3600.0
                delta_h = max(0.0, min(delta_h, 72.0))
            else:
                delta_h = 12.0

            feats = [
                1.0,
                math.sin(2 * math.pi * hour / 24.0),
                math.cos(2 * math.pi * hour / 24.0),
                math.sin(2 * math.pi * dow / 7.0),
                math.cos(2 * math.pi * dow / 7.0),
                last_kcal,
                mean3,
                mean7,
                std3,
                binge_last3,
                delta_h,
                meals_seen,
            ]
            X.append(feats)
            y.append(1.0 if m.kcal >= threshold else 0.0)
            meta.append((sid, m.ts, m.kcal))

            prev_kcals.append(m.kcal)
            prev_times.append(m.ts)

    return np.array(X, dtype=float), np.array(y, dtype=float), meta


def split_mask(meta: List[Tuple[str, datetime, float]], ratio: float = 0.8) -> np.ndarray:
    by_sid_idx: Dict[str, List[int]] = {}
    for i, (sid, _, _) in enumerate(meta):
        by_sid_idx.setdefault(sid, []).append(i)
    mask = np.zeros(len(meta), dtype=bool)
    for sid, idxs in by_sid_idx.items():
        n = len(idxs)
        k = int(n * ratio)
        k = max(1, min(k, n - 1)) if n >= 2 else 1
        for i in idxs[:k]:
            mask[i] = True
    return mask


def standardize_train_test(X: np.ndarray, train_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = X[train_mask].mean(axis=0)
    sd = X[train_mask].std(axis=0)
    sd = np.where(sd < 1e-9, 1.0, sd)
    Xn = (X - mu) / sd
    return Xn, mu, sd


def fit_logreg(X: np.ndarray, y: np.ndarray, lr: float = 0.05, steps: int = 2500, l2: float = 1e-3) -> np.ndarray:
    w = np.zeros(X.shape[1], dtype=float)
    for _ in range(steps):
        z = X @ w
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        grad = (X.T @ (p - y)) / len(y) + l2 * w
        w -= lr * grad
    return w


def predict_proba(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    z = X @ w
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def eval_binary(y: np.ndarray, p: np.ndarray, thr: float = 0.5) -> Dict[str, float]:
    pred = (p >= thr).astype(float)
    tp = float(np.sum((pred == 1) & (y == 1)))
    tn = float(np.sum((pred == 0) & (y == 0)))
    fp = float(np.sum((pred == 1) & (y == 0)))
    fn = float(np.sum((pred == 0) & (y == 1)))

    acc = (tp + tn) / max(1.0, len(y))
    prec = tp / max(1.0, tp + fp)
    rec = tp / max(1.0, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, (prec + rec))
    return {"acc": acc, "precision": prec, "recall": rec, "f1": f1, "tp": tp, "tn": tn, "fp": fp, "fn": fn}


def save_csv_metrics(path: str, metrics: Dict[str, float], threshold: float, train_n: int, test_n: int, pos_rate: float):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["binge_threshold_kcal", f"{threshold:.1f}"])
        w.writerow(["train_samples", train_n])
        w.writerow(["test_samples", test_n])
        w.writerow(["test_positive_rate", f"{pos_rate:.4f}"])
        for k, v in metrics.items():
            w.writerow([k, f"{v:.6f}"])


def save_csv_predictions(path: str, meta: List[Tuple[str, datetime, float]], y: np.ndarray, p: np.ndarray, test_mask: np.ndarray):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sid", "timestamp", "calories", "is_binge", "pred_prob"])
        for i, m in enumerate(meta):
            if not test_mask[i]:
                continue
            sid, ts, kcal = m
            w.writerow([sid, ts.isoformat(sep=' '), f"{kcal:.1f}", int(y[i]), f"{p[i]:.6f}"])


def save_svg(path: str, y_test: np.ndarray, p_test: np.ndarray, threshold: float):
    # sort by predicted probability for a clear ranking plot
    idx = np.argsort(-p_test)
    p = p_test[idx]
    y = y_test[idx]

    n = len(p)
    width, height = 1400, 700
    left, top = 70, 70
    plot_w, plot_h = 1260, 450

    def x(i):
        return left + (i / max(1, n - 1)) * plot_w

    def ymap(v):
        return top + (1.0 - v) * plot_h

    # lines
    p_pts = " ".join(f"{x(i):.1f},{ymap(float(v)):.1f}" for i, v in enumerate(p))
    y_pts = " ".join(f"{x(i):.1f},{ymap(float(v)):.1f}" for i, v in enumerate(y))

    lines = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<style>text{font-family:Arial,sans-serif;font-size:13px}.t{font-size:20px;font-weight:bold}</style>",
        "<rect width='100%' height='100%' fill='white'/>",
        "<text x='20' y='32' class='t'>Binge prediction (test set): probability ranking</text>",
        f"<text x='20' y='56'>Red=predicted probability, Blue=true label (0/1), threshold={threshold:.0f} kcal</text>",
        f"<rect x='{left}' y='{top}' width='{plot_w}' height='{plot_h}' fill='none' stroke='#ccc'/>",
    ]

    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        yy = ymap(t)
        lines.append(f"<line x1='{left}' y1='{yy:.1f}' x2='{left+plot_w}' y2='{yy:.1f}' stroke='#eee'/>")
        lines.append(f"<text x='25' y='{yy+4:.1f}'>{t:.2f}</text>")

    lines.append(f"<polyline fill='none' stroke='#d62728' stroke-width='1.5' points='{p_pts}'/>")
    lines.append(f"<polyline fill='none' stroke='#1f77b4' stroke-width='1.2' points='{y_pts}'/>")
    lines.append(f"<text x='{left}' y='{top+plot_h+28}'>samples sorted by predicted risk (high → low)</text>")
    lines.append("</svg>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/index_corrected.csv")
    ap.add_argument("--out-dir", default="outputs/binge_prediction")
    ap.add_argument("--threshold", type=float, default=800.0, help="kcal threshold for binge label")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    meals = load_meals(args.input)
    X, y, meta = build_features(meals, threshold=args.threshold)

    mask_train = split_mask(meta, ratio=0.8)
    mask_test = ~mask_train

    Xn, _, _ = standardize_train_test(X, mask_train)
    w = fit_logreg(Xn[mask_train], y[mask_train])
    p = predict_proba(Xn, w)

    test_metrics = eval_binary(y[mask_test], p[mask_test], thr=0.5)
    pos_rate = float(np.mean(y[mask_test])) if np.sum(mask_test) else 0.0

    metrics_csv = os.path.join(args.out_dir, "metrics.csv")
    preds_csv = os.path.join(args.out_dir, "predictions.csv")
    svg_path = os.path.join(args.out_dir, "binge_prediction_test.svg")

    save_csv_metrics(metrics_csv, test_metrics, args.threshold, int(np.sum(mask_train)), int(np.sum(mask_test)), pos_rate)
    save_csv_predictions(preds_csv, meta, y, p, mask_test)
    save_svg(svg_path, y[mask_test], p[mask_test], args.threshold)

    print("Done")
    print(f"samples: total={len(y)} train={int(np.sum(mask_train))} test={int(np.sum(mask_test))}")
    print(f"test positive rate: {pos_rate:.4f}")
    print("metrics:", test_metrics)
    print("saved:")
    print(metrics_csv)
    print(preds_csv)
    print(svg_path)


if __name__ == "__main__":
    main()
