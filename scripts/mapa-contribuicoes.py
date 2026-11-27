"""Renderiza a carta náutica estática e animada a partir do calendário público."""

import calendar
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SIZE = (456, 116)
WATER = (8, 27, 49)
GOLD = (245, 196, 109)
LEVELS = [(16, 47, 73), (26, 103, 135), (48, 152, 176), (95, 214, 208), GOLD]
MONTHS = ("", "JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")
SHIP = (
    ".......G.......", ".......GGG.....", ".......G.......", "......WW.......",
    ".....WWW.W.....", "....WWWW.WW....", "...WWWWW.WWW...", ".......G.......",
    ".GGGGGGGGGGGGG.", "..BBBBBBBBBBB..", "...BBBBBBBBB...", "...TTTTTTT.....",
)


def pixel_ship(draw, x, y, mirror=False):
    colors = {"G": GOLD, "W": (255, 237, 185), "B": (157, 93, 53), "T": (63, 207, 220)}
    draw.rectangle((x - 8, y - 7, x + 8, y + 6), fill=WATER)
    for j, row in enumerate(SHIP):
        for i, pixel in enumerate(row[::-1] if mirror else row):
            if pixel in colors:
                draw.point((x + i - 7, y + j - 6), fill=colors[pixel])


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
    draw.rectangle((3, 3, 452, 112), outline="#276180")
    draw.rectangle((9, 9, 446, 106), outline="#163d5b")
    for x in (3, 448):
        for y in (3, 108):
            draw.rectangle((x, y, x + 4, y + 4), fill=GOLD)
    draw.text((18, 11), "CARTA DO OCEANO", fill=GOLD, font_size=12)
    draw.text((438, 12), "MAPA DO GITHUB", fill="#75c8df", anchor="ra", font_size=10)
    draw.line((18, 27, 438, 27), fill="#2d5b73")

    cols = ((last - first).days // 7) + 1
    start_x = (SIZE[0] - 8 * cols) // 2
    targets = {}
    last_month_label = -8
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        col, row = divmod(offset, 7)
        x, y = start_x + 8 * col, 39 + 7 * row
        if day.day <= 7 and row == 0 and col - last_month_label >= 5:
            draw.text((x, 29), MONTHS[day.month], fill="#a1c5d4", font_size=9)
            last_month_label = col
        level, _ = activity.get(day, (0, 0))
        draw.rectangle((x, y, x + 5, y + 4), fill=LEVELS[level])
        if level:
            targets.setdefault(col, []).append((x + 2, y + 2))

    draw.text((18, 91), "MENOS", fill="#a1c5d4", font_size=10)
    for index, color in enumerate(LEVELS):
        draw.rectangle((59 + index * 8, 94, 64 + index * 8, 99), fill=color)
    draw.text((102, 91), "MAIS", fill="#a1c5d4", font_size=10)
    draw.text((438, 91), f"TOTAL {sum(count for _, count in activity.values())}",
              fill=GOLD, font_size=10, anchor="ra")
    stops = [(start_x - 3, 62)]
    for col, points in targets.items():
        stops.extend(points if col % 2 == 0 else reversed(points))
    stops.append((start_x + 8 * (cols - 1) + 5, 66))
    return image, stops


def render(source):
    base, stops = chart(source)
    scale = (SIZE[0] * 2, SIZE[1] * 2)
    lengths = [0]
    for before, after in zip(stops, stops[1:]):
        lengths.append(lengths[-1] + math.dist(before, after))

    def frame(distance):
        end = next(i for i in range(1, len(stops)) if lengths[i] >= distance)
        ratio = (distance - lengths[end - 1]) / (lengths[end] - lengths[end - 1])
        x, y = [round(a + (b - a) * ratio) for a, b in zip(stops[end - 1], stops[end])]
        image = base.copy()
        pixel_ship(ImageDraw.Draw(image), x, y)
        return image.resize(scale, Image.Resampling.NEAREST)

    frame(0).save(ASSETS / "carta-nautica.png", optimize=True)
    frames = [frame(lengths[-1] * i / 107) for i in range(108)]
    frames[0].save(ASSETS / "carta-nautica.gif", save_all=True, append_images=frames[1:],
                   duration=[140] * 107 + [900], loop=0, optimize=True)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("contribuicoes.json")
    render(json.loads(path.read_text(encoding="utf-8")))
