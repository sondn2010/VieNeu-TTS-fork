# 02. Đặc Tả Phân Hệ Phòng Thu (TTS Studio — Đơn Giọng)

* **Tham chiếu hình ảnh:** `../assets/screens/02_phong_thu_tts_studio.png` (`image_466bd7.png`)
* **Route:** `/studio`

---

## 1. Mục Đích Nghiệp Vụ
**Phòng thu (TTS Studio)** là màn hình làm việc trung tâm của người dùng để chuyển đổi văn bản thành giọng nói đơn lẻ. Màn hình hỗ trợ chọn giọng đọc, điều chỉnh tốc độ, chèn biểu cảm phi ngôn ngữ (cười, thở dài, hắng giọng), ghép nhạc nền, tự động đọc công thức Toán/Hóa học, phát thử độ trễ thấp (`Phát ngay`) hoặc xuất bản ghi chất lượng cao (`Tạo giọng nói`).

---

## 2. Đặc Tả Chi Tiết Giao Diện (UI Components)

### 2.1. Thanh Công Cụ Điều Khiển Trên Cùng (Studio Top Toolbar)
Nằm trong một khung ngang bo góc (`background: #13131C`, `border: 1px solid #262636`, `padding: 8px 14px`), chia làm 2 cụm trái và phải:

1. **Cụm điều khiển bên trái:**
   * **Bộ chọn Giọng nói (Voice Selector Button):**
     * Hiển thị Avatar tròn màu tím có chữ viết tắt (`MQ`), nhãn phụ phía trên `GIỌNG NÓI` (`10px`, in hoa, màu xám), tên giọng đang chọn `Minh Quân` (`14px`, đậm, màu trắng) và icon mũi tên kép `^v`.
     * Click vào sẽ mở Modal/Popover danh sách giọng đọc (cho phép lọc theo Giới tính, Vùng miền, tìm kiếm tên giọng và nghe thử).
   * **Bộ chọn Tốc độ (Speed Selector):**
     * Nút chọn gồm icon đồng hồ tốc độ + nhãn `1x v`.
     * Các mức tốc độ hỗ trợ: `0.5x`, `0.75x`, `0.9x`, `1x` (mặc định), `1.1x`, `1.25x`, `1.5x`, `2.0x`.
   * **Cụm chèn Cảm xúc nhanh (Emotion Quick-Tags):**
     * Nhãn văn bản `Cảm xúc:` seguido bởi 3 nút pill (`background: #1E1E2A`, `border: 1px solid #2E2E42`):
       * `[Cười]`
       * `[Thở dài]`
       * `[Hắng giọng]`
   * **Bộ chọn Nhạc nền (Background Music Dropdown):**
     * Nút `♪ Nhạc nền v`: Cho phép chọn nhạc nền có sẵn theo chủ đề (Kể chuyện, Tin tức, Thư giãn, Sôi động...), tải lên file nhạc riêng hoặc tắt nhạc nền, kèm thanh trượt chỉnh âm lượng nhạc nền (Ducking/Volume mix).

2. **Cụm tiện ích bên phải:**
   * Nút `[↑ Tải tệp]`: Mở hộp thoại chọn file văn bản từ máy tính (`.txt`, `.docx`, `.srt`) để nạp nội dung vào vùng soạn thảo.
   * Nút `[📖 Từ điển ↗]`: Điều hướng hoặc mở cửa sổ *Từ điển phát âm* để người dùng thêm nhanh cách đọc từ viết tắt/tên riêng.
   * Nút `[?]`: Hiển thị Popover/Modal hướng dẫn mẹo viết văn bản, cách ngắt nghỉ và chèn cảm xúc.

### 2.2. Banner Thông Báo Tính Năng Mới (Math & Chemistry Announcement Banner)
* Nằm ngay dưới thanh công cụ, nền tím đậm `rgba(124, 92, 252, 0.12)`, viền `1px solid rgba(124, 92, 252, 0.35)`, bo góc `8px`.
* Bên trái: Icon Sigma toán học `Σ` màu tím sáng.
* Nội dung văn bản:
  > **Mới: VieNeu giờ đọc được cả công thức toán học và hoá học! Cứ gõ tự nhiên như ax² + bx + c = 0, Δ ≥ 0, x ∈ ℝ hay 2H2 + O2 → 2H2O — hệ thống tự nhận diện và đọc đúng.**
* Bên phải: Nút `X` để ẩn banner (lưu trạng thái `dismissed_math_chem_banner = true` vào `localStorage`).

### 2.3. Vùng Soạn Thảo Văn Bản Chính (Main Text Editor)
* Khung `Textarea` lớn (`min-height: 360px`), nền `#0E0E14`, viền `#262636`, chữ trắng `#F3F4F6` (`15px`, `line-height: 1.6`).
* Placeholder: `Nhập hoặc dán văn bản của bạn vào đây...`
* **Thanh gợi ý đáy vùng soạn thảo (Empty-state Helper Bar):**
  * Hiển thị ở chính giữa phía dưới bên trong khung soạn thảo khi người dùng chưa nhập văn bản (hoặc luôn ghim nhẹ ở đáy khung):
  * Nút `[✨ Chèn câu mẫu]` (Nền tím nhạt, viền tím `#7C5CFC`, chữ tím sáng): Khi bấm vào sẽ điền một câu mẫu đa dạng vào ô nhập.
  * Nhãn hướng dẫn kế bên: `hoặc kéo thả tệp .txt vào đây` (`13px`, màu `#6B7280`).
  * Hỗ trợ sự kiện `onDragOver` / `onDrop` trực tiếp trên khung `Textarea`: Khi người dùng kéo thả file `.txt` vào, hiển thị viền nét đứt màu tím và tự động đọc nội dung UTF-8 của file đưa vào ô soạn thảo.

