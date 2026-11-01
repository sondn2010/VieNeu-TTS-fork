# 01. Đặc Tả Modal Điều Khoản Tạo Giọng Nói & Kiểm Duyệt AI

* **Tham chiếu hình ảnh:** `../assets/screens/01_modal_dieu_khoan_tao_giong_noi.jpg` (`image_466c33.jpg`)
* **Phân hệ:** Content Safety, Legal Compliance & Pre-TTS Moderation

---

## 1. Mục Đích Nghiệp Vụ
Đảm bảo mọi người dùng trước khi sử dụng các công cụ tổng hợp giọng nói (Phòng thu, Podcast, Truyện...) đều đọc, hiểu rõ và cam kết tuân thủ quy định pháp luật Việt Nam cũng như tiêu chuẩn cộng đồng của VieNeu. Mọi văn bản đầu vào đều phải đi qua lớp kiểm duyệt AI tự động trước khi được phép chuyển thành âm thanh.

---

## 2. Đặc Tả Giao Diện (UI Specification)

### 2.1. Cấu trúc Modal
* **Backdrop:** Phủ toàn màn hình (`background: rgba(5, 5, 10, 0.78)`, `backdrop-filter: blur(4px)`), khóa cuộn trang nền (`overflow: hidden`). Không cho phép đóng modal bằng cách click ra ngoài vùng backdrop hoặc bấm phím `ESC` nếu người dùng chưa đồng ý điều khoản.
* **Modal Dialog:**
  * Kích thước: `width: 100%`, `max-width: 520px`, `max-height: 85vh`, nền `#13131C`, viền `1px solid #28283C`, bo góc `14px`.
  * Bố cục chia 3 phần: **Header cố định**, **Body có thanh cuộn dọc (`overflow-y: auto`)**, và **Footer cố định**.

### 2.2. Chi tiết nội dung trong Modal
1. **Header:**
   * Icon Cán cân công lý (`⚖️`) màu tím đặt trong khung vuông bo góc nền tím nhạt (`36x36px`).
   * Tiêu đề: **Điều khoản tạo giọng nói** (`18px`, Bold, `#FFFFFF`).
   * Phụ đề: *Vui lòng đọc kỹ trước khi sử dụng* (`13px`, `#9CA3AF`).
2. **Đoạn dẫn nhập:**
   * *"Trước khi tạo giọng nói, vui lòng đọc và đồng ý với các điều khoản sau. Mọi văn bản đều được hệ thống AI kiểm duyệt trước khi tạo."*
3. **Khối "Được phép" (Allowed Content Box):**
   * Style: Nền `rgba(16, 185, 129, 0.08)`, viền `1px solid rgba(16, 185, 129, 0.3)`, bo góc `10px`, padding `14px 16px`.
   * Tiêu đề: Icon dấu tích tròn xanh lá + **Được phép** (Màu `#34D399`, Bold).
   * Nội dung (Màu `#6EE7B7`):
     > Nội dung hợp pháp, lịch sử cho mục đích cá nhân, giáo dục, kinh doanh, sáng tạo và giải trí.
4. **Khối "Không được phép" (Prohibited Content Box):**
   * Style: Nền `rgba(239, 68, 68, 0.08)`, viền `1px solid rgba(239, 68, 68, 0.3)`, bo góc `10px`, padding `14px 16px`.
   * Tiêu đề: Icon biển cấm tròn đỏ + **Không được phép** (Màu `#F87171`, Bold).
   * Danh sách 5 quy định cấm (Màu `#FCA5A5`, gạch đầu dòng `-`):
     1. `Ngôn từ tục tĩu mang tính lăng mạ, xúc phạm nghiêm trọng (ngôn ngữ đời thường vẫn được chấp nhận).`
     2. `Nội dung khiêu dâm hoặc gợi dục.`
     3. `Lăng mạ, bôi nhọ, phân biệt, kích động thù ghét hoặc quấy rối.`
     4. `Nội dung xuyên tạc, chống phá Nhà nước, Đảng, lãnh đạo hoặc chủ quyền quốc gia Việt Nam.`
     5. `Kêu gọi bạo lực, tự gây hại hoặc hành vi vi phạm pháp luật.`
