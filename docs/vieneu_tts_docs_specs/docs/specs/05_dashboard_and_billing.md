# 05. Đặc Tả Phân Hệ Bảng Điều Khiển (Dashboard) & Thanh Toán (Billing)

* **Tham chiếu hình ảnh:**
  * Bảng điều khiển: `../assets/screens/07_bang_dieu_khien_dashboard.png` (`image_4667f6.png`)
  * Thanh toán & Đăng ký: `../assets/screens/08_thanh_toan_va_dang_ky.png` (`image_466512.png`)
* **Routes:** `/dashboard` và `/billing`

---

## Phần A: Tài Khoản — Bảng Điều Khiển (`/dashboard`)

### 1. Mục Đích Nghiệp Vụ
Cung cấp trang tổng quan cá nhân hóa giúp người dùng theo dõi ngay số dư token còn lại, hạn mức trong ngày, ngày hết hạn gói, thống kê số lần tạo âm thanh, biểu đồ hoạt động 7 ngày qua, tỷ lệ thành công và phân bổ các giọng đọc đã dùng.

### 2. Đặc Tả Giao Diện (UI Components)

1. **Header Chào Mừng:**
   * Bên trái:
     * Tiêu đề: **Xin chào, `<username>`** (VD: `Xin chào, sondn2010f`, `24px`, Bold).
     * Ngày hiện tại (định dạng tiếng Việt): `Chủ Nhật, 1 tháng 11` (`13px`, `#9CA3AF`).
   * Bên phải: Nút Refresh `↻` để cập nhật số liệu mới nhất.

2. **Hero Card — Tổng Quan Số Dư Token:**
   * Khung Card lớn tràn ngang (`background: #13131C`, `border: 1px solid #262636`, `padding: 24px`):
   * Dòng nhãn trên: `Token còn lại` + Badge `[GÓI DÙNG THỬ]` (nền tím nhạt, chữ tím in hoa `11px`).
   * Dòng số liệu chính:
     * Số dư hiện tại cỡ rất lớn (`40px`, Bold, `#FFFFFF`): **140.574**
     * Tổng hạn mức gói kế bên (`16px`, `#6B7280`): `/ 150.000 token`
   * Thanh Progress Bar ngang: Chiều cao `8px`, bo tròn, màu tím `#7C5CFC` thể hiện tỷ lệ `140.574 / 150.000` (~93.7% còn lại).
   * Dòng thông tin phụ dưới thanh tiến trình:
     * `Còn hôm nay:` **50.000** (chữ trắng đậm)
     * Cách một khoảng `16px`: `Hết hạn:` **6/11/2026** (chữ trắng đậm)
   * Bên phải Card (căn giữa theo chiều dọc): Nút nền tím `[💳 Quản lý gói]` (Click chuyển hướng sang `/billing`).

3. **Hàng 4 Thẻ Chỉ Số KPI (4-Column Metric Grid):**
   * **Thẻ 1 — `Lần tạo hôm nay`:**
     * Con số chính: `0` (`28px`, Bold).
     * Dòng phụ: `1 lần trong 7 ngày`.
     * Biểu đồ Sparkline mini (7 cột dọc tương ứng 7 ngày gần nhất) nằm ở góc phải dưới của thẻ.
   * **Thẻ 2 — `Lần tạo tháng này`:**
     * Con số chính: `0` (`28px`, Bold).
     * Dòng phụ: `tháng 11 năm 2026` (tháng và năm hiện tại).
   * **Thẻ 3 — `Tổng audio đã tạo`:**
     * Con số chính: `2m 27s` (Định dạng `<phút>m <giây>s`).
     * Dòng phụ: `1 bản ghi thành công`.
   * **Thẻ 4 — `Tỷ lệ thành công`:**
     * Con số chính: `100%`.
     * Dòng phụ: `Chưa lần nào thất bại` (Nếu có lỗi thì hiển thị `<N> lần thất bại`).

