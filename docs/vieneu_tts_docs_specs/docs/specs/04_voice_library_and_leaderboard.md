# 04. Đặc Tả Phân Hệ Thư Viện Giọng Nói & Bảng Xếp Hạng Giọng

* **Tham chiếu hình ảnh:**
  * Giọng nói của tôi: `../assets/screens/05_thu_vien_giong_noi_cua_toi.png` (`image_466879.png`)
  * Bảng xếp hạng giọng: `../assets/screens/06_bang_xep_hang_giong.png` (`image_466839.png`)
* **Routes:** `/library/voices` và `/leaderboard`

---

## Phần A: Thư Viện — Giọng Nói Của Tôi (`/library/voices`)

### 1. Mục Đích Nghiệp Vụ
Cung cấp kho lưu trữ tập trung toàn bộ các bản ghi âm thanh mà người dùng đã tạo, hỗ trợ tìm kiếm toàn văn (full-text search) theo nội dung văn bản hoặc tên giọng, lọc theo giọng đọc, nghe lại, tải về máy hoặc xóa bản ghi.

### 2. Đặc Tả Giao Diện (UI Components)

1. **Header Trang:**
   * Tiêu đề: **Giọng nói của tôi** (`22px`, Bold, `#FFFFFF`).
   * Phụ đề: *Xem và quản lý giọng nói đã tạo* (`13px`, `#9CA3AF`).

2. **Thanh Tìm Kiếm, Bộ Lọc & Nút Tạo Mới:**
   * **Ô Tìm kiếm (Search Input):**
     * Chiều rộng `~420px`, chiều cao `40px`, bo góc `8px`, viền `#7C5CFC` khi focus.
     * Icon kính lúp `🔍` bên trái + Placeholder: `Tìm kiếm theo văn bản hoặc giọng...`
   * **Dropdown Lọc Giọng Đọc:**
     * Nằm ngay cạnh ô tìm kiếm, mặc định hiển thị `Tất cả giọng v`.
     * Khi mở ra sẽ liệt kê `Tất cả giọng` cùng danh sách các giọng đọc có trong lịch sử của người dùng.
   * **Nút `[+ Tạo mới]`:**
     * Căn sát lề phải, nền tím `#7C5CFC`, chữ trắng đậm. Click sẽ chuyển hướng người dùng sang trang **Phòng thu (`/studio`)**.

3. **Danh Sách Bản Ghi Âm Thanh (Recording Cards):**
   Mỗi bản ghi là một Card ngang (`background: #13131C`, `border: 1px solid #262636`, `border-radius: 10px`, `padding: 16px 20px`, `margin-bottom: 12px`):
   * **Bên trái:** Nút tròn `[▶]` (`42x42px`, nền `#1E1E2A`, icon tam giác trắng) để phát/tạm dừng bản ghi.
   * **Ở giữa:**
     * **Dòng 1 (Nội dung văn bản gốc):** Hiển thị văn bản gốc người dùng đã nhập (in đậm nhẹ, cắt 1 dòng với `...`), ví dụ:
       `ó một sự thật kỳ lạ trong tâm lý con người — kể cả những người có phép thuật — là khi một mối đe dọa...`
     * **Dòng 2 (4 thông số Metadata kèm icon riêng biệt, cách nhau `16px`):**
       * `👤 Minh Quân` (Icon người dùng + Tên giọng đọc)
       * `🌐 Tiếng Việt (VN)` (Icon quả địa cầu + Ngôn ngữ)
       * `🕒 146.0s` (Icon đồng hồ + Thời lượng giây)
       * `📅 16:23 30/10/2026` (Icon lịch + Giờ và ngày tạo `HH:mm DD/MM/YYYY`)
   * **Bên phải:**
     * Nút Icon Tải xuống `[⬇️]`: Tải trực tiếp file âm thanh về máy tính.
     * Nút Icon Xóa `[🗑️]`: Xóa bản ghi khỏi thư viện (hiển thị hộp thoại xác nhận trước khi xóa).