5. **Footer Hành động:**
   * **Checkbox xác nhận:**
     * Nhãn: `Tôi đã đọc và đồng ý với các điều khoản trên.`
     * Màu checkbox khi được chọn (`checked`): Nền xanh/tím `#6366F1` / `#7C5CFC` kèm dấu tích trắng.
   * **Button chính:**
     * Nhãn: **Đồng ý và tiếp tục**
     * Kích thước: `width: 100%`, chiều cao `42px`, bo góc `8px`, nền `#7C5CFC`, chữ trắng đậm.

---

## 3. Logic Nghiệp Vụ & Luồng Xử Lý Kỹ Thuật (Business & Technical Rules)

### 3.1. Điều kiện hiển thị Modal
* Khi người dùng truy cập vào `/studio`, `/podcast`, hoặc `/stories`:
  * Kiểm tra trường `user.has_accepted_tts_terms` (từ API `/api/v1/user/profile`) hoặc cờ `vieneu_tts_terms_v1_accepted` trong `localStorage`.
  * Nếu `false`: Hiển thị ngay Modal **Điều khoản tạo giọng nói** đè lên màn hình làm việc.
* Trạng thái nút **Đồng ý và tiếp tục**:
  * Nếu `checkbox.checked === false` -> Button ở trạng thái `disabled` (`opacity: 0.5`, `cursor: not-allowed`).
  * Nếu `checkbox.checked === true` -> Button ở trạng thái `enabled`.
* Khi click **Đồng ý và tiếp tục**:
  1. Gửi request `POST /api/v1/user/terms/accept` (lưu `terms_version = "1.0"`, `accepted_at = NOW()`, `ip_address`).
  2. Lưu cache `localStorage.setItem("vieneu_tts_terms_v1_accepted", "true")`.
  3. Đóng Modal và cho phép người dùng thao tác bình thường trên phòng thu.

### 3.2. Pipeline Kiểm duyệt AI trước khi tạo giọng (Pre-TTS AI Moderation)
Mọi request tạo giọng nói (`POST /api/v1/tts/generate`, `POST /api/v1/tts/stream`, `POST /api/v1/podcasts`, `POST /api/v1/stories/:id/segments/:segId/generate`) đều phải đi qua hàm `moderateTextContent(text)`:

| Mã Danh Mục Vi Phạm | Mô Tả Kiểm Duyệt | Hành Xử Hệ Thống |
| :--- | :--- | :--- |
| `PROFANITY_SEVERE` | Ngôn từ tục tĩu mang tính lăng mạ, xúc phạm nghiêm trọng *(Lưu ý: Cho phép ngôn ngữ đời thường tự nhiên trong văn học/đời sống không mang tính lăng mạ)*. | Chặn tạo audio, trả lỗi `422` |
| `SEXUAL_EXPLICIT` | Nội dung khiêu dâm hoặc gợi dục. | Chặn tạo audio, trả lỗi `422` |
| `HATE_HARASSMENT` | Lăng mạ, bôi nhọ, phân biệt, kích động thù ghét hoặc quấy rối cá nhân/tổ chức. | Chặn tạo audio, trả lỗi `422` |
| `POLITICAL_SOVEREIGNTY` | Nội dung xuyên tạc, chống phá Nhà nước, Đảng, lãnh đạo hoặc chủ quyền quốc gia Việt Nam. | Chặn tạo audio, trả lỗi `422`, ghi log cảnh báo bảo mật |
| `VIOLENCE_ILLEGAL` | Kêu gọi bạo lực, tự gây hại hoặc hướng dẫn hành vi vi phạm pháp luật. | Chặn tạo audio, trả lỗi `422` |

* **Chính sách bảo vệ Token người dùng:** Nếu văn bản bị chặn ở bước AI kiểm duyệt (`422 CONTENT_POLICY_VIOLATION`), hệ thống **tuyệt đối không trừ token** và **không trừ hạn mức ký tự hằng ngày** của người dùng, đồng thời không tính vào tỷ lệ lỗi kỹ thuật của hệ thống.
