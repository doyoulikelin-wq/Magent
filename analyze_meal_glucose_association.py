import csv
import math
import re
import statistics
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/Users/linlin/Desktop/V0')
DATA_DIR = ROOT / 'data'
GLUCOSE_DIR = DATA_DIR / 'glucose'
INDEX_ONCURVE = DATA_DIR / 'index_corrected_oncurve.csv'
FEATURES_CSV = DATA_DIR / 'meal_glucose_response_features.csv'
SUMMARY_TXT = DATA_DIR / 'meal_glucose_association_summary.txt'
SUMMARY_HOUR_CSV = DATA_DIR / 'meal_glucose_association_by_hour.csv'
SUMMARY_CAL_CSV = DATA_DIR / 'meal_glucose_association_by_calories.csv'

USER_RE = re.compile(r'(SC\d{3})')


@dataclass
class MealEvent:
    user_id: str
    timestamp: datetime
    calories: float


@dataclass
class MealFeature:
    user_id: str
    timestamp: datetime
    hour: float
    calories: float
    baseline: float
    g0: float
    peak: float
    delta_peak: float
    ttp_min: float
    auc_0_120: float
    slope_pre_30: float
    slope_0_30: float



def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-12 or vy <= 1e-12:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(vx * vy)



def load_glucose_points_by_user():
    out = {}
    for fp in sorted(GLUCOSE_DIR.glob('Clarity_Export_SC*.csv')):
        m = USER_RE.search(fp.name)
        if not m:
            continue
        uid = m.group(1)
        pts = []
        with fp.open('r', encoding='utf-8-sig', newline='') as f:
            r = csv.DictReader(f)
            for row in r:
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
                pts.append((ts, g))
        pts.sort(key=lambda x: x[0])
        out[uid] = pts
    return out



def load_meals():
    events = []
    with INDEX_ONCURVE.open('r', encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            uid = (row.get('SCxxx') or '').strip()
            ts_raw = (row.get('timestamp') or '').strip()
            cal_raw = (row.get('calories') or '').strip()
            if not uid or not ts_raw or not cal_raw:
                continue
            try:
                ts = datetime.strptime(ts_raw, '%Y-%m-%d %H:%M:%S')
                calories = float(cal_raw)
            except ValueError:
                continue
            events.append(MealEvent(user_id=uid, timestamp=ts, calories=calories))
    events.sort(key=lambda x: (x.user_id, x.timestamp))
    return events



def merge_close_events(events, merge_window_min=20):
    by_user = defaultdict(list)
    for e in events:
        by_user[e.user_id].append(e)

    merged = []
    window = timedelta(minutes=merge_window_min)

    for uid, rows in by_user.items():
        rows.sort(key=lambda x: x.timestamp)
        cur_ts = None
        cur_cal = 0.0

        for e in rows:
            if cur_ts is None:
                cur_ts = e.timestamp
                cur_cal = e.calories
                continue

            if e.timestamp - cur_ts <= window:
                cur_cal += e.calories
            else:
                merged.append(MealEvent(uid, cur_ts, cur_cal))
                cur_ts = e.timestamp
                cur_cal = e.calories

        if cur_ts is not None:
            merged.append(MealEvent(uid, cur_ts, cur_cal))

    merged.sort(key=lambda x: (x.user_id, x.timestamp))
    return merged



def _interp(points, t):
    if not points:
        return None
    ts = [x[0] for x in points]
    i = bisect_left(ts, t)
    if i <= 0 or i >= len(points):
        return None
    t0, g0 = points[i - 1]
    t1, g1 = points[i]
    span = (t1 - t0).total_seconds()
    if span <= 0:
        return g0
    ratio = (t - t0).total_seconds() / span
    return g0 + (g1 - g0) * ratio



def _window_values(points, t0, t1):
    return [(t, g) for t, g in points if t0 <= t <= t1]



def _auc_above_baseline(points, meal_ts, baseline):
    t_start = meal_ts
    t_end = meal_ts + timedelta(minutes=120)
    vals = _window_values(points, t_start, t_end)

    if len(vals) < 2:
        return None

    auc = 0.0
    prev_t, prev_g = vals[0]
    for t, g in vals[1:]:
        dt = (t - prev_t).total_seconds() / 60.0
        if dt <= 0 or dt > 20:
            prev_t, prev_g = t, g
            continue
        y0 = max(prev_g - baseline, 0.0)
        y1 = max(g - baseline, 0.0)
        auc += (y0 + y1) * 0.5 * dt
        prev_t, prev_g = t, g
    return auc



def compute_features(points_by_user, events):
    features = []

    for e in events:
        pts = points_by_user.get(e.user_id, [])
        if len(pts) < 10:
            continue

        pre = _window_values(pts, e.timestamp - timedelta(minutes=40), e.timestamp - timedelta(minutes=5))
        post = _window_values(pts, e.timestamp + timedelta(minutes=10), e.timestamp + timedelta(minutes=120))
        if len(pre) < 3 or len(post) < 3:
            continue

        g0 = _interp(pts, e.timestamp)
        g_pre30 = _interp(pts, e.timestamp - timedelta(minutes=30))
        g_30 = _interp(pts, e.timestamp + timedelta(minutes=30))
        if g0 is None or g_pre30 is None or g_30 is None:
            continue

        baseline = statistics.median([g for _, g in pre])

        peak_ts, peak_val = max(post, key=lambda x: x[1])
        delta_peak = peak_val - baseline
        ttp_min = (peak_ts - e.timestamp).total_seconds() / 60.0

        auc = _auc_above_baseline(pts, e.timestamp, baseline)
        if auc is None:
            continue

        hour = e.timestamp.hour + e.timestamp.minute / 60.0 + e.timestamp.second / 3600.0
        slope_pre_30 = (g0 - g_pre30) / 30.0
        slope_0_30 = (g_30 - g0) / 30.0

        features.append(
            MealFeature(
                user_id=e.user_id,
                timestamp=e.timestamp,
                hour=hour,
                calories=e.calories,
                baseline=baseline,
                g0=g0,
                peak=peak_val,
                delta_peak=delta_peak,
                ttp_min=ttp_min,
                auc_0_120=auc,
                slope_pre_30=slope_pre_30,
                slope_0_30=slope_0_30,
            )
        )

    return features



def write_features(features):
    with FEATURES_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'SCxxx',
            'timestamp',
            'hour',
            'calories',
            'baseline_mmol_L',
            'glucose_at_meal_mmol_L',
            'peak_10_120_mmol_L',
            'delta_peak_mmol_L',
            'time_to_peak_min',
            'auc_above_baseline_0_120',
            'slope_pre_30_mmol_L_per_min',
            'slope_0_30_mmol_L_per_min',
        ])
        for x in features:
            w.writerow([
                x.user_id,
                x.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                round(x.hour, 3),
                round(x.calories, 2),
                round(x.baseline, 3),
                round(x.g0, 3),
                round(x.peak, 3),
                round(x.delta_peak, 3),
                round(x.ttp_min, 2),
                round(x.auc_0_120, 3),
                round(x.slope_pre_30, 5),
                round(x.slope_0_30, 5),
            ])