4. **Thanh Tổng Hợp Dưới Đáy (Sticky Footer Status Bar):**
   * Nằm cố định ở đáy vùng nội dung, chia 2 đầu trái/phải (`13px`, màu `#9CA3AF`):
     * Bên trái: `2 trong số 2 giọng nói` (`<số_bản_ghi_đang_hiển_thị> trong số <tổng_số_bản_ghi> giọng nói`).
     * Bên phải: `Tổng thời lượng: 293.3s` (Tổng cộng thời lượng `duration_seconds` của các bản ghi đang hiển thị).

---

## Phần B: Thư Viện — Bảng Xếp Hạng Giọng (`/leaderboard`)

### 1. Mục Đích Nghiệp Vụ
Hiển thị bảng xếp hạng 50 giọng đọc được sử dụng nhiều nhất trên toàn hệ thống VieNeu, giúp người dùng dễ dàng khám phá các giọng đọc xu hướng theo vùng miền/giới tính, nghe thử chất giọng và chọn sử dụng ngay chỉ với 1 cú click.

### 2. Đặc Tả Giao Diện (UI Components)

1. **Header & Chú Thích Quy Tắc Xếp Hạng:**
   * Icon Cúp vàng `🏆` đặt trong hộp vuông bo góc nền vàng nâu tối (`40x40px`) + Tiêu đề lớn: **Bảng xếp hạng giọng** (`24px`, Bold).
   * Dòng mô tả quy tắc công bằng (Fair-ranking rule):
     > *Xếp theo số người dùng mỗi giọng trong kỳ, không theo số lần tạo — một người tạo nhiều cũng chỉ tính một.*

2. **Thanh Bộ Lọc Đa Chiều (Filter Bar):**
   Nằm trên cùng một hàng ngang, gồm 3 nhóm bộ lọc kết hợp (AND logic):
   * **Nhóm 1 — Thời gian (Segmented Control):**
     * `[7 ngày qua]` (Mặc định Active - nền `#252538`, chữ trắng đậm)
     * `[Mọi lúc]`
   * **Nhóm 2 — Giới tính:**
     * `[Giới tính: Tất cả]` (Active - viền tím `#7C5CFC`, nền tím nhạt, chữ tím sáng)
     * `[Nữ]`
     * `[Nam]`
   * **Nhóm 3 — Vùng miền (Ngăn cách với nhóm Giới tính bởi vạch dọc `|`):**
     * `[Miền: Tất cả]` (Active - viền tím `#7C5CFC`, nền tím nhạt, chữ tím sáng)
     * `[Miền Bắc]`
     * `[Miền Trung]`
     * `[Miền Nam]`
   * **Dòng thông tin cập nhật (Ngay dưới thanh lọc):**
     * `50 giọng · cập nhật 06:20 01-11` (`12px`, màu `#6B7280`).

3. **Khu Vực Top 3 Podium Cards (3 Giọng Đọc Dẫn Đầu):**
   Hiển thị 3 Card lớn theo bố cục bục trao giải: **Hạng 2 (Bên trái) — Hạng 1 (Ở giữa, cao hơn `16px`) — Hạng 3 (Bên phải)**:

