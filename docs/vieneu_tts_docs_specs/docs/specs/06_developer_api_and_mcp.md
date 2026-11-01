# 06. Đặc Tả Phân Hệ API Nhà Phát Triển & Tích Hợp MCP (Developer Portal)

* **Tham chiếu hình ảnh:** `../assets/screens/09_api_nha_phat_trien_mcp.png` (`image_4664f4.png`)
* **Route:** `/developer`

---

## 1. Mục Đích Nghiệp Vụ
Cung cấp cổng quản lý dành cho lập trình viên để tạo và quản lý khóa API (`Live` và `Test`), theo dõi lịch sử gọi API, tra cứu tài liệu tích hợp RESTful API (`/v1`), và cấu hình kết nối **MCP (Model Context Protocol)** để sử dụng trực tiếp giọng đọc VieNeu bên trong Claude, ChatGPT, Cursor và Claude Code.

---

## 2. Đặc Tả Giao Diện (UI Components)

### 2.1. Header & Hiển Thị Số Dư Token
* **Bên trái:**
  * Tiêu đề: **API Nhà phát triển** (`22px`, Bold).
  * Phụ đề: *Tích hợp VieNeu vào ứng dụng của bạn* (`13px`, `#9CA3AF`).
* **Bên phải:**
  * Khung Pill hiển thị số dư token hiện tại (`background: #13131C`, `border: 1px solid #262636`, `padding: 8px 14px`, `border-radius: 8px`):
  * Icon đồng xu/vòng tròn tím `🪙` + `Còn lại:` **140.574** `/ 150.000`.

### 2.2. Thanh Điều Hướng Tab (Developer Sub-Tabs)
Nằm bên dưới Header, có đường viền đáy `#262636`:
1. **`[🔑 API Keys]`** (Tab mặc định đang mở — chữ trắng, gạch chân màu tím `#7C5CFC` dày `2px`).
2. **`[📊 Sử dụng]`** (Hiển thị biểu đồ lượng request API, bảng log các lần gọi `/v1/tts`, mã trạng thái HTTP và số token đã trừ).
3. **`[📄 Tài liệu]`** (Hiển thị hướng dẫn tích hợp API, cURL mẫu, danh sách `voice_id`, cấu hình tham số và mã lỗi).

### 2.3. Khối "Tạo khóa mới" (Create API Key Card)
* Khung Card (`max-width: 680px`, `background: #13131C`, `border: 1px solid #262636`, `border-radius: 10px`, `padding: 20px`):
* Tiêu đề khối: **Tạo khóa mới** (`14px`, Bold).
* **Bộ chọn Môi trường (Environment Selector):**
  * Nút `[⚡ Live]` (Active: nền tím đậm `rgba(124, 92, 252, 0.2)`, viền `#7C5CFC`, chữ tím sáng).
  * Nút `[🧪 Test]` (Inactive: nền `#1A1A24`, viền `#262636`, chữ xám).
* **Hàng Nhập tên & Nút Tạo:**
  * Ô Input (`flex: 1`): Placeholder `Ví dụ: Khóa ứng dụng của tôi`.
  * Nút `[+ Tạo khóa]`: Nền tím `#7C5CFC`, chữ trắng. Khi ô input tên khóa đang rỗng, nút ở trạng thái mờ (`opacity: 0.5`, `disabled`).

### 2.4. Danh Sách Khóa API Hiện Có (API Keys List & Filter Tabs)
* **Thanh Tab lọc danh sách khóa:**
  * `[⚡ Live]` (Active - gạch chân tím) | `[🧪 Test]`
* **Trạng thái Trống (Empty State):**
  * Icon chìa khóa bị gạch chéo mờ ở chính giữa.
  * Dòng thông báo: `Chưa có khóa API. Tạo một khóa ở trên để bắt đầu.` (`13px`, `#6B7280`).