4. **Hàng Giữa — Biểu Đồ Hoạt Động & Bản Ghi Gần Đây (Grid 2 cột `62% : 38%`):**
   * **Cột trái — Card `Hoạt động hằng ngày (7 ngày qua)`:**
     * Header trái: Tiêu đề **Hoạt động hằng ngày (7 ngày qua)** + Phụ đề `1 lần tạo trong 7 ngày qua`.
     * Header phải (Legend): Chấm vuông tím `Thành công` (`#7C5CFC`) và chấm vuông đỏ `Thất bại` (`#EF4444`).
     * Biểu đồ cột (Bar Chart): Trục X hiển thị 7 nhãn ngày tính tới hiện tại (`Thứ 2`, `Thứ 3`, `Thứ 4`, `Thứ 5`, `Thứ 6`, `Thứ 7`, `Hôm nay` - chữ **Hôm nay** in đậm sáng).
   * **Cột phải — Card `Bản ghi gần đây`:**
     * Header trái: **Bản ghi gần đây** + Phụ đề *Nghe lại thứ bạn vừa tạo*.
     * Header phải: Link `Xem tất cả` màu tím `#8B5CF6` (Click điều hướng tới `/library/voices`).
     * Danh sách các bản ghi gần nhất: Nút `[▶]` + Trích đoạn văn bản + Dòng phụ `Minh Quân · 2m 26s · 30–10`.

5. **Hàng Dưới Cùng — Phân Bổ Theo Giọng & Thao Tác Nhanh (Grid 2 cột `55% : 45%`):**
   * **Cột trái — Card `Sử dụng theo giọng`:**
     * Tiêu đề: **Sử dụng theo giọng** (*Phân bổ theo giọng*).
     * Danh sách các giọng đọc đã sử dụng kèm số lần tạo ở góc phải và thanh progress bar màu tím bên dưới (VD: `Minh Quân` — `1`).
   * **Cột phải — Card `Thao tác nhanh`:**
     * Tiêu đề: **Thao tác nhanh** (*Đi tới tính năng*).
     * Lưới 2x2 các thẻ điều hướng nhanh:
       * **Phòng thu** (*Văn bản thành giọng nói*) — Khung viền tím nổi bật.
       * **Podcast** (*Nhiều giọng, một tập*).
       * **Truyện** (*Truyện nhiều nhân vật*).
       * **Lồng tiếng** (*Lồng tiếng video*).

---

## Phần B: Tài Khoản — Thanh Toán & Đăng Ký (`/billing`)

### 1. Mục Đích Nghiệp Vụ
Cho phép người dùng theo dõi chi tiết số dư token API, mua hoặc nâng cấp các gói token trả phí (Starter, Creator, Pro, Studio), áp dụng mã giảm giá khuyến mãi và mua bản quyền ứng dụng VieNeu trên máy tính (Desktop License).

### 2. Đặc Tả Giao Diện (UI Components)

1. **Header Trang:**
   * Tiêu đề: **Thanh toán & Đăng ký** (`22px`, Bold).
   * Phụ đề: *Quản lý gói dịch vụ, theo dõi mức sử dụng và cập nhật phương thức thanh toán.*

2. **Banner Chương Trình Khuyến Mãi (Promo Code Banner):**
   * Khung bo góc viền tím `rgba(124, 92, 252, 0.4)`, nền tím đen `rgba(124, 92, 252, 0.08)`, padding `14px 18px`.
   * Icon nhãn giá `🏷️` màu tím bên trái.
   * Dòng 1: **Ưu đãi Thịnh Vượng — Nhập mã `THINHVUONG` giảm ngay 15%** (Chữ `THINHVUONG` màu tím sáng nổi bật).
   * Dòng 2: *Áp dụng cho gói CREATOR, PRO, STUDIO · mỗi tài khoản 1 lần · HSD đến hết 31/12 · số lượng có hạn* (`12px`, `#9CA3AF`).

3. **Khu Vực Trạng Thái Hiện Tại (Grid 2 Cột `50% : 50%`):**
   * **Card Trái — `📦 Số dư token API`:**
     * Dòng 1: `Còn lại` (bên trái) — **140.574 / 150.000** (bên phải, font monospace đậm).
     * Thanh tiến trình chính: Màu tím `#7C5CFC`.
     * Dòng 2: `6% đã dùng` (bên trái) — Badge `[Dùng thử]` nền xanh lá đậm `#065F46`, chữ xanh lá sáng `#34D399` (bên phải).
     * Dòng 3 (Hạn mức ngày): `Hằng ngày` (bên trái) — `50.000 còn lại` (bên phải) kèm thanh tiến trình mỏng bên dưới.
     * Dòng 4: `Hết hạn:` **6/11/2026**.
     * Nút CTA dưới đáy Card: Nút full-width nền tím `#7C5CFC` `[↑ Nâng cấp gói token]`.
   * **Card Phải — `💻 Bản quyền app máy tính`:**
     * Header: Icon Laptop màu tím + **Bản quyền app máy tính**.
     * Nội dung trung tâm (Empty license state):
       * Icon Laptop lớn màu xám mờ (`48x48px`).
       * Dòng chính: **Chưa có bản quyền app máy tính** (`15px`, Bold).
       * Dòng phụ: *Mua bản quyền để dùng ứng dụng VieNeu trên máy tính.*
       * Nút CTA: `[🛒 Xem gói bản quyền]` (Nền tím `#7C5CFC`, bo góc `8px`).

