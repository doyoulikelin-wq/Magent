import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/Users/linlin/Desktop/V0')
DATA_DIR = ROOT / 'data'
GLUCOSE_DIR = DATA_DIR / 'glucose'
ACTIVITY_FOOD_CSV = DATA_DIR / 'activity_food.csv'
INDEX_CSV = DATA_DIR / 'index.csv'
RAW_DIR = DATA_DIR / 'raw'

USER_RE = re.compile(r'(SC\d{3})')


def load_glucose_users_and_points():
    user_points = {}
    glucose_files = sorted(GLUCOSE_DIR.glob('Clarity_Export_SC*.csv'))

    for file_path in glucose_files:
        m = USER_RE.search(file_path.name)
        if not m:
            continue
        user_id = m.group(1)

        points = []
        with file_path.open('r', encoding='utf-8-sig', newline='') as f:
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
                    glucose = float(g_raw)
                except ValueError:
                    continue
                points.append((ts, glucose))

        points.sort(key=lambda x: x[0])
        user_points[user_id] = points

    return user_points


def load_food_rows(glucose_users):
    rows = []
    with ACTIVITY_FOOD_CSV.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_raw = (row.get('user_id') or '').strip()
            m = USER_RE.search(user_raw)
            if not m:
                continue
            user_id = m.group(1)
            if user_id not in glucose_users:
                continue

            ts_raw = (row.get('created_timestamp') or '').strip()
            cal_raw = (row.get('total_calories') or '').strip()
            if not ts_raw or not cal_raw:
                continue

            try:
                ts = datetime.strptime(ts_raw, '%d-%m-%Y %I:%M %p')
                calories = float(cal_raw)
            except ValueError:
                continue

            rows.append((user_id, ts, calories))

    rows.sort(key=lambda x: (x[0], x[1]))
    return rows


def write_index_csv(rows):
    with INDEX_CSV.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SCxxx', 'timestamp', 'calories'])
        for user_id, ts, calories in rows:
            cal_out = int(calories) if calories.is_integer() else round(calories, 2)
            writer.writerow([user_id, ts.strftime('%Y-%m-%d %H:%M:%S'), cal_out])


def _hour_of_day(dt):
    return dt.hour + dt.minute / 60.0 + dt.second / 3600.0


def _draw_star(draw, x, y, r=8, fill=(220, 30, 30)):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(angle), y + rr * math.sin(angle)))
    draw.polygon(pts, fill=fill)


def _interp_y(meal_ts, day_points):
    if not day_points:
        return None

    ts_list = [p[0] for p in day_points]
    y_list = [p[1] for p in day_points]

    if meal_ts <= ts_list[0]:
        return y_list[0]
    if meal_ts >= ts_list[-1]:
        return y_list[-1]

    for i in range(1, len(ts_list)):
        left_t = ts_list[i - 1]
        right_t = ts_list[i]
        if left_t <= meal_ts <= right_t:
            left_y = y_list[i - 1]
            right_y = y_list[i]
            span = (right_t - left_t).total_seconds()
            if span <= 0:
                return left_y
            ratio = (meal_ts - left_t).total_seconds() / span
            return left_y + (right_y - left_y) * ratio

    return y_list[-1]


def draw_user_plot(user_id, points, meals):
    w, h = 1600, 900
    ml, mr, mt, mb = 90, 30, 70, 80

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.rectangle([ml, mt, w - mr, h - mb], outline=(180, 180, 180), width=2)

    if not points:
        draw.text((ml, mt - 35), f'{user_id} raw glucose curve', fill=(0, 0, 0), font=font)
        draw.text((ml + 10, mt + 10), 'No glucose data', fill=(120, 120, 120), font=font)
        img.save(RAW_DIR / f'{user_id}_raw.png')
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
        return ml + (hour / 24.0) * (w - ml - mr)

    def y_map(glucose):
        return mt + (y_high - glucose) / (y_high - y_low) * (h - mt - mb)

    for hour in range(0, 25, 2):
        x = x_map(hour)
        color = (225, 225, 225) if hour % 6 else (205, 205, 205)
        draw.line([(x, mt), (x, h - mb)], fill=color, width=1)
        draw.text((x - 10, h - mb + 8), str(hour), fill=(80, 80, 80), font=font)

    for i in range(7):
        gy = y_low + i * (y_high - y_low) / 6
        y = y_map(gy)
        draw.line([(ml, y), (w - mr, y)], fill=(232, 232, 232), width=1)
        draw.text((12, y - 6), f'{gy:.1f}', fill=(80, 80, 80), font=font)

    palette = [
        (31, 119, 180),
        (44, 160, 44),
        (255, 127, 14),
        (148, 103, 189),
        (140, 86, 75),
        (23, 190, 207),
    ]

    for idx, day in enumerate(sorted(groups)):
        day_points = groups[day]
        if len(day_points) < 2:
            continue
        c = palette[idx % len(palette)]
        line_color = tuple(int(0.7 * x + 0.3 * 255) for x in c)

        xy = [(x_map(_hour_of_day(ts)), y_map(g)) for ts, g in day_points]
        draw.line(xy, fill=line_color, width=2)

    meal_count = 0
    for meal_ts, _cal in meals:
        day_points = groups.get(meal_ts.date())
        if not day_points:
            continue
        g = _interp_y(meal_ts, day_points)
        if g is None:
            continue
        x = x_map(_hour_of_day(meal_ts))
        y = y_map(g)
        _draw_star(draw, x, y, r=8, fill=(220, 30, 30))
        meal_count += 1

    draw.text((ml, 20), f'{user_id} raw glucose curves by day (x: 24h)', fill=(0, 0, 0), font=font)
    draw.text((ml, 40), f'days={len(groups)}, glucose_points={len(points)}, meal_markers={meal_count}', fill=(60, 60, 60), font=font)
    draw.text((w - 220, mt - 22), 'red star = meal time', fill=(180, 30, 30), font=font)
    draw.text((ml, h - 24), 'hour of day', fill=(0, 0, 0), font=font)

    img.save(RAW_DIR / f'{user_id}_raw.png')


def main():
    user_points = load_glucose_users_and_points()
    glucose_users = set(user_points.keys())

    food_rows = load_food_rows(glucose_users)
    write_index_csv(food_rows)

    meals_by_user = defaultdict(list)
    for user_id, ts, calories in food_rows:
        meals_by_user[user_id].append((ts, calories))

    for user_id in sorted(glucose_users):
        draw_user_plot(user_id, user_points.get(user_id, []), meals_by_user.get(user_id, []))

    print(f'index_csv={INDEX_CSV}')
    print(f'plots_dir={RAW_DIR}')
    print(f'users={len(glucose_users)}')
    print(f'food_rows={len(food_rows)}')


if __name__ == '__main__':
    main()
