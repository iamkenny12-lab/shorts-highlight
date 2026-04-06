# KBO Shorts Highlight

KBO 프로야구 하이라이트 영상에서 자동으로 YouTube Shorts를 생성하는 도구

## 주요 기능

- YouTube 하이라이트 영상 자동 다운로드 (yt-dlp)
- 프레임 변화량 분석으로 주요 장면 자동 감지
- 세로형(9:16) 쇼츠 영상 자동 생성 (ffmpeg)
- 날짜, 팀명, 스코어 텍스트 오버레이 자동 생성
- YouTube 자동 업로드

## 프로젝트 구조

```
shorts-highlight/
├── shorts_maker.py       # 메인 파이프라인 (다운로드 → 감지 → 생성 → 업로드)
├── upload_shorts.py      # YouTube 업로드 모듈
├── ssl_handler.py        # SSL 우회 처리
├── credentials.json      # Google OAuth2 인증
├── token.json            # YouTube API 토큰
├── preview/              # 원본 캡처 이미지
├── preview_d/            # 텍스트 오버레이 시안
├── preview_d2/           # 텍스트 오버레이 시안 v2
├── preview_d3/           # 텍스트 오버레이 시안 v3
└── preview_final/        # 최종 버전
```

## 사용법

```bash
# 기본: 하이라이트 자동 감지 → 쇼츠 생성
python shorts_maker.py <youtube_url>

# 수동 구간 지정
python shorts_maker.py <youtube_url> --start 5:30 --duration 20

# 생성 + YouTube 업로드
python shorts_maker.py <youtube_url> --upload

# 공개로 업로드
python shorts_maker.py <youtube_url> --upload --public
```

## 워크플로우

1. YouTube 하이라이트 영상 URL 입력
2. yt-dlp로 영상 다운로드 + 제목에서 팀명/날짜 자동 파싱
3. 프레임 변화량 분석으로 가장 임팩트 있는 구간 감지
4. ffmpeg로 세로 쇼츠 생성 (블러 배경 + 텍스트 오버레이)
5. YouTube 업로드 (선택)

## 의존성

- yt-dlp
- ffmpeg
- Pillow, numpy
- google-api-python-client (YouTube 업로드)
