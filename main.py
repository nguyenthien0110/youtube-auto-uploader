import os
import io
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Đọc cấu hình từ biến môi trường
SOURCE_FOLDER_ID = os.environ.get("SOURCE_FOLDER_ID")
ARCHIVE_FOLDER_ID = os.environ.get("ARCHIVE_FOLDER_ID")
GDRIVE_REFRESH_TOKEN = os.environ.get("GDRIVE_REFRESH_TOKEN")
GDRIVE_CLIENT_ID = os.environ.get("GDRIVE_CLIENT_ID")
GDRIVE_CLIENT_SECRET = os.environ.get("GDRIVE_CLIENT_SECRET")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload"
]

def get_services():
    """Tạo client kết nối Drive và YouTube bằng OAuth Refresh Token"""
    creds = Credentials(
        None,
        refresh_token=GDRIVE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GDRIVE_CLIENT_ID,
        client_secret=GDRIVE_CLIENT_SECRET,
        scopes=SCOPES
    )
    drive_service = build("drive", "v3", credentials=creds)
    youtube_service = build("youtube", "v3", credentials=creds)
    return drive_service, youtube_service

def get_pending_videos(drive_service):
    """Bước 1: Watch/List các video trong folder nguồn"""
    query = f"'{SOURCE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def download_video(drive_service, file_id, file_name):
    """Bước 2: Download video về ổ đĩa tạm của GitHub Actions runner"""
    request = drive_service.files().get_media(fileId=file_id)
    local_path = os.path.join("/tmp", file_name)
    with io.FileIO(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Downloading {file_name}: {int(status.progress() * 100)}%")
    return local_path

def upload_to_youtube(youtube_service, file_path, title):
    """Bước 3: Upload video lên YouTube"""
    body = {
        "snippet": {
            "title": os.path.splitext(title)[0],
            "description": "Uploaded automatically via GitHub Actions",
            "tags": ["auto", "video"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private"  # 'public', 'private', hoặc 'unlisted'
        }
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube_service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading to YouTube: {int(status.progress() * 100)}%")
    print(f"Uploaded successfully! Video ID: {response.get('id')}")
    return response.get("id")

def move_drive_file(drive_service, file_id):
    """Bước 4: Di chuyển file sang thư mục Archive"""
    file = drive_service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents"))
    drive_service.files().update(
        fileId=file_id,
        addParents=ARCHIVE_FOLDER_ID,
        removeParents=previous_parents,
        fields="id, parents"
    ).execute()
    print(f"Moved file {file_id} to archive folder.")

def main():
    drive_service, youtube_service = get_services()
    videos = get_pending_videos(drive_service)
    
    if not videos:
        print("Không tìm thấy video nào mới trong thư mục nguồn.")
        return

    print(f"Tìm thấy {len(videos)} video cần xử lý.")
    for v in videos:
        file_id = v["id"]
        file_name = v["name"]
        print(f"\n--- Đang xử lý: {file_name} ---")
        
        # 1. Download
        local_file = download_video(drive_service, file_id, file_name)
        
        # 2. Upload YouTube
        upload_to_youtube(youtube_service, local_file, file_name)
        
        # 3. Move Drive File
        move_drive_file(drive_service, file_id)
        
        # Xóa file tạm
        if os.path.exists(local_file):
            os.remove(local_file)

if __name__ == "__main__":
    main()