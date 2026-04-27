"""손아섭 쇼츠 업로드 스크립트"""
from upload_shorts import upload_video

FILE = "D:/shorts-highlight/output/final_shorts.mp4"
TITLE = "서울오빠 손아섭, 두산 데뷔전 신고식 🔥"
DESCRIPTION = (
    "2026 신한 SOL KBO 리그 4/14 두산 vs SSG\n"
    "서울오빠 손아섭의 두산 데뷔 첫 경기 하이라이트\n\n"
    "0:00 팀 케미\n"
    "0:05 첫 득점\n"
    "0:15 첫 안타 (홈런)\n\n"
    "#KBO #손아섭 #두산베어스 #서울오빠 #Shorts"
)
TAGS = [
    "KBO", "손아섭", "두산베어스", "서울오빠", "두산", "SSG",
    "KBO하이라이트", "프로야구", "홈런", "손아섭홈런", "베어스",
    "Shorts", "야구쇼츠",
]

video_id, url = upload_video(FILE, TITLE, DESCRIPTION, TAGS, privacy="private")
print(f"\nVIDEO_ID={video_id}")
print(f"URL={url}")
