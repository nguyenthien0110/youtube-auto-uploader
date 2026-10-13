import os
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

def get_authenticated_services():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Thiếu biến môi trường OAuth.")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    drive_service = build("drive", "v3", credentials=creds)
    youtube_service = build("youtube", "v3", credentials=creds)

    return drive_service, youtube_service


def get_pending_videos(drive_service, folder_id):
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType contains 'video/' and "
        f"trashed = false"
    )
    results = drive_service.files().list(
        q=query,
        orderBy="createdTime",
        fields="files(id, name, mimeType, createdTime)",
        pageSize=50
    ).execute()

    return results.get("files", [])


def download_file(drive_service, file_id, destination_path):
    print(f"Bắt đầu tải file: {destination_path}")
    request = drive_service.files().get_media(fileId=file_id)
    with io.FileIO(destination_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024 * 10)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Tiến độ tải Drive: {int(status.progress() * 100)}%")


def upload_to_youtube(youtube_service, file_path, title):
    print(f"Bắt đầu upload YouTube: {title}")
    clean_title = os.path.splitext(title)[0]

    body = {
        "snippet": {
            "title": clean_title,
            "description": "Chào mừng các bạn đã đến với kênh của mình! Hãy nhấn đăng ký để xem các video chia sẻ kiến thức mới nhất mỗi ngày nhé !",
            "tags": ["chia se kien thuc", "kien thuc", "shorts"],
            "categoryId": "27"
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(
        file_path,
        chunksize=1024 * 1024 * 5,
        resumable=True
    )

    request = youtube_service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Tiến độ upload YouTube: {int(status.progress() * 100)}%")

    print(f"Upload thành công! Video ID: {response.get('id')}")
    return response.get("id")


def move_file_to_archive(drive_service, file_id, source_folder_id, archive_folder_id):
    file_info = drive_service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file_info.get("parents", [source_folder_id]))

    drive_service.files().update(
        fileId=file_id,
        addParents=archive_folder_id,
        removeParents=previous_parents,
        fields="id, parents"
    ).execute()
    print("Đã chuyển video vào thư mục lưu trữ.")


def main():
    source_folder_id = os.environ.get("SOURCE_FOLDER_ID")
    archive_folder_id = os.environ.get("ARCHIVE_FOLDER_ID")
    upload_limit = int(os.environ.get("UPLOAD_LIMIT", 1))

    if not source_folder_id or not archive_folder_id:
        raise ValueError("Thiếu SOURCE_FOLDER_ID hoặc ARCHIVE_FOLDER_ID.")

    drive_service, youtube_service = get_authenticated_services()

    videos = get_pending_videos(drive_service, source_folder_id)
    if not videos:
        print("Không có video nào trong thư mục nguồn.")
        return

    print(f"Tìm thấy {len(videos)} video. Giới hạn upload: {upload_limit}")
    videos_to_process = videos[:upload_limit]

    for index, video in enumerate(videos_to_process, 1):
        file_id = video["id"]
        file_name = video["name"]
        local_path = os.path.join("/tmp", file_name)

        try:
            print(f"\n--- [{index}/{len(videos_to_process)}] Xử lý: {file_name} ---")
            download_file(drive_service, file_id, local_path)
            upload_to_youtube(youtube_service, local_path, file_name)
            move_file_to_archive(drive_service, file_id, source_folder_id, archive_folder_id)
        except Exception as e:
            print(f"Lỗi khi xử lý {file_name}: {e}")
            raise e
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    print("\nHoàn tất xử lý.")


if __name__ == "__main__":
    main()