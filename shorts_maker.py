"""
KBO Shorts Maker - KBO 하이라이트 영상에서 자동으로 쇼츠를 생성하고 YouTube에 업로드합니다.

Usage:
    python shorts_maker.py <youtube_url>
    python shorts_maker.py <youtube_url> --upload
    python shorts_maker.py <youtube_url> --upload --public
    python shorts_maker.py <youtube_url> --start 5:30 --duration 20
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


# ──────────────────────────────────────────────
# 1단계: 영상 다운로드 & 메타데이터 추출
# ──────────────────────────────────────────────

def download_video(url):
    print("[1/4] 영상 다운로드 중...")
    result = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--dump-json", url],
        capture_output=True, encoding="utf-8",
    )
    meta = json.loads(result.stdout)
    title = meta.get("title", "")
    duration = meta.get("duration", 0)

    video_path = os.path.join(OUTPUT_DIR, "source.mp4")
    subprocess.run(
        [sys.executable, "-m", "yt_dlp", "-f", "best[height<=720]",
         "-o", video_path, "--no-warnings", url],
        capture_output=True,
    )
    print(f"  제목: {title}")
    print(f"  길이: {duration // 60}분 {duration % 60}초")
    return video_path, title, duration


def parse_metadata(title):
    """제목에서 팀명, 날짜를 자동 파싱한다."""
    info = {"away": "", "home": "", "date": "", "date_display": ""}

    # 팀명 파싱: [팀A vs 팀B] 또는 팀A vs 팀B
    team_match = re.search(r"\[?\s*(\S+)\s+vs\s+(\S+?)\s*\]", title, re.IGNORECASE)
    if not team_match:
        team_match = re.search(r"(\S+)\s+vs\s+(\S+)", title, re.IGNORECASE)
    if team_match:
        info["away"] = team_match.group(1).strip("[]")
        info["home"] = team_match.group(2).strip("[]")

    # 날짜 파싱: M/D 형식
    date_match = re.search(r"(\d{1,2})/(\d{1,2})", title)
    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        year = datetime.now().year % 100
        info["date"] = f"{year:02d}/{month:02d}/{day:02d}"
        info["date_display"] = f"{month}/{day}"

    return info


# ──────────────────────────────────────────────
# 2단계: 주요 장면 자동 감지
# ──────────────────────────────────────────────

def extract_frames(video_path, interval=2):
    """interval초 간격으로 프레임을 추출한다."""
    frames_dir = os.path.join(OUTPUT_DIR, "frames_analysis")
    os.makedirs(frames_dir, exist_ok=True)

    subprocess.run(
        ["ffmpeg", "-i", video_path, "-vf", f"fps=1/{interval}",
         "-q:v", "2", os.path.join(frames_dir, "f_%04d.jpg"), "-y"],
        capture_output=True,
    )
    frames = sorted(
        [os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith(".jpg")]
    )
    return frames


def compute_scene_scores(frames):
    """프레임 간 변화량을 계산하여 장면 점수를 매긴다."""
    scores = []
    prev = None
    for path in frames:
        img = np.array(Image.open(path).resize((160, 90)))
        if prev is not None:
            diff = np.mean(np.abs(img.astype(float) - prev.astype(float)))
            scores.append(diff)
        else:
            scores.append(0)
        prev = img
    return scores


def find_best_segment(scores, interval=2, clip_duration=20, top_n=1):
    """
    변화량이 큰 구간을 찾는다.
    연속된 clip_duration/interval 프레임의 평균 변화량이 가장 높은 구간을 선택.
    """
    window = clip_duration // interval
    if len(scores) < window:
        return [(0, clip_duration)]

    # 슬라이딩 윈도우로 평균 변화량 계산
    best_segments = []
    for i in range(len(scores) - window):
        avg_score = np.mean(scores[i:i + window])
        best_segments.append((i, avg_score))

    best_segments.sort(key=lambda x: x[1], reverse=True)

    results = []
    used = set()
    for idx, score in best_segments:
        # 이미 선택된 구간과 겹치지 않도록
        if any(abs(idx - u) < window for u in used):
            continue
        start_sec = idx * interval
        results.append((start_sec, clip_duration))
        used.add(idx)
        if len(results) >= top_n:
            break

    return results


def detect_highlight(video_path, clip_duration=20):
    """영상에서 가장 임팩트 있는 구간을 자동 감지한다."""
    print("[2/4] 주요 장면 분석 중...")
    interval = 2
    frames = extract_frames(video_path, interval)
    print(f"  {len(frames)}개 프레임 분석 중...")
    scores = compute_scene_scores(frames)
    segments = find_best_segment(scores, interval, clip_duration)

    if segments:
        start, dur = segments[0]
        m, s = divmod(start, 60)
        print(f"  최적 구간: {m}:{s:02d} ~ {m + (s + dur) // 60}:{(s + dur) % 60:02d}")
        return start, dur

    return 0, clip_duration


# ──────────────────────────────────────────────
# 3단계: 쇼츠 영상 생성
# ──────────────────────────────────────────────

def escape_ffmpeg_text(text):
    """ffmpeg drawtext 필터용 특수문자 이스케이프"""
    for ch in [":", "'", "\\", "[", "]", ";", ","]:
        text = text.replace(ch, f"\\{ch}")
    return text


def generate_shorts(video_path, start_sec, duration, info):
    """세로형 쇼츠 영상을 생성한다."""
    print("[3/4] 쇼츠 생성 중...")

    date_str = info.get("date", "")
    away = info.get("away", "")
    home = info.get("home", "")
    top_text = escape_ffmpeg_text(f"{away} vs {home} 하이라이트" if away and home else "KBO 하이라이트")
    bottom_text = escape_ffmpeg_text(f"{away} vs {home}" if away and home else "")
    date_str = escape_ffmpeg_text(date_str)

    m, s = divmod(start_sec, 60)
    start_ts = f"00:{m:02d}:{s:02d}"

    output_name = f"shorts_{date_str.replace('/', '')}_{away}vs{home}.mp4" if away else "shorts_output.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    font_bold = "C\\\\:/Windows/Fonts/malgunbd.ttf"

    # ffmpeg 명령을 .sh 파일로 작성하여 실행 (인코딩/이스케이프 문제 회피)
    script_path = os.path.join(OUTPUT_DIR, "run_ffmpeg.sh")
    script = (
        f'#!/bin/bash\n'
        f'ffmpeg -i "{video_path}" -ss {start_ts} -t {duration} \\\n'
        f'  -filter_complex "\n'
        f'    [0:v]crop=ih*9/16:ih,scale=1080:1920,gblur=sigma=30[bg];\n'
        f'    [0:v]scale=-2:960,crop=1080:960:(iw-1080)/2:0[main];\n'
        f"    [bg][main]overlay=0:(H-h)/2,\n"
        f"    drawtext=text='{date_str}':fontfile='{font_bold}':fontsize=100:fontcolor=yellow:borderw=4:bordercolor=black:x=(w-text_w)/2:y=60,\n"
        f"    drawtext=text='{top_text}':fontfile='{font_bold}':fontsize=108:fontcolor=yellow:borderw=4:bordercolor=black:x=(w-text_w)/2:y=175,\n"
        f"    drawtext=text='{bottom_text}':fontfile='{font_bold}':fontsize=80:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1750[outv]\n"
        f'  " \\\n'
        f'  -map "[outv]" -map 0:a -c:v libx264 -preset fast -crf 18 \\\n'
        f'  -c:a aac -b:a 128k -shortest "{output_path}" -y\n'
    )
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    result = subprocess.run(["bash", script_path], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"  ffmpeg 오류: {result.stderr[-500:]}")
        return None

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  생성 완료: {output_name} ({size_mb:.1f}MB)")
    return output_path


# ──────────────────────────────────────────────
# 4단계: YouTube 업로드
# ──────────────────────────────────────────────

def upload_to_youtube(file_path, info, privacy="private"):
    print("[4/4] YouTube 업로드 중...")
    from upload_shorts import upload_video

    away = info.get("away", "")
    home = info.get("home", "")
    date = info.get("date", "")
    date_display = info.get("date_display", "")

    title = f"{away} vs {home} 하이라이트 | {date}"
    description = (
        f"2026 신한 SOL KBO 리그 {away} vs {home} ({date_display})\n"
        f"하이라이트\n\n"
        f"#KBO #{home} #{away} #야구하이라이트 #Shorts"
    )
    tags = ["KBO", home, away, "야구하이라이트", "KBO하이라이트", "Shorts"]

    video_id, url = upload_video(file_path, title, description, tags, privacy=privacy)
    return url


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def parse_time(time_str):
    """'M:SS' 또는 'MM:SS' 형식을 초로 변환"""
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(time_str)


def main():
    parser = argparse.ArgumentParser(description="KBO Shorts Maker")
    parser.add_argument("url", help="YouTube 하이라이트 영상 URL")
    parser.add_argument("--upload", action="store_true", help="YouTube에 업로드")
    parser.add_argument("--public", action="store_true", help="공개로 업로드 (기본: 비공개)")
    parser.add_argument("--start", type=str, default=None, help="시작 시간 (예: 5:30)")
    parser.add_argument("--duration", type=int, default=20, help="클립 길이 (초, 기본: 20)")

    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1단계: 다운로드
    video_path, title, duration = download_video(args.url)
    info = parse_metadata(title)

    # 2단계: 장면 감지
    if args.start:
        start_sec = parse_time(args.start)
        clip_duration = args.duration
        m, s = divmod(start_sec, 60)
        print(f"[2/4] 수동 구간: {m}:{s:02d} ~ {m + (s + clip_duration) // 60}:{(s + clip_duration) % 60:02d}")
    else:
        start_sec, clip_duration = detect_highlight(video_path, args.duration)

    # 3단계: 쇼츠 생성
    output_path = generate_shorts(video_path, start_sec, clip_duration, info)
    if not output_path:
        print("쇼츠 생성 실패!")
        return

    # 4단계: 업로드 (선택)
    if args.upload:
        privacy = "public" if args.public else "private"
        url = upload_to_youtube(output_path, info, privacy)
        print(f"\n완료! {url}")
    else:
        print(f"\n완료! 파일: {output_path}")
        print("업로드하려면: python shorts_maker.py <url> --upload")


if __name__ == "__main__":
    main()
