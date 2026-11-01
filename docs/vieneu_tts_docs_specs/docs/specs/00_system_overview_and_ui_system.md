# 00. Tổng Quan Hệ Thống & Thiết Kế Giao Diện Chung (Global UI/UX & Design System)

* **Phiên bản:** 1.0
* **Cập nhật:** 01/11/2026
* **Đối tượng:** Product Manager, UI/UX Designer, Frontend Lead

---

## 1. Giới Thiệu Hệ Thống VieNeu

**VieNeu** là nền tảng chuyển đổi văn bản thành giọng nói (Text-to-Speech - TTS) thế hệ mới (Model V4) dành cho người dùng cá nhân, nhà sáng tạo nội dung (Content Creator, Podcaster, Audiobook Producer) và lập trình viên.

### 1.1. Sơ đồ phân hệ chức năng (Sitemap)
Hệ thống phía người dùng (User Portal) được tổ chức thành 3 nhóm chức năng chính trên thanh điều hướng bên trái (Left Sidebar):
1. **Nhóm `TẠO` (Creation Suite):**
   * **Phòng thu (`/studio`):** Chuyển đổi văn bản thành giọng nói đơn lẻ, hỗ trợ chèn cảm xúc, nhạc nền, đọc công thức Toán/Hóa.
   * **Podcast (`/podcast`):** Tạo tập podcast đa giọng nói theo kịch bản hội thoại từng lượt (`Host`, `Guest`).
   * **Truyện (`/stories`):** Quản lý dự án truyện nhiều nhân vật, tạo/sửa từng phân đoạn độc lập, kéo-thả sắp xếp và xuất file liền mạch.
   * **Lồng tiếng (`/dubbing`):** Công cụ lồng tiếng video/phụ đề.
   * **Bài giảng (`/lectures`):** Công cụ thuyết minh bài giảng/slide.
2. **Nhóm `THƯ VIỆN` (Library & Discovery):**
   * **Giọng nói (`/library/voices`):** Quản lý lịch sử các bản ghi âm thanh đã tạo của người dùng.
   * **Bảng xếp hạng (`/leaderboard`):** Bảng xếp hạng 50 giọng đọc phổ biến nhất theo thời gian, giới tính và vùng miền.
   * **Nhân bản giọng (`/voice-cloning`):** Công cụ nhân bản giọng nói AI cá nhân hóa.
   * **Cộng đồng (`/community`):** Không gian chia sẻ cộng đồng.
   * **Tải ứng dụng (`/download-app`):** Trang tải ứng dụng VieNeu cho máy tính (Desktop App).
3. **Nhóm `TÀI KHOẢN` (Account, Billing & Developer):**
   * **Bảng điều khiển (`/dashboard`):** Tổng quan số dư token, hạn mức ngày, biểu đồ hoạt động 7 ngày và phân bổ giọng đọc.
   * **Thanh toán (`/billing`):** Quản lý gói cước token API, bản quyền app máy tính và áp dụng mã giảm giá.
   * **Nhà phát triển (`/developer`):** Quản lý API Keys (`Live`/`Test`), theo dõi mức sử dụng và kết nối MCP (`https://api.vieneu.io/mcp`).
   * **Từ điển phát âm (`/dictionary`):** Định nghĩa quy tắc đọc từ viết tắt, tên riêng, thuật ngữ theo tài khoản (tối đa 2.000 luật).

---

## 2. Hệ Thống Thiết Kế (Design System & Tokens)

### 2.1. Bảng màu chuẩn (Color Palette - Dark Theme Default)

| Tên Token | Mã Màu (Hex / RGBA) | Mục Đích Sử Dụng |
| :--- | :--- | :--- |
| `--bg-app` | `#0B0B0F` | Nền chính toàn trang (Main Canvas Background) |
| `--bg-sidebar` | `#09090D` | Nền thanh điều hướng bên trái |
| `--bg-surface-1` | `#12121A` | Nền Card, Panel, Khối nội dung chính |
| `--bg-surface-2` | `#1A1A24` | Nền Input, Dropdown, Button phụ, Hover state |
| `--border-subtle` | `#262636` | Viền mảnh (`1px solid`) cho các Card, Input, Table |
| `--border-focus` | `#7C5CFC` | Viền khi focus vào ô tìm kiếm, ô nhập liệu hoặc Card đang chọn |
| `--primary-500` | `#7C5CFC` | Màu thương hiệu chính (Primary Button, Active Badge, Progress Bar, Toggle) |
| `--primary-600` | `#6D4AFF` | Màu Hover của Primary Button |
| `--primary-soft` | `rgba(124, 92, 252, 0.15)` | Nền nhạt cho Badge, Banner thông báo, Active Tab |
| `--text-primary` | `#F3F4F6` | Chữ tiêu đề, nội dung chính, con số thống kê |
| `--text-secondary` | `#9CA3AF` | Chữ mô tả phụ, nhãn cột, metadata |
| `--text-muted` | `#6B7280` | Placeholder trong ô nhập, chú thích mờ |
| `--success-500` | `#10B981` / `#34D399` | Trạng thái hợp lệ, khối "Được phép", badge "Dùng thử" |
| `--danger-500` | `#EF4444` / `#F87171` | Khối "Không được phép", lỗi thất bại, badge thông báo đỏ |
| `--rank-gold` | `#F59E0B` | Viền và badge Cúp Hạng 1 trên Bảng xếp hạng |
| `--rank-silver` | `#94A3B8` | Viền và badge Cúp Hạng 2 trên Bảng xếp hạng |
| `--rank-bronze` | `#D97706` | Viền và badge Cúp Hạng 3 trên Bảng xếp hạng |