* **Trạng thái Có dữ liệu (Khi đã tạo khóa):**
  * Hiển thị danh sách các khóa thuộc tab đang chọn (`Live` hoặc `Test`):
    * Tên khóa (VD: `Khóa ứng dụng của tôi`)
    * Chuỗi khóa rút gọn (`vn_live_8f92...a1b2` hoặc `vn_test_3c41...99e0`)
    * Thời gian tạo & Lần sử dụng gần nhất
    * Nút `[🗑️ Thu hồi]` (Revoke key).

### 2.5. Khối Tích Hợp MCP — "Dùng VieNeu trong Claude, ChatGPT"
* Khung Card (`max-width: 680px`, `background: #13131C`, `border: 1px solid #262636`, `border-radius: 10px`, `padding: 20px`, `margin-top: 24px`):
* **Tiêu đề:** **Dùng VieNeu trong Claude, ChatGPT** (`14px`, Bold).
* **Mô tả:** *Thêm địa chỉ này làm connector, đăng nhập VieNeu, rồi nhờ trợ lý đọc văn bản bằng giọng bạn chọn.*
* **Hàng Địa chỉ MCP Endpoint:**
  * Ô hiển thị URL (Read-only, nền `#0B0B10`, viền `#262636`, font monospace `13px`, chữ trắng):
    `https://api.vieneu.io/mcp`
  * Nút `[📋 Sao chép]` bên phải (`background: #1A1A24`, `border: 1px solid #2E2E42`, click để copy URL vào clipboard).
* **Dòng hướng dẫn cấu hình nhanh:**
  * `Trong Claude: Customize → Connectors → "Add custom connector". ChatGPT, Cursor, Claude Code: ` + Link gạch chân `xem hướng dẫn`.
* **Khu vực `ỨNG DỤNG ĐÃ KẾT NỐI` (Connected MCP Clients):**
  * Nhãn tiêu đề: `ỨNG DỤNG ĐÃ KẾT NỐI` (`11px`, in hoa, `#6B7280`, `letter-spacing: 0.05em`).
  * Khi chưa có ứng dụng kết nối: Hiển thị `Chưa có ứng dụng nào.` (`13px`, `#6B7280`).
  * Khi đã kết nối (qua OAuth 2.0 / MCP Auth flow): Hiển thị tên ứng dụng (VD: `Claude Desktop`, `Cursor`), thời점 kết nối và nút `[Ngắt kết nối]`.

---

## 3. Logic Nghiệp Vụ & Bảo Mật API / MCP

1. **Quy chuẩn sinh và lưu trữ API Key:**
   * Khóa `Live` có tiền tố `vn_live_` + 32 ký tự ngẫu nhiên an toàn mật mã (`crypto.randomBytes`).
   * Khóa `Test` có tiền tố `vn_test_` + 32 ký tự ngẫu nhiên.
   * **Bảo mật:** Backend chỉ lưu giá trị băm `SHA-256` (`key_hash`) và 8 ký tự đầu (`key_prefix`) vào cơ sở dữ liệu. Chuỗi khóa đầy đủ chỉ được trả về **duy nhất 1 lần** trong response của `POST /api/v1/developer/keys` để hiển thị trong Modal cho người dùng sao chép.
2. **Sự khác biệt giữa API `/v1` và Giao diện Web:**
   * Như được quy định tại màn hình *Từ điển phát âm*, các request gọi qua Developer API (`/v1/...`) **không tự động áp dụng** bảng *Từ điển phát âm* của tài khoản web (để đảm bảo tính nguyên bản của payload do lập trình viên tự kiểm soát ở phía ứng dụng tích hợp).
3. **Giao thức MCP (`https://api.vieneu.io/mcp`):**
   * Triển khai MCP Server hỗ trợ chuẩn SSE / Streamable HTTP kết hợp OAuth2 để các AI Assistant (Claude, ChatGPT, Cursor, Claude Code) có thể gọi tool `vieneu_list_voices` và `vieneu_text_to_speech` dưới quyền tài khoản của người dùng đã đăng nhập.
