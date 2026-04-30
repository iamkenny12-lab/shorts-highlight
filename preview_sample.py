"""쇼츠 레이아웃 미리보기 샘플 생성"""
from PIL import Image, ImageDraw, ImageFont
import os
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(BASE, "fonts", "Pretendard-Bold.otf")

W, H = 1080, 1920
MAIN_H = 960
MAIN_TOP = (H - MAIN_H) // 2  # 480
MAIN_BOTTOM = MAIN_TOP + MAIN_H  # 1440

DEFAULT_COLOR = (255, 255, 255)

NAMED_COLORS = {
    "white": (255, 255, 255),
    "yellow": (255, 230, 0),
    "orange": (255, 120, 0),
    "red": (255, 60, 60),
    "green": (60, 220, 120),
    "blue": (80, 160, 255),
}


def parse_highlights(spec):
    result = {}
    if not spec:
        return result
    for item in spec.split(","):
        if ":" not in item:
            continue
        word, color = item.split(":", 1)
        if word.strip() and color.strip().lower() in NAMED_COLORS:
            result[word.strip()] = NAMED_COLORS[color.strip().lower()]
    return result


def split_by_highlight(text, highlights):
    keywords = sorted(highlights.keys(), key=len, reverse=True)
    tokens = [(text, None)]
    for kw in keywords:
        new_tokens = []
        for seg, color in tokens:
            if color is not None:
                new_tokens.append((seg, color))
                continue
            parts = seg.split(kw)
            for i, part in enumerate(parts):
                if part:
                    new_tokens.append((part, None))
                if i < len(parts) - 1:
                    new_tokens.append((kw, highlights[kw]))
        tokens = new_tokens
    return [(t, c if c is not None else DEFAULT_COLOR) for t, c in tokens]


def draw_line_centered(draw, line, font, y, canvas_w, highlights, stroke_w=6):
    tokens = split_by_highlight(line, highlights)
    widths = [draw.textlength(t, font=font) for t, _ in tokens]
    total_w = sum(widths)
    x = (canvas_w - total_w) / 2
    for (text, color), w in zip(tokens, widths):
        draw.text((x, y), text, font=font, fill=color, stroke_width=stroke_w, stroke_fill=(0, 0, 0))
        x += w


def make_sample(top_lines, bottom_text, highlights, out_path,
                top_font_sizes=(140, 100), bottom_font_size=64,
                top_valign="center", bottom_valign="top",
                top_padding=20, bottom_padding=40):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 영상 영역 mock
    draw.rectangle([0, MAIN_TOP, W, MAIN_BOTTOM], fill=(60, 70, 90))
    info_font = ImageFont.truetype(FONT, 50)
    info_text = "[ 영상 영역 ]"
    tw = draw.textlength(info_text, font=info_font)
    draw.text(((W - tw) / 2, MAIN_TOP + MAIN_H / 2 - 25), info_text,
              font=info_font, fill=(150, 160, 180))

    # 위쪽 텍스트
    sizes = list(top_font_sizes)
    while len(sizes) < len(top_lines):
        sizes.append(sizes[-1])
    sizes = sizes[:len(top_lines)]
    fonts = [ImageFont.truetype(FONT, s) for s in sizes]
    line_heights = [s + 20 for s in sizes]
    total_h = sum(line_heights)

    if top_valign == "top":
        start_y = top_padding
    elif top_valign == "bottom":
        start_y = MAIN_TOP - total_h - top_padding
    else:  # center
        start_y = (MAIN_TOP - total_h) / 2

    y = start_y
    for line, font, lh in zip(top_lines, fonts, line_heights):
        draw_line_centered(draw, line, font, y, W, highlights)
        y += lh

    # 아래쪽 텍스트
    if bottom_text:
        bottom_font = ImageFont.truetype(FONT, bottom_font_size)
        line_h = bottom_font_size + 20
        bottom_area_h = H - MAIN_BOTTOM
        if bottom_valign == "top":
            by = MAIN_BOTTOM + bottom_padding
        elif bottom_valign == "bottom":
            by = H - line_h - bottom_padding
        else:  # center
            by = MAIN_BOTTOM + (bottom_area_h - line_h) / 2
        draw_line_centered(draw, bottom_text, bottom_font, by, W, highlights, stroke_w=4)

    img.save(out_path, quality=92)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--top", required=True, help="상단 텍스트 (\\n 구분)")
    p.add_argument("--bottom", default="", help="하단 텍스트")
    p.add_argument("--highlight", default="", help="단어 강조 (예: '정민철:yellow,염종석:orange')")
    p.add_argument("--top-sizes", default="140,100")
    p.add_argument("--bottom-size", type=int, default=64)
    p.add_argument("--top-valign", default="center", choices=["top", "center", "bottom"])
    p.add_argument("--bottom-valign", default="top", choices=["top", "center", "bottom"])
    p.add_argument("--out", default="output/sample.jpg")
    args = p.parse_args()

    top_lines = args.top.split("\\n")
    sizes = tuple(int(x) for x in args.top_sizes.split(","))
    out_path = args.out if os.path.isabs(args.out) else os.path.join(BASE, args.out)
    make_sample(
        top_lines=top_lines,
        bottom_text=args.bottom,
        highlights=parse_highlights(args.highlight),
        out_path=out_path,
        top_font_sizes=sizes,
        bottom_font_size=args.bottom_size,
        top_valign=args.top_valign,
        bottom_valign=args.bottom_valign,
    )
