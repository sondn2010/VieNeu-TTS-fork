# 03. Đặc Tả Phân Hệ Podcast Studio & Phòng Thu Truyện (Multi-Voice Studios)

* **Tham chiếu hình ảnh:**
  * Podcast Studio: `../assets/screens/03_podcast_studio.png` (`image_466b9f.png`)
  * Phòng thu Truyện: `../assets/screens/04_phong_thu_truyen_story_studio.png` (`image_4668b9.png`)
* **Routes:** `/podcast` và `/stories`

---

## Phần A: Phân Hệ Podcast Studio (`/podcast`)

### 1. Mục Đích Nghiệp Vụ
Cho phép người dùng tạo một tập Podcast hoàn chỉnh với nhiều người dẫn/khách mời (`Host`, `Guest`...) đối thoại tự nhiên. Người dùng có thể tự nhập từng lượt thoại, dán kịch bản có sẵn hoặc dùng AI tự động viết kịch bản, sau đó hệ thống tổng hợp và ghép thành một tập âm thanh duy nhất.

### 2. Đặc Tả Giao Diện (UI Components)

#### 2.1. Header & Thanh Công Cụ Kịch Bản
* **Header:**
  * Bên trái: Icon Podcast màu tím + Tiêu đề **PODCAST** (`16px`, in hoa, đậm) + Badge đếm số lượt hiện tại `2 lượt thoại`.
  * Bên phải: Nút `[⚙️ Cài đặt]` (chỉnh khoảng nghỉ giữa các lượt thoại, nhạc dạo đầu/kết thúc) và nút `[?]` (Hướng dẫn).
* **Thanh công cụ Khởi tạo Kịch bản:**
  * Nút `[📋 Dán kịch bản]`: Mở modal cho phép dán văn bản hội thoại nhiều dòng (ví dụ định dạng `Host: Xin chào... 
 Guest: Chào bạn...`) để hệ thống tự động bóc tách thành các thẻ lượt thoại tương ứng.
  * Nút `[✨ Viết kịch bản bằng AI]`: Mở modal cho phép người dùng nhập chủ đề, phong cách, số lượng nhân vật và độ dài mong muốn để LLM sinh kịch bản phân vai tự động.
  * Nhãn phụ kế bên: `hoặc thêm từng lượt bên dưới`.
* **Thanh Giới hạn & Nút Thêm Lượt:**
  * Bên trái: `2 LƯỢT THOẠI · tối đa 200 lượt mỗi podcast · gói trả phí: 1000 lượt`.
  * Bên phải: Nút `[+ Thêm lượt]` (Viền tím `#7C5CFC`, nền tím nhạt).

#### 2.2. Danh sách Thẻ Lượt Thoại (Dialogue Turn Cards)
Mỗi lượt thoại là một Card bo góc (`background: #13131C`, `border: 1px solid #262636`, `padding: 14px`):
* **Thanh điều khiển trên của mỗi lượt thoại:**
  * **Badge số thứ tự:** Hình tròn `24x24px` nền tím đậm, chữ tím sáng (`1`, `2`, `3`...).
  * **Ô nhập Tên nhân vật/Vai trò:** Input nhỏ (`width: ~120px`), mặc định lượt 1 là `Host`, lượt 2 là `Guest`.
  * **Dropdown Chọn Giọng Đọc:** Mặc định lượt 1 là `Ngọc Lan v`, lượt 2 là `Minh Quân v`.
  * **Dropdown Chọn Phong Cách (Style):** Mặc định `Tự nhiên v`.
  * **Nút Xóa lượt thoại `[🗑️]`:** Nằm ở góc phải cùng của thanh điều khiển lượt thoại.
* **Ô nhập Nội dung lượt thoại:**
  * `Textarea` (`min-height: 68px`, có thể kéo giãn chiều cao), placeholder: `Nội dung lượt thoại...`
* **Thanh chèn Cảm xúc của lượt thoại:**
  * Nằm ngay dưới `Textarea` của từng lượt: `[Cười]`, `[Thở dài]`, `[Hắng giọng]` (bấm vào sẽ chèn tag cảm xúc vào đúng lượt thoại đó).

#### 2.3. Thanh Hành Động & Lịch Sử "PODCAST ĐÃ TẠO"
* **Thanh Hành động dưới danh sách lượt thoại:**
  * Bên trái: Hiển thị hạn mức `Còn 50,000 ký tự hôm nay` (font monospace).
  * Bên phải: Nút chính `[🎙️ Tạo podcast]` (Nền tím `#7C5CFC`, chiều cao `42px`).
