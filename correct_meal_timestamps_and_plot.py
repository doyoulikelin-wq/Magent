import csv
import math
import re
import statistics
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/Users/linlin/Desktop/V0')
DATA_DIR = ROOT / 'data'
GLUCOSE_DIR = DATA_DIR / 'glucose'
INDEX_CSV = DATA_DIR / 'index.csv'
INDEX_CORRECTED_CSV = DATA_DIR / 'index_corrected.csv'
RAW_DIR = DATA_DIR / 'raw'

USER_RE = re.compile(r'(SC\d{3})')


@dataclass
class MealRow:
    user_id: str
    timestamp: datetime
    calories: float


@dataclass
class CorrectionResult:
    corrected_ts: datetime
    confidence: float
    delta_min: float


def _load_font(size: int):
    for name in ('DejaVuSans.ttf', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_glucose_points_by_user():
    user_points: dict[str, list[tuple[datetime, float]]] = {}

    for fp in sorted(GLUCOSE_DIR.glob('Clarity_Export_SC*.csv')):
        m = USER_RE.search(fp.name)
        if not m:
            continue
        user_id = m.group(1)

        points = []
        with fp.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get('Event Type') or '').strip() != 'EGV':
                    continue
                ts_raw = (row.get('Timestamp (YYYY-MM-DDThh:mm:ss)') or '').strip()
                g_raw = (row.get('Glucose Value (mmol/L)') or '').strip()
                if not ts_raw or not g_raw:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_raw)
                    g = float(g_raw)
                except ValueError:
                    continue
                points.append((ts, g))

        points.sort(key=lambda x: x[0])
        user_points[user_id] = points

    return user_points


def load_index_rows(glucose_users: set[str]):
    rows: list[MealRow] = []
    with INDEX_CSV.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = (row.get('SCxxx') or '').strip()
            if user_id not in glucose_users:
                continue

            ts_raw = (row.get('timestamp') or '').strip()
            cal_raw = (row.get('calories') or '').strip()
            if not ts_raw or not cal_raw:
                continue
            try:
                ts = datetime.strptime(ts_raw, '%Y-%m-%d %H:%M:%S')
                calories = float(cal_raw)
            except ValueError:
                continue
            rows.append(MealRow(user_id=user_id, timestamp=ts, calories=calories))

    rows.sort(key=lambda x: (x.user_id, x.timestamp))
    return rows


def _collect_window(values: list[tuple[datetime, float]], t0: datetime, t1: datetime):
    return [v for ts, v in values if t0 <= ts <= t1]


def _interp_glucose(
    points: list[tuple[datetime, float]],
    target: datetime,
    *,
    allow_extrapolation: bool = True,
    max_neighbor_gap_min: float | None = None,
):
    if not points:
        return None
    ts_list = [ts for ts, _ in points]
    idx = bisect_left(ts_list, target)

    if idx <= 0:
        if allow_extrapolation:
            return points[0][1]
        return points[0][1] if points[0][0] == target else None
    if idx >= len(points):
        if allow_extrapolation:
            return points[-1][1]
        return points[-1][1] if points[-1][0] == target else None

    t0, g0 = points[idx - 1]
    t1, g1 = points[idx]
    left_gap = (target - t0).total_seconds() / 60.0
    right_gap = (t1 - target).total_seconds() / 60.0
    if max_neighbor_gap_min is not None and (left_gap > max_neighbor_gap_min or right_gap > max_neighbor_gap_min):
        return None
    span = (t1 - t0).total_seconds()
    if span <= 0:
        return g0
    ratio = (target - t0).total_seconds() / span
    return g0 + (g1 - g0) * ratio


def _candidate_score(points: list[tuple[datetime, float]], cand_ts: datetime, anchor_ts: datetime):
    pre_vals = _collect_window(points, cand_ts - timedelta(minutes=35), cand_ts - timedelta(minutes=5))
    post1_vals = _collect_window(points, cand_ts + timedelta(minutes=20), cand_ts + timedelta(minutes=70))
    post2_vals = _collect_window(points, cand_ts + timedelta(minutes=60), cand_ts + timedelta(minutes=140))

    if len(pre_vals) < 2 or len(post1_vals) < 2:
        return -999.0

    g0 = _interp_glucose(points, cand_ts)
    if g0 is None:
        return -999.0

    baseline = statistics.median(pre_vals)
    pre_rise = g0 - baseline
    rise1 = max(post1_vals) - g0
    rise2 = (max(post2_vals) - g0) if post2_vals else rise1
    auc1 = sum(max(v - g0, 0.0) for v in post1_vals)

    distance_hours = abs((cand_ts - anchor_ts).total_seconds()) / 3600.0

    score = 0.0
    score += 1.35 * max(rise1, 0.0)
    score += 0.85 * max(rise2, 0.0)
    score += 0.06 * auc1
    score -= 0.95 * max(pre_rise, 0.0)  # penalize candidates already in rising/high phase
    score -= 0.12 * distance_hours

    # Hard penalties for unlikely onset.
    if rise1 < 0.25:
        score -= 1.2
    if g0 - baseline > 1.5:
        score -= 0.8

    return score