def summarize_by_bins(features):
    hour_bins = [
        ('00-06', 0, 6),
        ('06-10', 6, 10),
        ('10-14', 10, 14),
        ('14-18', 14, 18),
        ('18-22', 18, 22),
        ('22-24', 22, 24),
    ]
    cal_bins = [
        ('<300', -1, 300),
        ('300-600', 300, 600),
        ('600-900', 600, 900),
        ('>=900', 900, 1e9),
    ]

    hour_rows = []
    for label, lo, hi in hour_bins:
        rows = [x for x in features if lo <= x.hour < hi]
        if not rows:
            continue
        hour_rows.append(
            {
                'bin': label,
                'n': len(rows),
                'delta_peak_mean': statistics.mean(x.delta_peak for x in rows),
                'delta_peak_median': statistics.median(x.delta_peak for x in rows),
                'auc_mean': statistics.mean(x.auc_0_120 for x in rows),
                'ttp_mean': statistics.mean(x.ttp_min for x in rows),
            }
        )

    cal_rows = []
    for label, lo, hi in cal_bins:
        rows = [x for x in features if lo < x.calories < hi or (label == '>=900' and x.calories >= 900)]
        if not rows:
            continue
        cal_rows.append(
            {
                'bin': label,
                'n': len(rows),
                'delta_peak_mean': statistics.mean(x.delta_peak for x in rows),
                'delta_peak_median': statistics.median(x.delta_peak for x in rows),
                'auc_mean': statistics.mean(x.auc_0_120 for x in rows),
                'ttp_mean': statistics.mean(x.ttp_min for x in rows),
            }
        )

    with SUMMARY_HOUR_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['hour_bin', 'n', 'delta_peak_mean', 'delta_peak_median', 'auc_mean', 'time_to_peak_mean'])
        for r in hour_rows:
            w.writerow([
                r['bin'],
                r['n'],
                round(r['delta_peak_mean'], 4),
                round(r['delta_peak_median'], 4),
                round(r['auc_mean'], 4),
                round(r['ttp_mean'], 2),
            ])

    with SUMMARY_CAL_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['calorie_bin', 'n', 'delta_peak_mean', 'delta_peak_median', 'auc_mean', 'time_to_peak_mean'])
        for r in cal_rows:
            w.writerow([
                r['bin'],
                r['n'],
                round(r['delta_peak_mean'], 4),
                round(r['delta_peak_median'], 4),
                round(r['auc_mean'], 4),
                round(r['ttp_mean'], 2),
            ])

    return hour_rows, cal_rows