* **Khu vực `PODCAST ĐÃ TẠO`:**
  * Header: Icon lịch sử + `PODCAST ĐÃ TẠO` + Nút làm mới `↻`.
  * **Empty State (Khi chưa có tập podcast nào):**
    * Hiển thị icon khung hội thoại mờ ở trung tâm, dòng tiêu đề **Chưa có podcast nào** và dòng mô tả phụ *Ghép nhiều giọng thành một tập podcast ở trên*.

### 3. Logic Nghiệp Vụ Podcast Studio
1. **Kiểm tra giới hạn lượt thoại:**
   * Tài khoản gói Dùng thử (`TRIAL`) / Cơ bản: Tối đa `200` lượt thoại mỗi podcast.
   * Tài khoản gói Trả phí (`CREATOR`, `PRO`, `STUDIO`): Tối đa `1.000` lượt thoại mỗi podcast.
   * Khi thêm lượt mới bằng nút `[+ Thêm lượt]`, hệ thống tự động luân phiên vai và giọng đọc dựa trên 2 lượt gần nhất (ví dụ nếu lượt 1 là `Host - Ngọc Lan`, lượt 2 là `Guest - Minh Quân`, thì bấm thêm lượt 3 sẽ tự động gán mặc định `Host - Ngọc Lan` để tiết kiệm thao tác cho người dùng).
2. **Xử lý ghép nối âm thanh (Audio Stitching):**
   * Khi bấm `[🎙️ Tạo podcast]`, Backend kiểm duyệt toàn bộ các lượt thoại, tổng hợp âm thanh song song (worker pool) cho từng lượt, chuẩn hóa độ lớn âm thanh (`-16 LUFS` chuẩn podcast) và chèn khoảng nghỉ tự nhiên (`300ms - 500ms`) giữa các lượt trước khi xuất ra 1 file `.mp3` hoàn chỉnh.

---

## Phần B: Phân Hệ Phòng Thu Truyện (`/stories` — Multi-Voice Story Studio)

### 1. Mục Đích Nghiệp Vụ
Khác với Podcast (tạo một lần theo kịch bản ngắn), **Phòng thu Truyện** được thiết kế cho các dự án truyện dài kỳ / Audiobook nhiều nhân vật. Điểm cốt lõi của phân hệ này là **quản lý theo Dự án (Project-based)** và **tổng hợp độc lập từng phân đoạn (Segment-level synthesis)**: người dùng sửa đoạn nào chỉ cần tạo lại giọng cho đúng đoạn đó mà không làm ảnh hưởng hay tốn lại token của các đoạn khác, có thể kéo-thả sắp xếp lại thứ tự và xuất ra **MỘT file âm thanh liền mạch**.

### 2. Đặc Tả Giao Diện (UI Components)

#### 2.1. Cột Quản Lý Danh Sách Dự Án Truyện (Left Sub-Sidebar `width: 250px`)
* **Header:** Icon quyển sách mở màu tím + Tiêu đề **Dự án truyện**.
* **Nút Tạo Dự Án:** Nút full-width `[+ Truyện mới]` (Nền tím đậm `rgba(124, 92, 252, 0.2)`, viền tím, chữ tím sáng).
* **Danh sách Dự án:**
  * Hiển thị danh sách các dự án truyện của người dùng.
  * Mỗi mục hiển thị:
    * Dòng 1: Tên dự án (VD: **Truyện mới**).
    * Dòng 2: Phiên bản engine + Số phân đoạn hiện có (VD: `V4 · 0 đoạn`).

#### 2.2. Màn Hình Giới Thiệu & Hướng Dẫn Quy Trình 5 Bước (Story Studio Onboarding Workspace)
Khi người dùng mở mục `Truyện` hoặc chọn một dự án chưa có phân đoạn, vùng làm việc chính hiển thị:
* **Hero Section:**
  * Icon Quyển sách mở cỡ lớn kèm badge `[✨ MỚI]` màu tím.
  * Tiêu đề chính: **Phòng thu Truyện** (`24px`, Bold).
  * Mô tả: *"Tạo một câu chuyện nhiều giọng: mỗi nhân vật một giọng riêng, viết từng lời thoại, tạo và chỉnh sửa từng đoạn, rồi xuất ra MỘT file âm thanh liền mạch."*