def infer_corrected_meal_time(
    points: list[tuple[datetime, float]],
    logged_ts: datetime,
    lag_bias_min: float = 0.0,
):
    if len(points) < 12:
        return CorrectionResult(corrected_ts=logged_ts, confidence=0.0, delta_min=0.0)

    anchor_ts = logged_ts + timedelta(minutes=lag_bias_min)
    win_start = anchor_ts - timedelta(minutes=130)
    win_end = anchor_ts + timedelta(minutes=60)

    candidates = [ts for ts, _ in points if win_start <= ts <= win_end]
    if len(candidates) < 4:
        return CorrectionResult(corrected_ts=logged_ts, confidence=0.0, delta_min=0.0)

    best_ts = logged_ts
    best_score = -999.0
    for cand_ts in candidates:
        score = _candidate_score(points, cand_ts, anchor_ts)
        if score > best_score:
            best_score = score
            best_ts = cand_ts

    # convert score to confidence in [0,1]
    z = max(-60.0, min(60.0, best_score - 1.0))
    confidence = 1.0 / (1.0 + math.exp(-z))

    if best_score < 0.35:
        return CorrectionResult(corrected_ts=logged_ts, confidence=round(confidence, 3), delta_min=0.0)

    delta_min = (best_ts - logged_ts).total_seconds() / 60.0
    if abs(delta_min) > 180:
        return CorrectionResult(corrected_ts=logged_ts, confidence=round(confidence, 3), delta_min=0.0)

    return CorrectionResult(corrected_ts=best_ts, confidence=round(confidence, 3), delta_min=round(delta_min, 1))


def correct_user_meals(points: list[tuple[datetime, float]], meals: list[MealRow]):
    if not meals:
        return []

    # Pass 1: rough user lag estimate.
    deltas = []
    pass1 = []
    for meal in meals:
        res = infer_corrected_meal_time(points, meal.timestamp, lag_bias_min=0.0)
        pass1.append((meal, res))
        if res.confidence >= 0.55 and abs(res.delta_min) <= 120:
            deltas.append(res.delta_min)

    user_lag = statistics.median(deltas) if deltas else 0.0

    # Pass 2: with user lag bias.
    corrected = []
    for meal in meals:
        res = infer_corrected_meal_time(points, meal.timestamp, lag_bias_min=user_lag)
        final_ts = res.corrected_ts if res.confidence >= 0.35 else meal.timestamp
        corrected.append(
            {
                'user_id': meal.user_id,
                'raw_ts': meal.timestamp,
                'corrected_ts': final_ts,
                'calories': meal.calories,
                'confidence': res.confidence,
                'delta_min': (final_ts - meal.timestamp).total_seconds() / 60.0,
            }
        )

    return corrected


def write_index_corrected(rows):
    with INDEX_CORRECTED_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['SCxxx', 'timestamp', 'calories'])
        for r in rows:
            cal = r['calories']
            cal_out = int(cal) if float(cal).is_integer() else round(float(cal), 2)
            w.writerow([r['user_id'], r['corrected_ts'].strftime('%Y-%m-%d %H:%M:%S'), cal_out])


def _hour_of_day(dt: datetime):
    return dt.hour + dt.minute / 60 + dt.second / 3600


