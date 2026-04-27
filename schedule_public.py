"""비공개 상태 영상을 publishAt으로 예약 공개 처리"""
import os
import sys
import json
import certifi
import httplib2
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google_auth_httplib2
import google.auth.transport.requests

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token_fullscope.json")


def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    http = httplib2.Http(disable_ssl_certificate_validation=True)
    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
    return build("youtube", "v3", http=authorized_http)


def schedule_public(video_id, minutes_from_now=60):
    yt = get_service()
    publish_at = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    publish_at_iso = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    body = {
        "id": video_id,
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at_iso,
            "selfDeclaredMadeForKids": False,
        },
    }
    resp = yt.videos().update(part="status", body=body).execute()
    print(f"Video: {video_id}")
    print(f"publishAt: {publish_at_iso}")
    print(f"status: {resp.get('status')}")


if __name__ == "__main__":
    video_id = sys.argv[1] if len(sys.argv) > 1 else "MfaBUBO3tVM"
    minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    schedule_public(video_id, minutes)
