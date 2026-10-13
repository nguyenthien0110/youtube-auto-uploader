# Hướng dẫn Cài đặt & Vận hành Tự động Upload Video từ Google Drive lên YouTube

Tài liệu này hướng dẫn chi tiết từng bước (step-by-step) cách thiết lập hệ thống tự động tải video từ Google Drive và đăng lên YouTube bằng **GitHub Actions**.

---

## 1. Chuẩn bị Thư mục Google Drive

1. Đăng nhập vào [Google Drive](https://drive.google.com/).
2. Tạo 2 thư mục riêng biệt:
   - **Thư mục nguồn (Source Folder):** Chứa video chờ đăng tải.
   - **Thư mục lưu trữ (Archive Folder):** Nơi tự động chuyển video vào sau khi upload thành công lên YouTube.
3. Lấy ID của từng thư mục:
   - Mở thư mục trên trình duyệt web, quan sát đường link URL có dạng:
     `https://drive.google.com/drive/folders/1a2b3c4d5e6f...`
   - Chuỗi ký tự nằm sau `/folders/` chính là **Folder ID**.
   - Ghi lại 2 ID này để chuẩn bị cấu hình vào GitHub.

---

## 2. Tạo Dự án và Cấu hình Google Cloud Platform (GCP)

### 2.1. Tạo Project & Kích hoạt API

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo một Project mới (hoặc chọn project hiện có).
3. Vào mục **APIs & Services** (API và Dịch vụ) -> **Library** (Thư viện).
4. Tìm kiếm và bấm **Enable** (Bật) lần lượt 2 API sau:
   - **Google Drive API**
   - **YouTube Data API v3**

### 2.2. Cấu hình Màn hình xác thực (OAuth Consent Screen)

1. Vào **APIs & Services** -> **OAuth consent screen** (Màn hình xác nhận OAuth).
2. Chọn loại người dùng là **External** (Ngoài tổ chức) rồi bấm **Create**.
3. Điền các trường thông tin cơ bản:
   - App name: `Auto Uploader`
   - User support email: Email của bạn.
   - Developer contact email: Email của bạn.
   - Bấm **Save and Continue**.
4. Bỏ qua bước **Scopes** bằng cách bấm **Save and Continue**.
5. Tại mục **Test users** (Người dùng thử nghiệm):
   - Bấm **Add Users** và nhập chính xác địa chỉ Gmail sở hữu kênh YouTube và Google Drive.
   - Bấm **Save and Continue** rồi hoàn tất.

### 2.3. Tạo OAuth Client ID & Secret

1. Vào mục **APIs & Services** -> **Credentials** (Mã định danh).
2. Bấm **+ Create Credentials** -> chọn **OAuth client ID**.
3. Tại ô **Application type**, chọn **Web application**.
4. Điền tên client tùy ý (ví dụ: `Web client 1`).
5. Cuộn xuống phần **Authorized redirect URIs** (URI chuyển hướng được phép), bấm **Add URI** và thêm chính xác đường dẫn:
   ```text
   https://developers.google.com/oauthplayground
   ```
6. Bấm **Create**.
7. Lưu lại 2 giá trị xuất hiện trên màn hình:
   - **Client ID** (dạng `...apps.googleusercontent.com`)
   - **Client Secret**

---

## 3. Lấy Refresh Token qua OAuth Playground

1. Truy cập [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
2. Bấm vào biểu tượng **Bánh răng ⚙️** ở góc trên cùng bên phải:
   - Tích chọn ô **Use your own OAuth credentials**.
   - Dán **OAuth Client ID** và **OAuth Client secret** vừa lấy ở Bước 2 vào 2 ô tương ứng.
   - Bấm **Close**.
3. Tại cột bên trái (**Step 1: Select & authorize APIs**):
   - Cuộn xuống dưới cùng tìm ô **Input your own scopes**.
   - Dán chính xác chuỗi sau vào ô:
     ```text
     https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/youtube
     ```
   - Nhấn nút xanh **Authorize APIs**.
4. Đăng nhập bằng tài khoản Google đã được thêm vào Test users:
   - Khi gặp màn hình _"Google chưa xác minh ứng dụng này"_, nhấn chữ **Tiếp tục** (hoặc _Nâng cao -> Đi tới ứng dụng (không an toàn)_).
   - Tích chọn đồng ý các quyền truy cập được yêu cầu -> Bấm **Tiếp tục**.
5. Trang sẽ tự động chuyển sang **Step 2: Exchange authorization code for tokens**:
   - Bấm nút xanh **Exchange authorization code for tokens**.
   - Sao chép toàn bộ chuỗi ký tự hiển thị tại ô **Refresh token**.

---

## 4. Cấu hình GitHub Repository

Mở repository trên GitHub, chuyển đến tab **Settings** -> mục **Secrets and variables** -> **Actions**.

### 4.1. Thêm Repository Secrets (Bảo mật)

Nhấn **New repository secret** và thêm đủ 5 biến sau:

| Tên Secret             | Ý nghĩa                                        |
| :--------------------- | :--------------------------------------------- |
| `GDRIVE_CLIENT_ID`     | OAuth Client ID lấy từ GCP                     |
| `GDRIVE_CLIENT_SECRET` | OAuth Client Secret lấy từ GCP                 |
| `GDRIVE_REFRESH_TOKEN` | Refresh Token lấy từ OAuth Playground          |
| `SOURCE_FOLDER_ID`     | ID thư mục Google Drive chứa video chờ upload  |
| `ARCHIVE_FOLDER_ID`    | ID thư mục Google Drive lưu trữ sau khi upload |

### 4.2. Thêm Repository Variables (Cấu hình linh hoạt)

Chuyển sang tab **Variables**, bấm **New repository variable** và thêm 2 biến:

| Tên Variable    | Giá trị mẫu | Ý nghĩa                                                          |
| :-------------- | :---------- | :--------------------------------------------------------------- |
| `SCHEDULE_HOUR` | `07`        | Giờ chạy tự động hàng ngày theo giờ Việt Nam (từ `00` đến `23`). |
| `UPLOAD_LIMIT`  | `1`         | Số lượng video tối đa được upload trong mỗi lượt chạy.           |

---

## 5. Cấu trúc Code trong Repository

Repository cần chứa 2 file chính sau:

```text
├── .github/
│   └── workflows/
│       └── run.yml    # File cấu hình lịch trình GitHub Actions
├── main.py            # Script xử lý tải, đăng video và chuyển thư mục
└── README.md
```

### File `main.py`

Xử lý kết nối OAuth không truyền param scopes để tránh lỗi `invalid_scope`, tự động lấy video cũ nhất theo thời gian tạo (`orderBy="createdTime"`), đẩy lên YouTube với metadata chuẩn và chuyển file sang thư mục archive.

### File `.github/workflows/run.yml`

Chạy cron job định kỳ hàng giờ để kiểm tra biến `SCHEDULE_HOUR`. Khi đến đúng khung giờ chỉ định (giờ Việt Nam), workflow sẽ kích hoạt chạy script Python. Ngoài ra, workflow vẫn cho phép bấm nút **Run workflow** thủ công với tùy chọn nhập đè số lượng video bất cứ lúc nào.

---

## 6. Vận hành & Lưu ý

- **Vận hành hàng ngày:** Chỉ cần thả các video cần đăng vào thư mục nguồn trên Drive. Hệ thống sẽ tự động quét các file cũ nhất và upload đúng giờ đã hẹn.
- **Thay đổi giờ chạy hoặc số lượng video:** Vào **Settings** -> **Secrets and variables** -> **Actions** -> **Variables**, chỉnh sửa giá trị của `SCHEDULE_HOUR` hoặc `UPLOAD_LIMIT` mà không cần sửa code.
- **Giới hạn API YouTube:** Mỗi tài khoản Google thông thường có hạn ngạch YouTube API v3 là 10.000 units/ngày (mỗi video upload tốn khoảng 1.600 units). Khuyến nghị để `UPLOAD_LIMIT` từ 1 đến 5 video/ngày để tránh vượt quota.
