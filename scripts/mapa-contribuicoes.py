"""Transforma os dias ativos recentes do calendário público em pontos da rota."""

import calendar
import json
import math
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SIZE = (456, 128)
WATER = (8, 27, 49)
GOLD = (245, 196, 109)
LEVELS = [(45, 116, 153), (63, 170, 187), (109, 222, 210), GOLD]
HEIGHTS = (59, 78, 51, 68, 43, 59, 80, 52, 69)
TREASURE_ROWS = (0, 3, 6, 1, 5, 2, 4)
FRAMES = 210
SHIP = (
    ".......G.......", ".......GGG.....", ".......G.......", "......WW.......",
    ".....WWW.W.....", "....WWWW.WW....", "...WWWWW.WWW...", ".......G.......",
    ".GGGGGGGGGGGGG.", "..BBBBBBBBBBB..", "...BBBBBBBBB...", "...TTTTTTT.....",
)


def pixel_ship(draw, x, y):
    colors = {"G": GOLD, "W": (255, 237, 185), "B": (157, 93, 53), "T": (63, 207, 220)}
    for j, row in enumerate(SHIP):
        for i, pixel in enumerate(row):
            if pixel in colors:
                draw.point((x + i - 7, y + j - 6), fill=colors[pixel])


def treasure_route(waypoints, requested):
    gaps = [i for i, (a, b) in enumerate(zip(waypoints, waypoints[1:])) if b[0] - a[0] >= 34]
    count = min(requested, len(gaps) * len(TREASURE_ROWS))
    stops = [waypoints[0]]
    treasures = []
    if not count:
        return waypoints, treasures
    per_gap, remainder = divmod(count, len(gaps))
    for i, (left, right) in enumerate(zip(waypoints, waypoints[1:])):
        if i in gaps:
            gap = gaps.index(i)
            center = (left[0] + right[0]) // 2
            rows = sorted(TREASURE_ROWS[:per_gap + (gap < remainder)], reverse=gap % 2 == 1)
            for row in rows:
                x = center + 3 * ((row * 3 + gap) % 5 - 2)
                y = 36 + row * 9 + (gap % 3 - 1) * 2
                treasures.append(len(stops))
                stops.append((x, y))
        stops.append(right)
    return stops, treasures


def chart(source):
    first, last = (date.fromisoformat(source[key]) for key in ("inicio", "fim"))
    activity = {date.fromisoformat(day): (level, count) for day, level, count in source["dias_ativos"]}
    if not 360 <= (last - first).days <= 371 or first.weekday() != calendar.SUNDAY:
        raise ValueError("O intervalo deve começar no domingo e cobrir o calendário anual do GitHub.")
    if any(not (first <= day <= last and 1 <= level <= 4 and count > 0)
           for day, (level, count) in activity.items()):
        raise ValueError("Há um dia de contribuição fora do intervalo ou com dados inválidos.")

    image = Image.new("RGB", SIZE, WATER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((3, 3, 452, 124), outline="#276180")
    draw.rectangle((9, 9, 446, 118), outline="#163d5b")
    for x in (3, 448):
        for y in (3, 120):
            draw.rectangle((x, y, x + 4, y + 4), fill=GOLD)
    draw.text((18, 11), "CARTA DO OCEANO", fill=GOLD, font_size=12)
    draw.text((438, 12), "DIAS COM ATIVIDADE", fill="#75c8df", anchor="ra", font_size=11)
    draw.line((18, 27, 438, 27), fill="#2d5b73")
    draw.line((18, 101, 438, 101), fill="#2d5b73")
    for x in range(27, 438, 16):
        for y in range(34, 100, 9):
            draw.point((x, y), fill="#21455e")
    for x, y in ((101, 39), (163, 91), (282, 34), (351, 89)):
        draw.line((x - 4, y, x + 4, y), fill="#376c83")
        draw.line((x + 2, y + 2, x + 6, y + 2), fill="#21455e")

    days = sorted(activity)[-len(HEIGHTS):]
    positions = [(round(44 + 368 * (i / (len(days) - 1) if len(days) > 1 else .5)), HEIGHTS[i])
                 for i in range(len(days))]
    waypoints = [(18, 70), *positions, (438, 65)]
    for (x1, y1), (x2, y2) in zip(waypoints, waypoints[1:]):
        steps = max(1, round(math.hypot(x2 - x1, y2 - y1) / 4))
        for step in range(steps):
            x = round(x1 + (x2 - x1) * step / steps)
            y = round(y1 + (y2 - y1) * step / steps)
            draw.rectangle((x, y, x + 1, y + 1), fill="#48748c")
    for day, (x, y) in zip(days, positions):
        level, _ = activity[day]
        color = LEVELS[level - 1]
        draw.rectangle((x - 5, y - 5, x + 5, y + 5), fill=WATER, outline="#537b8d")
        draw.rectangle((x - 3, y - 3, x + 3, y + 3), fill=color)
        draw.line((x - 2, y - 2, x + 2, y - 2), fill="#e5efde")
        draw.rectangle((x - 17, y + 7, x + 17, y + 19), fill=WATER)
        draw.text((x, y + 8), day.strftime("%d/%m"), fill="#d0e4e9", anchor="ma", font_size=11)

    draw.text((18, 104), "MENOS", fill="#a1c5d4", font_size=10)
    for index, color in enumerate(LEVELS):
        draw.rectangle((59 + index * 8, 107, 64 + index * 8, 112), fill=color)
    draw.text((94, 104), "MAIS", fill="#a1c5d4", font_size=10)
    draw.polygon([(431, 104), (435, 108), (431, 112), (427, 108)], fill=GOLD)
    # A marca datada representa um registro. Os restantes viram pontos de coleta.
    extra = sum(activity[day][1] - 1 for day in days)
    stops, treasures = treasure_route(waypoints, extra)
    return image, stops, treasures


def render(source):
    base, stops, treasures = chart(source)
    scale = (SIZE[0] * 2, SIZE[1] * 2)
    lengths = [0]
    for before, after in zip(stops, stops[1:]):
        lengths.append(lengths[-1] + math.dist(before, after))

    def frame(distance):
        end = next(i for i in range(1, len(stops)) if lengths[i] >= distance)
        ratio = (distance - lengths[end - 1]) / (lengths[end] - lengths[end - 1])
        x, y = [round(a + (b - a) * ratio) for a, b in zip(stops[end - 1], stops[end])]
        image = base.copy()
        draw = ImageDraw.Draw(image)
        for target in treasures:
            t_x, t_y = stops[target]
            if distance < lengths[target]:
                draw.rectangle((t_x - 1, t_y - 1, t_x + 1, t_y + 1), fill="#67cec6")
                draw.point((t_x - 1, t_y - 1), fill="#b5e8d9")
            elif distance - lengths[target] < 7:
                draw.point((t_x - 2, t_y + 1), fill=GOLD)
                draw.point((t_x + 2, t_y - 1), fill=GOLD)
        pixel_ship(draw, x, y)
        return image.resize(scale, Image.Resampling.NEAREST)

    frame(0).save(ASSETS / "carta-nautica.png", optimize=True)
    frames = [frame(lengths[-1] * i / (FRAMES - 1)) for i in range(FRAMES)]
    frames[0].save(ASSETS / "carta-nautica.gif", save_all=True, append_images=frames[1:],
                   duration=[100] * (FRAMES - 1) + [900], loop=0, optimize=True)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("contribuicoes.json")
    render(json.loads(path.read_text(encoding="utf-8")))