* **Khung quy trình chuẩn `📖 CÁCH TẠO TRUYỆN NHIỀU GIỌNG`:**
  Hiển thị 5 bước đánh số tròn màu tím từ `1` đến `5`:
  1. **`👥 Thêm nhân vật`**: *Mỗi nhân vật (người kể, Phương, Long...) gán một giọng riêng. Có thể gắn màu để dễ phân biệt.*
  2. **`✍️ Viết từng phân đoạn`**: *Chọn nhân vật rồi nhập lời thoại cho từng đoạn. Giọng "tự nhiên" có thể chèn cảm xúc như [cười].*
  3. **`🔊 Tạo giọng từng đoạn`**: *Bấm "Tạo giọng" cho mỗi đoạn. Sửa đoạn nào chỉ cần tạo lại đoạn đó, không ảnh hưởng đoạn khác.*
  4. **`⠿ Sắp xếp thứ tự`**: *Kéo-thả các đoạn bằng biểu tượng `⠿` để đổi thứ tự kể chuyện.*
  5. **`🎬 Xuất truyện`**: *Ghép tất cả thành MỘT file liền mạch. Bấm play ở danh sách để nghe lại bất cứ lúc nào.*
* **Nút CTA dưới cùng:** Nút lớn nền tím `#7C5CFC` `[+ Truyện mới]`.

### 3. Đặc Tả Kỹ Thuật Chi Tiết Cho Màn Hình Biên Tập Truyện (Story Editor Workspace)
Để đội ngũ Frontend & Backend lập trình hoàn chỉnh toàn bộ 5 bước nghiệp vụ đã mô tả trên giao diện:

1. **Thanh Quản lý Nhân vật (Character Bar):**
   * Cho phép tạo danh sách nhân vật của bộ truyện:
     * `name`: Tên nhân vật (VD: `Người kể`, `Phương`, `Long`).
     * `voice_id`: Giọng đọc được gán cố định cho nhân vật đó.
     * `color_hex`: Mã màu đại diện (VD: Tím `#8B5CF6`, Xanh dương `#3B82F6`, Xanh lá `#10B981`, Cam `#F59E0B`, Hồng `#EC4899`) để hiển thị viền/badge phân biệt nhanh các lời thoại.
2. **Danh sách Phân đoạn Kéo-Thả (Draggable Segment List):**
   * Mỗi phân đoạn (`Segment Row`) bao gồm:
     * **Drag Handle (`⠿`):** Cho phép kéo-thả thay đổi vị trí đoạn văn trong truyện.
     * **Character Selector:** Chọn nhân vật nói đoạn này (tự động kế thừa giọng đọc và màu sắc của nhân vật).
     * **Segment Textarea:** Nhập lời dẫn hoặc lời thoại; hỗ trợ chèn tag cảm xúc `[cười]`, `[thở dài]`, `[hắng giọng]` nếu giọng thuộc nhóm hỗ trợ biểu cảm "tự nhiên".
     * **Nút `[🔊 Tạo giọng]` & Mini Audio Player `[▶]`:**
       * Khi đoạn chưa tạo âm thanh: Hiển thị nút `[Tạo giọng]`.
       * Khi đoạn đã tạo xong (`status = READY`): Hiển thị nút `[▶]` để nghe lại ngay đoạn đó.
       * Nếu người dùng sửa nội dung văn bản hoặc đổi nhân vật của một đoạn đã tạo âm thanh: Đổi trạng thái đoạn đó sang `MODIFIED` (hiện nút `[↻ Tạo lại giọng]`), trong khi các đoạn khác vẫn giữ nguyên file audio đã tạo.
3. **Tính năng `[🎬 Xuất truyện]` (Seamless Audio Merge):**
   * Kiểm tra tất cả các phân đoạn trong dự án đã ở trạng thái `READY` chưa (nếu còn đoạn chưa tạo giọng hoặc vừa sửa chưa tạo lại, nhắc người dùng tạo giọng cho các đoạn đó trước).
   * Gọi API `POST /api/v1/stories/:projectId/export`: Backend dùng `ffmpeg` nối toàn bộ file audio của các phân đoạn theo đúng thứ tự `sort_order` hiện tại thành **1 file âm thanh duy nhất** và trả về trình phát chính ở danh sách để người dùng nghe lại hoặc tải xuống bất cứ lúc nào.