4. **Khu Vực Bảng Giá `📦 Gói token API` (Pricing Tiers):**
   * Header: Icon khối lập phương tím + **Gói token API**.
   * Mô tả: *Mua hoặc nâng cấp số dư token để truy cập API TTS. Bạn có thể nâng cấp bất cứ lúc nào — token chưa dùng sẽ được hoàn theo tỉ lệ.*
   * **Bảng thông số chi tiết các Gói Token:**

| Thông số | Gói **Starter** | Gói **Creator** | Gói **Pro** | Gói **Studio** *(Gói cao cấp)* |
| :--- | :--- | :--- | :--- | :--- |
| **Tên gói** | **Starter** | **Creator** | **Pro** | **Studio** |
| **Tagline** | Gói khởi đầu — hạn dùng 6 tháng | Cho nhà sáng tạo nội dung | Phổ biến nhất — đơn giá tốt | Cho studio & doanh nghiệp |
| **Giá niêm yết** | **99.000 ₫** | **299.000 ₫** | **799.000 ₫** | Theo cấu hình Admin |
| **Số lượng Token** | `400.000 token` | `1.500.000 token` | `5.000.000 token` | Theo cấu hình Admin |
| **Thời lượng quy đổi** | `≈ 2 giờ âm thanh · đã tính theo đơn giá V4` | `≈ 7.5 giờ âm thanh · đã tính theo đơn giá V4` | `≈ 25 giờ âm thanh · đã tính theo đơn giá V4` | Theo đơn giá V4 (`200k token/giờ`) |
| **Thời hạn sử dụng** | `Hiệu lực 6 tháng` | `Hiệu lực 6 tháng` | `Hiệu lực 6 tháng` | `Hiệu lực 6 tháng` |
| **Khuyến mãi `THINHVUONG`** | Không áp dụng | Giảm 15% (còn `254.150 ₫`) | Giảm 15% (còn `679.150 ₫`) | Giảm 15% |
| **Thành phần Voucher** | Ô `Mã giảm giá` + Nút `[Áp dụng]` | Ô `Mã giảm giá` + Nút `[Áp dụng]` | Ô `Mã giảm giá` + Nút `[Áp dụng]` | Ô `Mã giảm giá` + Nút `[Áp dụng]` |

### 3. Logic Nghiệp Vụ Thanh Toán & Gói Cước
1. **Công thức quy đổi Thời lượng âm thanh V4:**
   * Chuẩn hệ thống: `200.000 token = 1 giờ âm thanh V4` (`3.600 giây`).
   * Mọi hiển thị thời lượng ước tính trên bảng giá được tính tự động: `estimated_hours = plan_tokens / 200000`.
2. **Logic Hoàn trả theo tỷ lệ khi Nâng cấp (Pro-rata Credit Calculation):**
   * Khi người dùng đang ở gói trả phí $A$ (còn hạn và còn dư $T_{	ext{unused}}$ token thực mua) và nâng cấp lên gói $B$:
     * Giá trị hoàn lại (Credit) hoặc số token cộng dồn được bảo lưu theo tỷ lệ phần chưa sử dụng để người dùng không bị mất quyền lợi.
3. **Logic Kiểm tra Mã giảm giá (`POST /api/v1/billing/vouchers/validate`):**
   * Kiểm tra `code` (không phân biệt hoa/thường, tự động `trim()` và `toUpperCase()`).
   * Kiểm tra `applicable_plans`: Ví dụ mã `THINHVUONG` chỉ hợp lệ cho `['CREATOR', 'PRO', 'STUDIO']`. Nếu người dùng bấm `Áp dụng` ở thẻ `Starter`, hiển thị thông báo lỗi màu đỏ ngay dưới ô input của thẻ `Starter`: *"Mã THINHVUONG chỉ áp dụng cho gói Creator, Pro, Studio."*
   * Kiểm tra giới hạn mỗi tài khoản 1 lần (`user_voucher_usages`) và ngày hết hạn (`2026-12-31T23:59:59+07:00`).