### 2.4. Thanh Đếm Hạn Mức & Nút Hành Động (Bottom Action Bar)
* **Bên trái — Bộ đếm thời gian thực (Usage Counter Pill):**
  * Hiển thị trong khung bo góc nền `#14141D`, font monospace `12px`:
    `0 ký tự · ~0 token · còn 50.000`
  * Trong đó:
    * `0 ký tự`: Tổng số ký tự hiện có trong ô soạn thảo.
    * `~0 token`: Số token ước tính sẽ tiêu tốn cho lần tạo này.
    * `còn 50.000`: Hạn mức ký tự/token còn lại trong ngày hôm nay của tài khoản.
* **Bên phải — Cụm nút thực thi:**
  * Nút `[⚡ Phát ngay]`: Nền tối `#1A1A26`, viền `#2E2E42`, icon tia sét. Dùng để phát thử âm thanh trực tuyến (streaming) với độ trễ thấp.
  * Nút `[🔊 Tạo giọng nói]`: Nền tím chủ đạo `#7C5CFC`, icon sóng âm. Dùng để tổng hợp file âm thanh hoàn chỉnh và lưu vào danh sách bản ghi. (Khi ô văn bản đang rỗng `0 ký tự`, cả 2 nút ở trạng thái `disabled`/mờ).

### 2.5. Khu Vực "CÁC BẢN GHI GẦN ĐÂY" (Recent Recordings Section)
* **Header:**
  * Bên trái: Icon lịch sử `↺` + Tiêu đề `CÁC BẢN GHI GẦN ĐÂY` (`12px`, in hoa, đậm, `#9CA3AF`) + Badge số lượng `2`.
  * Bên phải: Nút làm mới danh sách `↻`.
* **Danh sách Card Bản ghi:**
  Mỗi bản ghi gồm:
  * **Nút Play tròn `[▶]`** (`36x36px`, nền `#1E1E2A`) ở bên trái. Khi bấm phát, chuyển thành icon Pause `[⏸]` và hiển thị thanh tiến trình phát âm thanh.
  * **Thông tin giữa:**
    * Dòng 1: Trích đoạn văn bản của bản ghi (1 dòng, cắt `...` ở cuối), ví dụ: `ó một sự thật kỳ lạ trong tâm lý con người — kể cả những người có phép thuật — là khi một mối đe dọa...`
    * Dòng 2: Tên giọng `Minh Quân` + Badge model `[V4]` (nền tím nhạt, chữ tím) · Thời lượng `146.0s` · Thời gian tạo `16:23 30/10/2026`.
  * **Cụm nút bên phải:**
    * Nút `[↑]` (Tải xuống / Chia sẻ file âm thanh).
    * Nút `[♪]` (Nền tím `#7C5CFC` - Chỉnh/ghép nhạc nền cho bản ghi đã tạo).

---

## 3. Logic Nghiệp Vụ & Xử Lý Kỹ Thuật (Business Rules)

1. **Cơ chế chèn Tag Cảm xúc tại vị trí con trỏ (`insertAtCursor`):**
   * Khi người dùng click vào `[Cười]`, `[Thở dài]`, hoặc `[Hắng giọng]`, hệ thống lấy vị trí `selectionStart` và `selectionEnd` hiện tại của `textareaRef`.
   * Chèn chuỗi tag chuẩn của Engine (ví dụ `[cười] `, `[thở dài] `, `[hắng giọng] `) vào đúng vị trí con trỏ, sau đó đặt lại focus và di chuyển con trỏ ra ngay sau tag vừa chèn.
2. **Công thức tính Token ước tính (`~token`):**
   * Cập nhật tức thì mỗi khi văn bản thay đổi (debounce `100ms` nếu văn bản trên 5.000 ký tự).
   * Kiểm tra ràng buộc:
     * Nếu `char_count == 0`: Disable nút `Phát ngay` và `Tạo giọng nói`.
     * Nếu `char_count > daily_char_remaining` hoặc `estimated_tokens > token_balance`: Đổi màu phần `còn 50.000` sang đỏ `#EF4444`, hiển thị tooltip báo vượt hạn mức và disable nút `Tạo giọng nói`.
3. **Đồng bộ danh sách Bản ghi gần đây:**
   * Ngay sau khi API `POST /api/v1/tts/generate` trả về thành công, bản ghi mới được đẩy lên đầu danh sách `CÁC BẢN GHI GẦN ĐÂY`, đồng thời trừ trực tiếp số dư token ở Sidebar (`140.574 / 150.000`) và hạn mức ngày (`còn 50.000`) mà không cần tải lại toàn trang.