def main():
    points_by_user = load_glucose_points_by_user()
    raw_events = load_meals()
    merged_events = merge_close_events(raw_events, merge_window_min=20)

    features = compute_features(points_by_user, merged_events)
    write_features(features)

    if not features:
        raise RuntimeError('No usable features computed')

    hours = [x.hour for x in features]
    calories = [x.calories for x in features]
    delta = [x.delta_peak for x in features]
    auc = [x.auc_0_120 for x in features]
    ttp = [x.ttp_min for x in features]

    # overall correlations
    corr_hour_delta = pearson(hours, delta)
    corr_cal_delta = pearson(calories, delta)
    corr_hour_auc = pearson(hours, auc)
    corr_cal_auc = pearson(calories, auc)

    # within-user de-meaned correlations (controls user baseline differences)
    by_user = defaultdict(list)
    for x in features:
        by_user[x.user_id].append(x)

    h_dm = []
    c_dm = []
    d_dm = []
    a_dm = []
    t_dm = []

    per_user_cal_corr = []
    per_user_hour_corr = []

    for uid, rows in by_user.items():
        if len(rows) < 8:
            continue
        mh = statistics.mean(r.hour for r in rows)
        mc = statistics.mean(r.calories for r in rows)
        md = statistics.mean(r.delta_peak for r in rows)
        ma = statistics.mean(r.auc_0_120 for r in rows)
        mt = statistics.mean(r.ttp_min for r in rows)

        ux = [r.calories for r in rows]
        uh = [r.hour for r in rows]
        ud = [r.delta_peak for r in rows]

        c1 = pearson(ux, ud)
        c2 = pearson(uh, ud)
        if c1 is not None:
            per_user_cal_corr.append(c1)
        if c2 is not None:
            per_user_hour_corr.append(c2)

        for r in rows:
            h_dm.append(r.hour - mh)
            c_dm.append(r.calories - mc)
            d_dm.append(r.delta_peak - md)
            a_dm.append(r.auc_0_120 - ma)
            t_dm.append(r.ttp_min - mt)

    corr_hour_delta_dm = pearson(h_dm, d_dm)
    corr_cal_delta_dm = pearson(c_dm, d_dm)
    corr_hour_auc_dm = pearson(h_dm, a_dm)
    corr_cal_auc_dm = pearson(c_dm, a_dm)

    hour_rows, cal_rows = summarize_by_bins(features)

    late = [x for x in features if x.hour >= 20 or x.hour < 6]
    daytime = [x for x in features if 10 <= x.hour < 18]

    with SUMMARY_TXT.open('w', encoding='utf-8') as f:
        f.write('Meal time vs glucose dynamics association summary\n')
        f.write('=================================================\n')
        f.write(f'usable_events={len(features)}\n')
        f.write(f'users={len(set(x.user_id for x in features))}\n')
        f.write(f'mean_delta_peak_mmol_L={statistics.mean(delta):.4f}\n')
        f.write(f'median_delta_peak_mmol_L={statistics.median(delta):.4f}\n')
        f.write(f'mean_auc_0_120={statistics.mean(auc):.4f}\n')
        f.write(f'mean_time_to_peak_min={statistics.mean(ttp):.2f}\n\n')

        f.write('Overall correlations\n')
        f.write('--------------------\n')
        f.write(f'corr(hour, delta_peak)={corr_hour_delta}\n')
        f.write(f'corr(calories, delta_peak)={corr_cal_delta}\n')
        f.write(f'corr(hour, auc)={corr_hour_auc}\n')
        f.write(f'corr(calories, auc)={corr_cal_auc}\n\n')

        f.write('Within-user de-meaned correlations\n')
        f.write('-----------------------------------\n')
        f.write(f'corr(hour_dm, delta_peak_dm)={corr_hour_delta_dm}\n')
        f.write(f'corr(calories_dm, delta_peak_dm)={corr_cal_delta_dm}\n')
        f.write(f'corr(hour_dm, auc_dm)={corr_hour_auc_dm}\n')
        f.write(f'corr(calories_dm, auc_dm)={corr_cal_auc_dm}\n\n')

        if per_user_cal_corr:
            f.write(f'per_user_corr(calories,delta) median={statistics.median(per_user_cal_corr):.4f} n={len(per_user_cal_corr)}\n')
        if per_user_hour_corr:
            f.write(f'per_user_corr(hour,delta) median={statistics.median(per_user_hour_corr):.4f} n={len(per_user_hour_corr)}\n')

        f.write('\nDaypart compare\n')
        f.write('--------------\n')
        if late:
            f.write(f'late(20-24 or 00-06) n={len(late)} mean_delta={statistics.mean(x.delta_peak for x in late):.4f} mean_auc={statistics.mean(x.auc_0_120 for x in late):.4f}\n')
        if daytime:
            f.write(f'daytime(10-18) n={len(daytime)} mean_delta={statistics.mean(x.delta_peak for x in daytime):.4f} mean_auc={statistics.mean(x.auc_0_120 for x in daytime):.4f}\n')

    print(f'features_csv={FEATURES_CSV}')
    print(f'summary_txt={SUMMARY_TXT}')
    print(f'hour_csv={SUMMARY_HOUR_CSV}')
    print(f'cal_csv={SUMMARY_CAL_CSV}')
    print(f'usable_events={len(features)}')


if __name__ == '__main__':
    main()