| Thuộc tính | Hạng 2 (Trái) | Hạng 1 (Giữa - Quán Quân) | Hạng 3 (Phải) |
| :--- | :--- | :--- | :--- |
| **Badge Thứ hạng** | `🏆 2` (Nền bạc `#CBD5E1`, chữ đen) | `🏆 1` (Nền vàng `#FBBF24`, chữ đen) | `🏆 3` (Nền cam đồng `#F59E0B`, chữ đen) |
| **Viền Card** | Viền xám bạc `#475569` | Viền vàng kim `#D97706` | Viền nâu đồng `#92400E` |
| **Tên giọng mẫu** | **Adam Tốp Tốp** | **Minh Quân** | **Hải Đăng** |
| **Giới tính & Miền** | `Nam · Miền Nam` | `Nam · Miền Bắc` | `Nam · Miền Bắc` |
| **Tags mô tả** | `Cảm xúc · Không nghiêm túc · Tốp Tốp · Tấu hài` | `Giọng nam trầm ấm` | `Bắc · Code · IT · Chuyên nghiệp` |
| **Thanh độ phổ biến** | Thanh tím tỷ lệ so với Hạng 1 (~85%) | Thanh tím đầy `100%` | Thanh tím tỷ lệ so với Hạng 1 (~42%) |
| **Nút hành động** | `[▶]` + `[Dùng giọng này]` (Nền tím) | `[▶]` + `[Dùng giọng này]` (Nền tím) | `[▶]` + `[Dùng giọng này]` (Nền tím) |

4. **Danh Sách Hạng 4 Trở Đi (Ranked List Rows — Hạng 4 đến 50):**
   * Khung danh sách bo góc (`background: #13131C`, `border: 1px solid #262636`), mỗi dòng (`height: 64px`, ngăn cách bằng `border-bottom: 1px solid #1E1E2C`) gồm:
     * **Cột 1 (Số thứ tự):** `4`, `5`, `6`, `7`, `8`, `9`, `10`... (`width: 48px`, căn giữa, màu `#9CA3AF`).
     * **Cột 2 (Avatar & Tên giọng):**
       * Avatar minh họa tròn (`36x36px`).
       * Dòng trên: Tên giọng đậm (**Duyên Hà My**, **Nhật Phong**, **Đăng Quân**, **Mai Bé Phương**, **Tường Vy**, **Thiện Minh**, **Nhỏ Ngọt Ngào**...).
       * Dòng dưới: `Nữ · Miền Nam` hoặc `Nam · Miền Bắc` (`12px`, `#6B7280`).
     * **Cột 3 (Thanh độ phổ biến):** Thanh progress bar ngang (`width: 110px`, chiều cao `6px`, nền `#262636`, phần fill màu tím `#7C5CFC` tỷ lệ theo lượng người dùng so với Top 1).
     * **Cột 4 (Hành động):**
       * Nút `[▶]` (Nghe file audio mẫu của giọng).
       * Nút `[Dùng]` (Viền `#2E2E42`, nền `#1A1A26`, click sẽ chuyển sang `/studio?voice=<voice_id>`).

### 3. Logic Nghiệp Vụ & Thuật Toán Bảng Xếp Hạng
1. **Công thức tính điểm xếp hạng (Unique Active Users per Voice):**
   * Với mỗi giọng đọc $v$, điểm phổ biến $U(v)$ trong khoảng thời gian $T \in \{ 	ext{7\_days}, 	ext{all\_time} \}$ là số lượng tài khoản duy nhất (`COUNT(DISTINCT user_id)`) đã tạo thành công ít nhất 1 bản ghi âm thanh sử dụng giọng $v$.
   * Khi người dùng chọn bộ lọc Giới tính và/hoặc Vùng miền, danh sách được lọc tương ứng, lấy Top 50 giọng có $U(v)$ cao nhất, đánh lại số thứ tự từ `1` đến `N` và tính lại tỷ lệ thanh tiến trình theo giọng đứng số 1 của tập kết quả đã lọc:
     $$	ext{ProgressWidth}(v_i) = \max\left(5\%, 	ext{round}\left(rac{U(v_i)}{U(v_1)} 	imes 100ight)\%ight)$$
2. **Trình phát mẫu giọng (Single Audio Preview Player):**
   * Tại một thời điểm chỉ cho phép phát mẫu 1 giọng duy nhất. Nếu người dùng đang nghe mẫu giọng *Minh Quân* mà bấm `[▶]` ở giọng *Adam Tốp Tốp*, trình phát tự động dừng *Minh Quân* và phát mẫu của *Adam Tốp Tốp*.