### 2.2. Typography (Kiểu chữ & Kích thước)
* **Font chữ chính (Sans-serif):** `Inter`, `Plus Jakarta Sans`, hoặc `system-ui` (hỗ trợ đầy đủ dấu tiếng Việt và ký hiệu toán học Unicode).
* **Font chữ số liệu / kỹ thuật (Monospace):** `JetBrains Mono` hoặc `Fira Code` (áp dụng cho bộ đếm ký tự/token `140.574 / 150.000`, thời lượng `146.0s`, địa chỉ MCP URL, và API Keys).
* **Quy ước định dạng số:**
  * Sử dụng dấu chấm (`.`) hoặc dấu phẩy (`,`) phân cách hàng nghìn nhất quán cho hạn mức và giá tiền: `140.574 / 150.000`, `99.000 ₫`.
  * Sử dụng dấu chấm thập phân cho thời lượng giây: `146.0s`, `147.3s`.

---

## 3. Đặc Tả Các Thành Phần Khung Giao Diện Chung (Global Shell)

### 3.1. Left Sidebar Navigation (`width: 240px`, cố định bên trái)
1. **Brand Header:**
   * Hiển thị icon sóng âm màu trắng trong ô vuông bo góc màu tím (`32x32px`) + chữ **VieNeu** (`18px`, `font-weight: 700`).
2. **Menu Items & Notification Dot:**
   * Mỗi mục menu có chiều cao `38px`, bo góc `8px`, icon `18x18px` bên trái + nhãn văn bản.
   * Khi đang ở route tương ứng (`active`), mục menu có nền `#1F1F2E`, chữ trắng đậm và icon đổi sang màu tím `#8B5CF6`.
   * Các tính năng mới hoặc đang có cập nhật (`Podcast`, `Truyện`, `Bài giảng`, `Cộng đồng`) hiển thị một chấm tròn nhỏ màu tím (`6x6px`) ở sát lề phải của mục menu.
3. **Sidebar Footer:**
   * **Widget Số dư Token** (hiển thị động ở các màn hình công cụ Tạo như *Phòng thu*, *Podcast*):
     * Khung bo góc viền mảnh, icon ví tiền bên trái, dòng trên ghi `Số dư token`, dòng dưới ghi `140.574 / 150.000`.
   * **Mục Thông báo:** Icon chuông + chữ `Thông báo` + Badge vuông bo góc nền đỏ `#EF4444` chữ trắng hiển thị số lượng thông báo chưa đọc (VD: `1`).
   * **Mục Trợ giúp & liên hệ:** Mở modal hỗ trợ hoặc trang tài liệu hướng dẫn.
   * **Cụm chuyển đổi Theme & Ngôn ngữ:**
     * Nút vuông `[☀️]` / `[🌙]`: Chuyển đổi giữa Dark Mode và Light Mode.
     * Dropdown `[VI v]`: Chuyển đổi ngôn ngữ giao diện (`VI` - Tiếng Việt, `EN` - English).
   * **User Profile Footer Bar:**
     * Avatar tròn `32x32px` hiển thị 2 chữ cái đầu của tên/email (VD: `SO`) trên nền tím.
     * Tên tài khoản/email có `text-overflow: ellipsis` (VD: `sondn2010f@gmail...`) và dòng phụ hiển thị gói hiện tại (`Gói Pro`).
     * Nút Icon Đăng xuất (`Logout`) nằm bên phải cùng.

### 3.2. Thanh Tiến Độ Người Mới (Top Onboarding Bar — "Bắt đầu")
* Hiển thị ở phần đầu màn hình làm việc (*Phòng thu*, *Podcast*) cho tới khi người dùng hoàn thành 4/4 bước hoặc chủ động bấm `X Ẩn`.
* Cấu trúc:
  * Bên trái: Icon danh sách + chữ **Bắt đầu** + Badge `Đã xong 1/4` (hoặc `Đã xong 2/4`) + nút mũi tên mở rộng `v` để xem danh sách 4 nhiệm vụ làm quen hệ thống.
  * Bên phải: Nút `X Ẩn` (Gọi API lưu trạng thái `onboarding_hidden = true`).

### 3.3. Nút Hỗ Trợ Nhanh (Floating Customer Support Button)
* Vị trí: `position: fixed; bottom: 20px; right: 20px; z-index: 50`.
* Kích thước: Hình tròn `48x48px`, nền tím `#7C5CFC`, đổ bóng nhẹ, bên trong là icon tai nghe hỗ trợ màu trắng.
* Hành vi: Click để mở khung chat hỗ trợ trực tuyến hoặc gửi phản hồi nhanh.