def _draw_star(draw: ImageDraw.ImageDraw, x: float, y: float, r: int, fill):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    panel_box,
    points: list[tuple[datetime, float]],
    meal_times: list[datetime],
    title: str,
    marker_color,
    font_title,
    font_small,
):
    x0, y0, x1, y1 = panel_box
    ml, mr, mt, mb = 80, 20, 60, 60
    ax0, ay0, ax1, ay1 = x0 + ml, y0 + mt, x1 - mr, y1 - mb

    draw.rectangle([ax0, ay0, ax1, ay1], outline=(160, 160, 160), width=2)
    draw.text((x0 + 10, y0 + 10), title, fill=(0, 0, 0), font=font_title)

    if not points:
        draw.text((ax0 + 10, ay0 + 10), 'No glucose data', fill=(120, 120, 120), font=font_small)
        return

    groups = defaultdict(list)
    for ts, g in points:
        groups[ts.date()].append((ts, g))
    for d in groups:
        groups[d].sort(key=lambda x: x[0])

    all_g = [g for _, g in points]
    y_min = min(all_g)
    y_max = max(all_g)
    pad = max(0.5, (y_max - y_min) * 0.1)
    y_low = y_min - pad
    y_high = y_max + pad

    def x_map(hour):
        return ax0 + (hour / 24.0) * (ax1 - ax0)

    def y_map(g):
        if y_high == y_low:
            return (ay0 + ay1) / 2
        return ay0 + (y_high - g) / (y_high - y_low) * (ay1 - ay0)

    for h in range(0, 25, 2):
        x = x_map(h)
        c = (230, 230, 230) if h % 6 else (210, 210, 210)
        draw.line([(x, ay0), (x, ay1)], fill=c, width=1)
        draw.text((x - 8, ay1 + 8), str(h), fill=(70, 70, 70), font=font_small)

    for i in range(7):
        gy = y_low + i * (y_high - y_low) / 6
        y = y_map(gy)
        draw.line([(ax0, y), (ax1, y)], fill=(235, 235, 235), width=1)

    palette = [
        (52, 107, 169),
        (57, 159, 89),
        (203, 125, 46),
        (153, 93, 170),
        (102, 133, 188),
    ]
    max_line_gap_min = 20.0
    for idx, day in enumerate(sorted(groups)):
        day_pts = groups[day]
        if len(day_pts) < 2:
            continue
        c = palette[idx % len(palette)]
        # Draw only contiguous segments to avoid bridging large data gaps.
        segment = [day_pts[0]]
        for i in range(1, len(day_pts)):
            prev_ts = day_pts[i - 1][0]
            cur_ts = day_pts[i][0]
            gap_min = (cur_ts - prev_ts).total_seconds() / 60.0
            if gap_min > max_line_gap_min:
                if len(segment) >= 2:
                    draw.line([(x_map(_hour_of_day(ts)), y_map(g)) for ts, g in segment], fill=c, width=2)
                segment = [day_pts[i]]
            else:
                segment.append(day_pts[i])
        if len(segment) >= 2:
            draw.line([(x_map(_hour_of_day(ts)), y_map(g)) for ts, g in segment], fill=c, width=2)

    # marker placement: interpolate y from same day's curve.
    marker_cnt = 0
    for m_ts in meal_times:
        day_pts = groups.get(m_ts.date())
        if not day_pts:
            continue
        g = _interp_glucose(
            day_pts,
            m_ts,
            allow_extrapolation=False,
            max_neighbor_gap_min=max_line_gap_min,
        )
        if g is None:
            continue
        x = x_map(_hour_of_day(m_ts))
        y = y_map(g)
        _draw_star(draw, x, y, r=10, fill=marker_color)
        marker_cnt += 1

    draw.text((ax0, ay0 - 26), f'days={len(groups)}  markers={marker_cnt}', fill=(60, 60, 60), font=font_small)


def draw_compare_plot(user_id: str, points: list[tuple[datetime, float]], corrected_rows: list[dict]):
    # High resolution output.
    w, h = 3600, 2000
    img = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_title = _load_font(44)
    font_sub = _load_font(28)
    font_small = _load_font(22)

    draw.text((80, 28), f'{user_id} meal-time correction compare', fill=(0, 0, 0), font=font_title)
    draw.text((80, 88), 'left: original meal markers (red)   right: corrected meal markers (green)', fill=(60, 60, 60), font=font_sub)

    panel_top = 160
    margin = 70
    mid_gap = 50
    panel_w = (w - margin * 2 - mid_gap) // 2
    panel_h = h - panel_top - 80

    left_box = (margin, panel_top, margin + panel_w, panel_top + panel_h)
    right_box = (margin + panel_w + mid_gap, panel_top, margin + panel_w + mid_gap + panel_w, panel_top + panel_h)

    raw_meals = [r['raw_ts'] for r in corrected_rows]
    corrected_meals = [r['corrected_ts'] for r in corrected_rows]

    _draw_panel(draw, left_box, points, raw_meals, 'Original', (220, 30, 30), font_sub, font_small)
    _draw_panel(draw, right_box, points, corrected_meals, 'Corrected', (20, 150, 60), font_sub, font_small)

    shift_vals = [abs((r['corrected_ts'] - r['raw_ts']).total_seconds()) / 60.0 for r in corrected_rows]
    shifted = sum(1 for v in shift_vals if v >= 5)
    median_shift = statistics.median(shift_vals) if shift_vals else 0.0
    draw.text(
        (80, h - 46),
        f'meals={len(corrected_rows)}  shifted(>=5min)={shifted}  median_shift_min={median_shift:.1f}',
        fill=(30, 30, 30),
        font=font_sub,
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f'{user_id}_corrected_compare.png'
    img.save(out)


def main():
    user_points = load_glucose_points_by_user()
    glucose_users = set(user_points.keys())

    meal_rows = load_index_rows(glucose_users)
    by_user = defaultdict(list)
    for r in meal_rows:
        by_user[r.user_id].append(r)

    all_corrected_rows = []
    for user_id in sorted(glucose_users):
        points = user_points.get(user_id, [])
        corrected = correct_user_meals(points, by_user.get(user_id, []))
        all_corrected_rows.extend(corrected)
        draw_compare_plot(user_id, points, corrected)

    all_corrected_rows.sort(key=lambda x: (x['user_id'], x['corrected_ts']))
    write_index_corrected(all_corrected_rows)

    shifted = sum(
        1
        for r in all_corrected_rows
        if abs((r['corrected_ts'] - r['raw_ts']).total_seconds()) >= 300
    )
    total = len(all_corrected_rows)

    print(f'index_corrected={INDEX_CORRECTED_CSV}')
    print(f'plots_dir={RAW_DIR}')
    print(f'users={len(glucose_users)}')
    print(f'meals_total={total}')
    print(f'meals_shifted_ge_5min={shifted}')


if __name__ == '__main__':
    main()
