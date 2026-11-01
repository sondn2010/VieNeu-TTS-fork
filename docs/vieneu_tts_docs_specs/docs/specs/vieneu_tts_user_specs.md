# Tài Liệu Đặc Tả Kỹ Thuật & Chức Năng (Product & Technical Specifications)
**Hệ thống Quản lý & Tạo Giọng Nói AI Phía Người Dùng — VieNeu TTS Platform**
*Phiên bản: 1.0 | Ngày cập nhật: 01/11/2026 | Đối tượng: Đội ngũ phát triển (Frontend, Backend, AI Engine, QA)*

---

## 1. Tổng Quan Hệ Thống (System Overview)

**VieNeu** là nền tảng chuyển đổi văn bản thành giọng nói (Text-to-Speech - TTS) ứng dụng AI dành cho người dùng cuối và nhà phát triển. Hệ thống cung cấp bộ công cụ toàn diện từ phòng thu đơn giọng, sản xuất podcast đa giọng, dựng truyện nhiều nhân vật, quản lý thư viện âm thanh, bảng xếp hạng giọng nói cộng đồng, từ điển phát âm tùy chỉnh đến tích hợp API/MCP và thanh toán theo mô hình Token.

### 1.1. Danh sách các màn hình & Module trong phạm vi đặc tả
Tài liệu này được xây dựng trực tiếp từ 10 màn hình thiết kế UI/UX chuẩn của hệ thống:
1. **Global Layout & Navigation Sidebar**: Khung giao diện chung, thanh điều hướng, trạng thái tài khoản, đa ngôn ngữ và chế độ sáng/tối.
2. **Modal Điều Khoản Tạo Giọng Nói (Terms & AI Moderation Consent)**: Kiểm duyệt nội dung và xác nhận điều khoản trước khi tạo âm thanh.
3. **Phòng Thu (TTS Studio)**: Công cụ chuyển văn bản thành giọng nói đơn giọng (kèm cảm xúc, tốc độ, nhạc nền, đọc công thức Toán/Hóa).
4. **Podcast Studio**: Công cụ tạo kịch bản và ghép nối hội thoại đa giọng nói theo từng lượt thoại (turn-based).
5. **Phòng Thu Truyện (Story Studio)**: Quản lý dự án truyện nhiều giọng, phân vai nhân vật, kéo-thả phân đoạn và xuất file âm thanh liền mạch.
6. **Thư Viện Giọng Nói Của Tôi (My Voices / Audio History)**: Quản lý, tìm kiếm, lọc, nghe lại, tải xuống và xóa các bản ghi đã tạo.
7. **Bảng Xếp Hạng Giọng (Voice Leaderboard)**: Thống kê và xếp hạng các giọng đọc phổ biến nhất theo thời gian, giới tính và vùng miền.
8. **Bảng Điều Khiển (User Dashboard)**: Thống kê hạn mức token, biểu đồ hoạt động 7 ngày, tỷ lệ thành công, phân bổ giọng đọc và thao tác nhanh.
9. **Thanh Toán & Đăng Ký (Billing & Subscription)**: Quản lý số dư token API, bản quyền ứng dụng máy tính (Desktop App), mã giảm giá và các gói cước (Starter, Creator, Pro).
10. **API Nhà Phát Triển (Developer Portal & MCP)**: Quản lý API Keys (Live/Test), theo dõi mức sử dụng, tài liệu tích hợp và kết nối MCP (Claude, ChatGPT, Cursor).
11. **Từ Điển Phát Âm (Pronunciation Dictionary)**: Định nghĩa quy tắc đọc tên riêng, thuật ngữ, chữ viết tắt theo tài khoản và công cụ test trực tiếp.

---

## 2. Thiết Kế Giao Diện Chung & Hệ Thống Thiết Kế (UI/UX & Global Layout)

### 2.1. Bảng màu & Theme (Design Tokens)
Hệ thống mặc định sử dụng **Dark Mode** mang phong cách phòng thu hiện đại:
* **Background Primary (Nền chính):** `#0B0B0F` / `#0D0D12` (Đen ánh tím than sâu)
* **Background Secondary / Surface (Card, Sidebar, Input):** `#13131A` / `#181822`
* **Border / Divider:** `#262636` (Viền mảnh `1px solid`)
* **Primary Brand / Accent Color:** `#7C5CFC` / `#8B5CF6` (Tím Violet chủ đạo cho nút bấm chính, active state, progress bar, badge)
* **Text Primary:** `#F3F4F6` (Trắng sáng)
* **Text Secondary / Muted:** `#9CA3AF` / `#6B7280` (Xám trung tính cho nhãn phụ, placeholder, metadata)
* **Semantic Colors:**
  * **Success / Allowed (Xanh lá):** Text `#34D399`, Background `rgba(16, 185, 129, 0.1)`, Border `rgba(16, 185, 129, 0.3)`
  * **Danger / Prohibited / Notification Badge (Đỏ):** Text `#F87171`, Badge `#EF4444`, Background `rgba(239, 68, 68, 0.1)`, Border `rgba(239, 68, 68, 0.3)`
  * **Warning / Gold Rank #1 (Vàng cam):** `#F59E0B` / `#FBBF24`
  * **Silver Rank #2 (Bạc/Xám xanh):** `#94A3B8`
  * **Bronze Rank #3 (Đồng/Cam nâu):** `#D97706`

### 2.2. Thanh Điều Hướng Bên Trái (Left Sidebar Navigation)
Cố định bên trái (`width: ~240px`), chia thành các vùng rõ rệt:

1. **Header Logo:**
   * Icon sóng âm trên nền tím bo góc + Text thương hiệu **VieNeu** (font đậm, trắng).
2. **Nhóm menu `TẠO` (Creation Tools):**
   * `Phòng thu` (Icon: Microphone)
   * `Podcast` (Icon: Broadcast/Podcast, có chấm tím thông báo tính năng mới khi cần)
   * `Truyện` (Icon: Open Book, có chấm tím thông báo)
   * `Lồng tiếng` (Icon: Clapperboard/Video)
   * `Bài giảng` (Icon: Presentation/User-board, có chấm tím thông báo)
3. **Nhóm menu `THƯ VIỆN` (Library & Community):**
   * `Giọng nói` (Icon: Soundwave)
   * `Bảng xếp hạng` (Icon: Bar Chart)
   * `Nhân bản giọng` (Icon: Mic + Sparkle/Clone)
   * `Cộng đồng` (Icon: Chat Bubbles, có chấm tím)
   * `Tải ứng dụng` (Icon: Download Laptop)
4. **Nhóm menu `TÀI KHOẢN` (Account & Developer):**
   * `Bảng điều khiển` (Icon: Grid 4 ô)
   * `Thanh toán` (Icon: Credit Card)
   * `Nhà phát triển` (Icon: Code `< >`)
   * `Từ điển phát âm` (Icon: Chữ `A` kèm sóng âm)
5. **Khu vực Footer Sidebar (Cố định dưới đáy):**
   * **Widget Số dư Token** *(Hiển thị trên một số màn hình tạo nội dung như Phòng thu, Podcast)*: Icon ví + Nhãn `Số dư token` + Giá trị dạng `140.574 / 150.000` (font monospace).
   * **Thông báo (Notifications):** Icon Chuông + `Thông báo` + Badge số lượng chưa đọc nền đỏ (VD: `1`).
   * **Trợ giúp & Liên hệ:** Icon Message Question + `Trợ giúp & liên hệ`.
   * **Thanh công cụ Cài đặt giao diện:**
     * Nút chuyển đổi Theme (Icon Mặt trời / Mặt trăng).
     * Dropdown chọn Ngôn ngữ giao diện: `VI v` (Tiếng Việt / Tiếng Anh).
   * **User Profile Card:**
     * Avatar tròn viết tắt tên (VD: `SO` nền tím).
     * Email/Username cắt gọn bằng dấu `...` (VD: `sondn2010f@gmail...`).
     * Nhãn gói hiện tại ở dòng phụ (VD: `Gói Pro`).
     * Nút Đăng xuất (Icon mũi tên thoát `->]` bên phải).

### 2.3. Thanh Onboarding Checklist ("Bắt đầu") & Nút Chat Hỗ Trợ
* **Top Onboarding Bar** (Hiển thị phía trên cùng của vùng nội dung ở Phòng thu, Podcast):
  * Bên trái: Icon checklist + chữ **Bắt đầu** + Badge tiến độ `Đã xong 1/4` hoặc `Đã xong 2/4` + mũi tên mở rộng `v`.
  * Bên phải: Nút `X Ẩn` để đóng thanh hướng dẫn người mới.
* **Floating Action Button (Góc dưới cùng bên phải):**
  * Nút tròn màu tím (`#7C5CFC`) chứa icon Tai nghe hỗ trợ (Customer Support / Live Chat widget), luôn nổi (`fixed bottom-right`) trên mọi màn hình.

---

## 3. Đặc Tả Chi Tiết Từng Module Chức Năng

### 3.1. Module 1: Modal Điều Khoản Tạo Giọng Nói (Terms of Service & Moderation)
* **Tham chiếu hình ảnh:** `image_466c33.jpg`
* **Mục đích:** Buộc người dùng đọc và xác nhận quy định sử dụng trước khi thực hiện tạo giọng nói lần đầu (hoặc khi chính sách cập nhật), đồng thời thông báo về cơ chế AI kiểm duyệt tự động.

#### 3.1.1. Thành phần giao diện (UI Components)
* **Overlay:** Làm tối và mờ nền phía sau (`backdrop-filter: blur(4px)`, `background: rgba(0,0,0,0.7)`).
* **Modal Container:** Căn giữa màn hình, `max-width: ~520px`, bo góc `12px`, có thanh cuộn dọc (`scrollbar`) cho phần nội dung điều khoản.
* **Header:**
  * Icon Cán cân công lý (Scale of Justice) màu tím.
  * Tiêu đề chính: **Điều khoản tạo giọng nói**
  * Phụ đề: *Vui lòng đọc kỹ trước khi sử dụng*
* **Nội dung mô tả:**
  * Đoạn mở đầu: *"Trước khi tạo giọng nói, vui lòng đọc và đồng ý với các điều khoản sau. Mọi văn bản đều được hệ thống AI kiểm duyệt trước khi tạo."*
  * **Khối "Được phép" (Card viền xanh lá, nền xanh lá trong suốt):**
    * Tiêu đề: Icon Checkmark tròn xanh + **Được phép**
    * Nội dung: *"Nội dung hợp pháp, lịch sử cho mục đích cá nhân, giáo dục, kinh doanh, sáng tạo và giải trí."*
  * **Khối "Không được phép" (Card viền đỏ, nền đỏ trong suốt):**
    * Tiêu đề: Icon Cấm (`🚫`) đỏ + **Không được phép**
    * Danh sách gạch đầu dòng (`-`):
      1. *Ngôn từ tục tĩu mang tính lăng mạ, xúc phạm nghiêm trọng (ngôn ngữ đời thường vẫn được chấp nhận).*
      2. *Nội dung khiêu dâm hoặc gợi dục.*
      3. *Lăng mạ, bôi nhọ, phân biệt, kích động thù ghét hoặc quấy rối.*
      4. *Nội dung xuyên tạc, chống phá Nhà nước, Đảng, lãnh đạo hoặc chủ quyền quốc gia Việt Nam.*
      5. *Kêu gọi bạo lực, tự gây hại hoặc hành vi vi phạm pháp luật.*
* **Footer (Cố định dưới đáy Modal):**
  * Checkbox: `[v] Tôi đã đọc và đồng ý với các điều khoản trên.`
  * Button chính (Full-width, nền tím): **Đồng ý và tiếp tục**

#### 3.1.2. Logic nghiệp vụ & Xử lý (Business Rules)
1. **Trạng thái nút bấm:** Nút **Đồng ý và tiếp tục** chỉ được phép kích hoạt (`enabled`) khi Checkbox đã được tích chọn (`checked = true`). Nếu bỏ tích, nút chuyển sang trạng thái `disabled` (mờ, không click được).
2. **Lưu trữ trạng thái (Persistence):**
   * Khi người dùng bấm "Đồng ý và tiếp tục", gọi API cập nhật cờ `has_accepted_tts_terms = true` (kèm `terms_version` và `accepted_at` timestamp) trong bảng `users` (và cache tại `localStorage` để tránh hiển thị lại không cần thiết).
3. **Kiểm duyệt AI (AI Pre-moderation Pipeline):**
   * Trước khi gửi văn bản xuống TTS Engine ở bất kỳ module nào (Phòng thu, Podcast, Truyện), Backend phải chạy qua lớp **AI Content Moderation** kiểm tra 5 nhóm vi phạm nêu trên. Nếu vi phạm, trả về mã lỗi `422 CONTENT_POLICY_VIOLATION` kèm thông báo cụ thể và không trừ token của người dùng.

---

### 3.2. Module 2: Phòng Thu (TTS Studio - Đơn Giọng)
* **Tham chiếu hình ảnh:** `image_466bd7.png`
* **Mục đích:** Màn hình làm việc chính để chuyển đổi văn bản thành giọng nói đơn lẻ với đầy đủ tùy chỉnh giọng đọc, tốc độ, cảm xúc và nhạc nền.

#### 3.2.1. Thành phần giao diện (UI Components)
1. **Thanh công cụ điều khiển (Top Control Toolbar):**
   * **Bộ chọn Giọng nói (Voice Selector Pill):**
     * Hiển thị Avatar viết tắt (`MQ` nền tím), nhãn nhỏ `GIỌNG NÓI`, tên giọng đang chọn (`Minh Quân`) và icon mũi tên lên/xuống `^v` để mở modal/dropdown chọn giọng.
   * **Bộ chọn Tốc độ đọc (Speed Selector):**
     * Icon đồng hồ tốc độ + Giá trị hiện tại (`1x`) + mũi tên `v` (Cho phép chọn dải tốc độ như `0.5x`, `0.75x`, `1x`, `1.25x`, `1.5x`, `2.0x`).
   * **Nhóm nút chèn Cảm xúc (Emotion Tags):**
     * Nhãn `Cảm xúc:` đi kèm các nút bấm nhanh (Quick-insert pills): `[Cười]`, `[Thở dài]`, `[Hắng giọng]`.
   * **Bộ chọn Nhạc nền (Background Music Selector):**
     * Icon nốt nhạc `♪` + `Nhạc nền v` (Dropdown chọn nhạc nền có sẵn, tải nhạc lên hoặc tắt nhạc nền, kèm chỉnh âm lượng).
   * **Nhóm nút tiện ích (Bên phải Toolbar):**
     * Nút `[↑ Tải tệp]`: Cho phép chọn file văn bản (`.txt`, `.docx`, `.srt`...) từ máy tính để nạp vào ô soạn thảo.
     * Nút `[📖 Từ điển ↗]`: Mở nhanh trang hoặc popup *Từ điển phát âm* trong tab mới/modal.
     * Nút `[?]`: Mở hướng dẫn sử dụng Phòng thu.

2. **Banner Thông báo tính năng mới (Feature Announcement Banner):**
   * Nền tím đậm viền mảnh, icon Sigma `Σ` màu tím:
   * Nội dung: *"Mới: VieNeu giờ đọc được cả công thức toán học và hoá học! Cứ gõ tự nhiên như ax² + bx + c = 0, Δ ≥ 0, x ∈ ℝ hay 2H2 + O2 → 2H2O — hệ thống tự nhận diện và đọc đúng."*
   * Nút đóng `X` bên phải (lưu trạng thái đã đóng vào `localStorage`).

3. **Vùng Soạn Thảo Văn Bản (Main Text Editor):**
   * Textarea lớn, placeholder: *"Nhập hoặc dán văn bản của bạn vào đây..."*
   * Ở đáy bên trong vùng soạn thảo (khi chưa cuộn kín hoặc cố định góc dưới):
     * Nút `[✨ Chèn câu mẫu]`: Viền tím, bấm vào sẽ điền ngẫu nhiên một đoạn văn bản mẫu (bao gồm cả văn xuôi, cảm xúc hoặc công thức) để người dùng test thử ngay.
     * Chữ hướng dẫn kế bên: *"hoặc kéo thả tệp .txt vào đây"* (Hỗ trợ Drag & Drop file `.txt` trực tiếp vào vùng editor).

4. **Thanh Trạng Thái & Hành Động (Bottom Action Bar):**
   * **Bên trái (Counter Pill):** Hiển thị thông số thời gian thực theo định dạng:
     `0 ký tự · ~0 token · còn 50.000`
     *(Giải thích: Số ký tự hiện tại trong ô nhập · Ước tính số token tiêu thụ · Hạn mức ký tự/token còn lại trong ngày là 50.000).*
   * **Bên phải (Action Buttons):**
     * Nút phụ `[⚡ Phát ngay]`: Stream âm thanh trực tiếp (Low-latency preview/streaming) hoặc đọc nhanh.
     * Nút chính `[🔊 Tạo giọng nói]` (Nền tím): Gửi yêu cầu tổng hợp âm thanh chất lượng cao và lưu vào danh sách bản ghi.

5. **Khu vực "CÁC BẢN GHI GẦN ĐÂY" (Recent Recordings Section):**
   * Header: Icon đồng hồ ngược + `CÁC BẢN GHI GẦN ĐÂY` + Badge đếm số lượng (VD: `2`) + Nút Refresh `↻` ở góc phải.
   * Danh sách các Card bản ghi (hiển thị tối đa các bản ghi mới nhất trong phiên/gần đây):
     * Nút tròn `[▶]` (Play/Pause) bên trái.
     * **Dòng 1 (Title/Snippet):** Trích đoạn văn bản đã đọc (cắt gọn 1 dòng với `...`), VD: *"ó một sự thật kỳ lạ trong tâm lý con người — kể cả những người có phép thuật — là khi một mối đe dọa..."*
     * **Dòng 2 (Metadata):** Tên giọng (`Minh Quân`) + Badge phiên bản model (`V4` nền tím) · Thời lượng (`146.0s`) · Thời gian tạo (`16:23 30/10/2026`).
     * **Cụm nút hành động bên phải:**
       * Nút `[↑]` (Share / Export / Tải xuống).
       * Nút `[♪]` (Nền tím - Bật/tắt hoặc trộn nhạc nền / Mở trình chỉnh sửa âm thanh).

#### 3.2.2. Logic nghiệp vụ & Xử lý (Business Rules)
* **Chèn Tag cảm xúc:** Khi con trỏ chuột đang ở vị trí bất kỳ trong `Textarea`, bấm vào nút `Cười`, `Thở dài`, hoặc `Hắng giọng` sẽ chèn tag tương ứng (ví dụ `[cười]`, `[thở dài]`, `[hắng giọng]`) vào đúng vị trí con trỏ (hoặc cuối văn bản nếu không focus) và cập nhật lại bộ đếm ký tự.
* **Bộ đếm Real-time:** Mỗi khi `Textarea` thay đổi (`onInput`), tính toán ngay:
  * `char_count = text.length`
  * `estimated_tokens = calculateTokens(text, voice_model)`
  * Kiểm tra nếu `estimated_tokens > remaining_daily_quota` hoặc `> total_token_balance`, hiển thị cảnh báo màu đỏ tại bộ đếm và disable nút `Tạo giọng nói`.
* **Xử lý Toán học & Hóa học (Text Normalization Engine):** Trước khi đưa vào model TTS V4, pipeline tiền xử lý văn bản (Text Frontend) tự động nhận diện biểu thức toán học (`ax² + bx + c = 0`, ký hiệu tập hợp `∈ ℝ`, bất đẳng thức `≥`) và phương trình hóa học (`2H2 + O2 → 2H2O`) để chuyển thành âm đọc tiếng Việt tự nhiên (ví dụ: *"a x bình phương cộng b x cộng c bằng không"*, *"hai H hai cộng O hai tạo thành hai H hai O"*).

---

### 3.3. Module 3: Podcast Studio (Hội Thoại Đa Giọng)
* **Tham chiếu hình ảnh:** `image_466b9f.png`
* **Mục đích:** Tạo một tập podcast hoàn chỉnh từ cuộc hội thoại giữa nhiều người (Host, Guest...) với khả năng viết kịch bản bằng AI hoặc nhập từng lượt thoại.

#### 3.3.1. Thành phần giao diện (UI Components)
1. **Header Podcast:**
   * Bên trái: Icon Podcast màu tím + Tiêu đề **PODCAST** + Badge tổng số lượt thoại hiện tại (`2 lượt thoại`).
   * Bên phải: Nút `[⚙️ Cài đặt]` (Cấu hình khoảng nghỉ giữa các lượt thoại, nhạc intro/outro, chuẩn hóa âm lượng) và nút `[?]` (Hướng dẫn).
2. **Thanh công cụ Khởi tạo Kịch bản (Script Toolbar):**
   * Nút `[📋 Dán kịch bản]`: Mở modal cho phép dán toàn bộ kịch bản dạng văn bản thô để hệ thống tự động tách thành các lượt thoại theo tên nhân vật.
   * Nút `[✨ Viết kịch bản bằng AI]`: Mở modal nhập chủ đề/ý tưởng/URL bài viết để AI tự động sinh kịch bản hội thoại phân vai Host & Guest.
   * Text hướng dẫn phụ: *"hoặc thêm từng lượt bên dưới"*.
3. **Thanh Thông tin giới hạn & Thêm lượt:**
   * Bên trái: `2 LƯỢT THOẠI · tối đa 200 lượt mỗi podcast · gói trả phí: 1000 lượt` (Hiển thị rõ giới hạn theo gói cước: Free/Trial tối đa 200 lượt, Paid/Pro tối đa 1.000 lượt).
   * Bên phải: Nút viền tím `[+ Thêm lượt]` để thêm một khối lượt thoại mới vào cuối danh sách.
4. **Danh sách Khối Lượt Thoại (Dialogue Turn Cards):**
   Mỗi lượt thoại là một Card độc lập gồm:
   * **Header của Lượt thoại:**
     * Badge số thứ tự tròn màu tím: `1`, `2`, ...
     * Ô input Tên vai/Nhân vật: Mặc định lượt 1 là `Host`, lượt 2 là `Guest` (người dùng có thể sửa tên).
     * Dropdown Chọn giọng nói: VD Lượt 1 chọn `Ngọc Lan v`, Lượt 2 chọn `Minh Quân v`.
     * Dropdown Chọn phong cách/ngữ điệu (Style): `Tự nhiên v`.
     * Nút Xóa lượt thoại `[🗑️]` ở góc phải của card.
   * **Body của Lượt thoại:**
     * Textarea nhập lời thoại, placeholder: *"Nội dung lượt thoại..."* (hỗ trợ kéo giãn chiều cao).
   * **Footer của Lượt thoại:**
     * Các nút chèn nhanh cảm xúc vào lượt thoại đó: `[Cười]`, `[Thở dài]`, `[Hắng giọng]`.
5. **Thanh Hành Động Dưới Cùng (Bottom Bar):**
   * Bên trái: Hiển thị hạn mức `Còn 50,000 ký tự hôm nay` (font monospace).
   * Bên phải: Nút chính `[🎙️ Tạo podcast]` (Nền tím, chỉ active khi có ít nhất 1 lượt thoại có nội dung).
6. **Khu vực "PODCAST ĐÃ TẠO" (Created Podcasts History):**
   * Header: Icon History + `PODCAST ĐÃ TẠO` + Nút Refresh `↻`.
   * **Empty State (Khi chưa có dữ liệu):**
     * Icon hội thoại mờ ở giữa.
     * Dòng chính: **Chưa có podcast nào**
     * Dòng phụ: *Ghép nhiều giọng thành một tập podcast ở trên*

#### 3.3.2. Logic nghiệp vụ & Xử lý (Business Rules)
* **Giới hạn lượt thoại (Turn Limits):**
  * Kiểm tra gói tài khoản: Nếu gói thường/dùng thử (`max_turns = 200`), gói trả phí (`max_turns = 1000`). Khi chạm ngưỡng, disable nút `+ Thêm lượt` và thông báo nâng cấp gói.
* **Luồng tổng hợp Podcast (Podcast Synthesis Pipeline):**
  * Khi bấm `Tạo podcast`, hệ thống duyệt tuần tự qua mảng `turns[]`, gọi TTS Engine tổng hợp từng đoạn audio theo `voice_id` và `style` tương ứng, sau đó ghép nối (concatenate) các đoạn audio với khoảng nghỉ tự nhiên (crossfade / silence padding cấu hình trong `Cài đặt`) thành 1 file âm thanh duy nhất và lưu vào mục `PODCAST ĐÃ TẠO`.

---

### 3.4. Module 4: Phòng Thu Truyện (Multi-Voice Story Studio)
* **Tham chiếu hình ảnh:** `image_4668b9.png`
* **Mục đích:** Công cụ chuyên biệt theo mô hình Project-based để sản xuất truyện аудио (Audiobook / Truyện nhiều giọng), cho phép quản lý danh sách nhân vật, tạo và sửa từng phân đoạn độc lập mà không cần render lại toàn bộ truyện, kéo-thả đổi thứ tự và xuất ra một file âm thanh liền mạch.

#### 3.4.1. Thành phần giao diện (UI Components)
Màn hình chia làm 2 cột (Master-Detail Layout bên cạnh Sidebar chính):

1. **Cột Quản lý Dự án Truyện (Left Project Panel - `width: ~260px`):**
   * Header: Icon Sách mở màu tím + Tiêu đề **Dự án truyện**.
   * Nút tạo mới (Full-width trong panel, viền/nền tím đậm): `[+ Truyện mới]`.
   * Danh sách các dự án truyện đã tạo:
     * Mỗi item hiển thị: Tiêu đề truyện (VD: **Truyện mới**) và dòng phụ hiển thị phiên bản model + số đoạn hiện có (`V4 · 0 đoạn`).
     * Cho phép chọn dự án để mở vào vùng làm việc bên phải, đổi tên hoặc xóa dự án.

2. **Vùng Làm Việc Chính / Màn hình Onboarding Phòng Thu Truyện (Main Workspace):**
   Khi dự án mới chưa có phân đoạn hoặc mới truy cập, hiển thị màn hình hướng dẫn trực quan:
   * **Hero Header:**
     * Icon Quyển sách lớn kèm badge `[✨ MỚI]` màu tím.
     * Tiêu đề lớn: **Phòng thu Truyện**
     * Mô tả: *"Tạo một câu chuyện nhiều giọng: mỗi nhân vật một giọng riêng, viết từng lời thoại, tạo và chỉnh sửa từng đoạn, rồi xuất ra MỘT file âm thanh liền mạch."*
   * **Card Hướng dẫn "CÁCH TẠO TRUYỆN NHIỀU GIỌNG" (5 bước quy trình chuẩn):**
     * **Bước 1 — `👥 Thêm nhân vật`:** *Mỗi nhân vật (người kể, Phương, Long...) gán một giọng riêng. Có thể gắn màu để dễ phân biệt.*
     * **Bước 2 — `✍️ Viết từng phân đoạn`:** *Chọn nhân vật rồi nhập lời thoại cho từng đoạn. Giọng "tự nhiên" có thể chèn cảm xúc như [cười].*
     * **Bước 3 — `🔊 Tạo giọng từng đoạn`:** *Bấm "Tạo giọng" cho mỗi đoạn. Sửa đoạn nào chỉ cần tạo lại đoạn đó, không ảnh hưởng đoạn khác.*
     * **Bước 4 — `⠿ Sắp xếp thứ tự`:** *Kéo-thả các đoạn bằng biểu tượng `⠿` để đổi thứ tự kể chuyện.*
     * **Bước 5 — `🎬 Xuất truyện`:** *Ghép tất cả thành MỘT file liền mạch. Bấm play ở danh sách để nghe lại bất cứ lúc nào.*
   * **CTA Button dưới đáy:** Nút lớn nền tím `[+ Truyện mới]`.

#### 3.4.2. Đặc tả Chức năng Chi tiết cho Workspace Dự Án Truyện (Dựa trên 5 bước nghiệp vụ)
Để đội ngũ lập trình triển khai đầy đủ bên trong một Dự án truyện (khi người dùng bấm `+ Truyện mới` hoặc mở dự án):
1. **Quản lý Nhân vật (Character Roster):**
   * Cho phép thêm/sửa/xóa nhân vật trong dự án (`character_id`, `name`, `voice_id`, `color_hex`, `default_style`). Mặc định khởi tạo sẵn nhân vật `Người kể chuyện (Narrator)`.
2. **Danh sách Phân đoạn (Segment Editor List):**
   * Mỗi phân đoạn (`StorySegment`) gồm:
     * Handle kéo-thả (`⠿` - Drag handle sử dụng thư viện như `@dnd-kit` hoặc `react-beautiful-dnd`).
     * Dropdown chọn Nhân vật (hiển thị kèm chấm màu `color_hex` và tên giọng đã gán).
     * Ô nhập lời thoại (hỗ trợ chèn tag cảm xúc `[cười]`, `[thở dài]`, `[hắng giọng]`).
     * Nút `[Tạo giọng]` riêng cho từng đoạn + Trình phát mini `[▶]` để nghe thử ngay đoạn đó sau khi tạo.
     * Trạng thái đoạn (`status`: `DRAFT`, `GENERATING`, `READY`, `MODIFIED_NEEDS_REGEN` - nếu người dùng sửa chữ sau khi đã tạo audio, đánh dấu cần tạo lại đoạn đó).
3. **Xuất truyện (Export / Merge Audio):**
   * Nút `[🎬 Xuất truyện]` chỉ ghép các file audio của từng phân đoạn đã tạo (`READY`) theo đúng thứ tự kéo-thả hiện tại (`sort_order`) thành 1 file `.mp3`/`.wav` hoàn chỉnh thông qua `ffmpeg` ở Backend mà không tốn thêm token tổng hợp lại các đoạn chưa sửa.

---

### 3.5. Module 5: Thư Viện — Giọng Nói Của Tôi (My Generated Audio Library)
* **Tham chiếu hình ảnh:** `image_466879.png`
* **Mục đích:** Lưu trữ, tra cứu, nghe lại, tải về và quản lý toàn bộ các bản ghi âm thanh mà người dùng đã tạo.

#### 3.5.1. Thành phần giao diện (UI Components)
1. **Header:**
   * Tiêu đề: **Giọng nói của tôi**
   * Phụ đề: *Xem và quản lý giọng nói đã tạo*
2. **Thanh Tìm kiếm, Bộ lọc & Hành động (Filter & Action Bar):**
   * **Ô tìm kiếm (Search Input):** Có viền tím khi focus, icon kính lúp `🔍`, placeholder: *"Tìm kiếm theo văn bản hoặc giọng..."* (`width: ~420px`).
   * **Dropdown Lọc theo giọng:** Mặc định `Tất cả giọng v` (Liệt kê danh sách các giọng đọc mà người dùng đã từng sử dụng để lọc nhanh).
   * **Nút hành động bên phải:** Nút nền tím `[+ Tạo mới]` (Click sẽ điều hướng người dùng về trang `Phòng thu`).
3. **Danh sách Bản ghi âm thanh (Audio List Items):**
   Mỗi bản ghi hiển thị trên một Card ngang:
   * **Nút Play/Pause tròn `[▶]`** bên trái (kích thước lớn `40x40px`, nền xám tối).
   * **Nội dung chính:**
     * **Dòng 1:** Nội dung văn bản gốc của bản ghi (1 dòng, cắt `...` nếu dài).
     * **Dòng 2 (Metadata kèm icon):**
       * `👤 Minh Quân` (Tên giọng đọc)
       * `🌐 Tiếng Việt (VN)` (Ngôn ngữ/Quốc gia)
       * `🕒 146.0s` (Thời lượng bản ghi tính bằng giây)
       * `📅 16:23 30/10/2026` (Giờ và ngày tạo `HH:mm DD/MM/YYYY`)
   * **Hành động bên phải:**
     * Nút `[⬇️]` (Download file âm thanh `.mp3`/`.wav` về máy).
     * Nút `[🗑️]` (Xóa bản ghi — hiển thị confirm dialog trước khi xóa vĩnh viễn).
4. **Thanh Trạng thái Footer (Bottom Summary Bar):**
   * Cố định ở đáy màn hình:
   * Bên trái: `2 trong số 2 giọng nói` (Số lượng đang hiển thị sau khi lọc / Tổng số bản ghi).
   * Bên phải: `Tổng thời lượng: 293.3s` (Tổng cộng thời lượng của các bản ghi).

---

### 3.6. Module 6: Thư Viện — Bảng Xếp Hạng Giọng (Voice Leaderboard)
* **Tham chiếu hình ảnh:** `image_466839.png`
* **Mục đích:** Giúp người dùng khám phá các giọng đọc được yêu thích nhất trên hệ thống, nghe thử mẫu giọng và chọn sử dụng ngay.

#### 3.6.1. Thành phần giao diện (UI Components)
1. **Header & Quy tắc xếp hạng:**
   * Icon Cúp vàng `🏆` trong ô vuông bo góc + Tiêu đề: **Bảng xếp hạng giọng**
   * Phụ đề giải thích thuật toán: *"Xếp theo số người dùng mỗi giọng trong kỳ, không theo số lần tạo — một người tạo nhiều cũng chỉ tính một."*
2. **Thanh Bộ lọc Đa chiều (Multi-Filter Bar):**
   * **Bộ lọc Thời gian (Segmented Toggle):** `[7 ngày qua]` (Active) | `[Mọi lúc]`
   * **Bộ lọc Giới tính (Pills):** `[Giới tính: Tất cả]` (Active - viền tím) | `[Nữ]` | `[Nam]`
   * **Bộ lọc Vùng miền (Pills):** `[Miền: Tất cả]` (Active - viền tím) | `[Miền Bắc]` | `[Miền Trung]` | `[Miền Nam]`
   * **Dòng trạng thái dữ liệu:** `50 giọng · cập nhật 06:20 01-11` (Hiển thị tổng số giọng trong bảng xếp hạng và thời điểm cronjob cập nhật gần nhất).
3. **Khu vực Top 3 Podium Cards (3 Giọng Dẫn Đầu):**
   Hiển thị 3 Card lớn bố cục Podium: **Hạng 2 (Trái) — Hạng 1 (Giữa, nhô cao hơn) — Hạng 3 (Phải)**:
   * **Hạng 1 (Giữa - Viền vàng `#F59E0B`, Badge `🏆 1` nền vàng):**
     * Avatar minh họa nhân vật lớn (viền xanh/vàng).
     * Tên giọng: **Minh Quân**
     * Thuộc tính: `Nam · Miền Bắc`
     * Tags mô tả chất giọng: `Giọng nam trầm ấm`
     * Thanh độ phổ biến (Popularity Progress Bar): Thanh màu tím đầy `100%` (làm chuẩn so sánh cho các hạng dưới).
     * Hành động: Nút `[▶]` (Nghe thử audio sample của giọng) + Nút lớn nền tím `[Dùng giọng này]`.
   * **Hạng 2 (Trái - Viền xám bạc, Badge `🏆 2` nền bạc):**
     * Avatar minh họa + Tên: **Adam Tốp Tốp**
     * Thuộc tính: `Nam · Miền Nam`
     * Tags: `Cảm xúc · Không nghiêm túc · Tốp Tốp · Tấu hài`
     * Thanh độ phổ biến (tỷ lệ so với Hạng 1) + Nút `[▶]` + `[Dùng giọng này]`.
   * **Hạng 3 (Phải - Viền đồng, Badge `🏆 3` nền cam đồng):**
     * Avatar minh họa + Tên: **Hải Đăng**
     * Thuộc tính: `Nam · Miền Bắc`
     * Tags: `Bắc · Code · IT · Chuyên nghiệp`
     * Thanh độ phổ biến + Nút `[▶]` + `[Dùng giọng này]`.
4. **Danh sách Hạng 4 trở đi (Ranked Table List - Hạng 4 đến 50):**
   Mỗi dòng gồm:
   * **Cột Thứ hạng:** Số thứ tự `4`, `5`, `6`, `7`, `8`, `9`, `10`...
   * **Cột Thông tin giọng:** Avatar tròn minh họa + Tên giọng (**Duyên Hà My**, **Nhật Phong**, **Đăng Quân**, **Mai Bé Phương**, **Tường Vy**, **Thiện Minh**, **Nhỏ Ngọt Ngào**...) + Dòng phụ `Giới tính · Vùng miền` (VD: `Nữ · Miền Nam`, `Nam · Miền Bắc`).
   * **Cột Thanh tỷ lệ phổ biến (Popularity Bar):** Thanh ngang màu tím thể hiện độ phổ biến tương đối so với Top 1 (ẩn số tuyệt đối để bảo mật số liệu kinh doanh, chỉ hiển thị thanh trực quan).
   * **Cột Hành động:** Nút `[▶]` (Nghe mẫu) + Nút `[Dùng]`.

#### 3.6.2. Logic nghiệp vụ & Xử lý (Business Rules)
* **Thuật toán xếp hạng (`COUNT(DISTINCT user_id)`):**
  * Điểm xếp hạng của một giọng $V$ trong kỳ $T$ (`7d` hoặc `all_time`) được tính bằng:
    $$\text{Score}(V, T) = \text{COUNT}(\text{DISTINCT } \text{user\_id} \text{ có tạo thành công ít nhất 1 audio bằng giọng } V \text{ trong kỳ } T)$$
  * Chiều dài thanh tiến trình của hạng thứ $i$: $\text{Width}_i = \left(\frac{\text{Score}_i}{\text{Score}_1}\right) \times 100\%$.
* **Hành động "Dùng giọng này" / "Dùng":** Khi click, lưu `selected_voice_id` vào state/URL query (`/studio?voice=minh-quan`) và chuyển hướng sang màn hình **Phòng thu** với giọng đó đã được chọn sẵn.

---

### 3.7. Module 7: Tài Khoản — Bảng Điều Khiển (User Dashboard)
* **Tham chiếu hình ảnh:** `image_4667f6.png`
* **Mục đích:** Cung cấp cái nhìn tổng quan toàn diện về số dư token, hạn mức ngày, thống kê tần suất sử dụng, tỷ lệ thành công và lối tắt tới các tính năng chính.

#### 3.7.1. Thành phần giao diện (UI Components)
1. **Header Chào mừng:**
   * Bên trái: **Xin chào, `<username>`** (VD: `Xin chào, sondn2010f`) + Dòng ngày tháng hiện tại bên dưới: `Chủ Nhật, 1 tháng 11`.
   * Bên phải: Nút Refresh dữ liệu `↻`.
2. **Hero Card — Quản lý Token (Token Balance Overview Card):**
   * Nhãn trên: `Token còn lại` + Badge gói hiện tại `[GÓI DÙNG THỬ]` (nền tím nhạt, chữ tím).
   * Con số chính (Font lớn `36px-42px` đậm): **140.574** accompanied by `/ 150.000 token`.
   * Thanh Progress Bar màu tím thể hiện tỷ lệ token còn lại trên tổng token của gói.
   * Dòng thông tin phụ bên dưới thanh:
     * `Còn hôm nay: 50.000` (Hạn mức sử dụng trong ngày còn lại).
     * `Hết hạn: 6/11/2026` (Ngày hết hạn của gói token hiện tại).
   * Bên phải Card: Nút nền tím `[💳 Quản lý gói]` (Điều hướng sang trang `Thanh toán`).
3. **Hàng 4 Thẻ Chỉ Số Thống Kê (4 KPI Metric Cards):**
   * **Card 1 — `Lần tạo hôm nay`:**
     * Giá trị lớn: `0`
     * Phụ đề: `1 lần trong 7 ngày`
     * Kèm biểu đồ mini (Sparkline bar chart 7 cột) ở góc phải của card.
   * **Card 2 — `Lần tạo tháng này`:**
     * Giá trị lớn: `0`
     * Phụ đề: `tháng 11 năm 2026`
   * **Card 3 — `Tổng audio đã tạo`:**
     * Giá trị lớn: `2m 27s` (Tổng thời lượng âm thanh đã tạo thành công).
     * Phụ đề: `1 bản ghi thành công`
   * **Card 4 — `Tỷ lệ thành công`:**
     * Giá trị lớn: `100%`
     * Phụ đề: `Chưa lần nào thất bại`
4. **Hàng Giữa (Biểu đồ Hoạt động & Bản ghi gần đây - Tỷ lệ cột 65% : 35%):**
   * **Bên trái — Card `Hoạt động hằng ngày (7 ngày qua)`:**
     * Phụ đề: `1 lần tạo trong 7 ngày qua`.
     * Chú giải (Legend) góc phải trên: `🟪 Thành công` | `🟥 Thất bại`.
     * Biểu đồ cột (Bar Chart) với trục hoành là 7 ngày gần nhất (`Thứ 2`, `Thứ 3`, `Thứ 4`, `Thứ 5`, `Thứ 6`, `Thứ 7`, `Hôm nay`).
   * **Bên phải — Card `Bản ghi gần đây`:**
     * Header: **Bản ghi gần đây** (*Nghe lại thứ bạn vừa tạo*) + Link `Xem tất cả` màu tím (trỏ tới trang `Giọng nói`).
     * Danh sách rút gọn các bản ghi mới nhất: Nút `[▶]` + Trích đoạn văn bản + Metadata `Minh Quân · 2m 26s · 30–10`.
5. **Hàng Dưới Cùng (Phân bổ giọng & Thao tác nhanh - Tỷ lệ cột 55% : 45%):**
   * **Bên trái — Card `Sử dụng theo giọng`:**
     * Phụ đề: *Phân bổ theo giọng*
     * Danh sách các giọng đã dùng kèm số lần tạo và thanh ngang tỷ lệ: VD `Minh Quân` — `1` (thanh tím 100%).
   * **Bên phải — Card `Thao tác nhanh`:**
     * Phụ đề: *Đi tới tính năng*
     * Grid 2x2 các thẻ điều hướng nhanh:
       1. **Phòng thu** (*Văn bản thành giọng nói*) - Viền tím nổi bật.
       2. **Podcast** (*Nhiều giọng, một tập*).
       3. **Truyện** / **Lồng tiếng** (các card phía dưới).

---

### 3.8. Module 8: Tài Khoản — Thanh Toán & Đăng Ký (Billing & Subscriptions)
* **Tham chiếu hình ảnh:** `image_466512.png`
* **Mục đích:** Quản lý số dư token, mua hoặc nâng cấp các gói token API, áp dụng mã khuyến mãi và mua bản quyền ứng dụng máy tính (Desktop App).

#### 3.8.1. Thành phần giao diện (UI Components)
1. **Header:**
   * Tiêu đề: **Thanh toán & Đăng ký**
   * Phụ đề: *Quản lý gói dịch vụ, theo dõi mức sử dụng và cập nhật phương thức thanh toán.*
2. **Banner Khuyến Mãi (Promo Banner):**
   * Khung viền tím nhạt, icon Tag giảm giá `🏷️` màu tím:
   * Dòng 1: **Ưu đãi Thịnh Vượng — Nhập mã `THINHVUONG` giảm ngay 15%**
   * Dòng 2: *Áp dụng cho gói CREATOR, PRO, STUDIO · mỗi tài khoản 1 lần · HSD đến hết 31/12 · số lượng có hạn*
3. **Khu vực Trạng thái Hiện tại (2 Cột ngang bằng nhau):**
   * **Cột trái — Card `📦 Số dư token API`:**
     * Dòng trạng thái chính: `Còn lại` — **140.574 / 150.000** (font monospace).
     * Thanh tiến trình màu tím + Dòng dưới: `6% đã dùng` (bên trái) và Badge `Dùng thử` màu xanh lá (bên phải).
     * Thanh tiến trình phụ cho hạn mức ngày: `Hằng ngày` — `50.000 còn lại`.
     * Ngày hết hạn: `Hết hạn: 6/11/2026`.
     * Nút CTA full-width nền tím: `[↑ Nâng cấp gói token]` (Cuộn xuống phần bảng giá hoặc mở modal chọn gói).
   * **Cột phải — Card `💻 Bản quyền app máy tính`:**
     * Trạng thái khi chưa mua: Icon Laptop mờ ở giữa + Tiêu đề **Chưa có bản quyền app máy tính** + Mô tả *"Mua bản quyền để dùng ứng dụng VieNeu trên máy tính."*
     * Nút CTA nền tím: `[🛒 Xem gói bản quyền]`.
4. **Khu vực Bảng Giá "📦 Gói token API" (Token Pricing Tiers):**
   * Mô tả: *"Mua hoặc nâng cấp số dư token để truy cập API TTS. Bạn có thể nâng cấp bất cứ lúc nào — token chưa dùng sẽ được hoàn theo tỉ lệ."*
   * **Grid các Gói cước (Pricing Cards):**

| Thuộc tính | Gói **Starter** | Gói **Creator** | Gói **Pro** | Gói **Studio** *(Mở rộng)* |
| :--- | :--- | :--- | :--- | :--- |
| **Mô tả ngắn** | Gói khởi đầu — hạn dùng 6 tháng | Cho nhà sáng tạo nội dung | Phổ biến nhất — đơn giá tốt | Dành cho doanh nghiệp / studio |
| **Giá bán** | **99.000 ₫** | **299.000 ₫** | **799.000 ₫** | Theo cấu hình hệ thống |
| **Số lượng Token** | `400.000 token` | `1.500.000 token` | `5.000.000 token` | Theo cấu hình hệ thống |
| **Quy đổi thời lượng** | `≈ 2 giờ âm thanh · đã tính theo đơn giá V4` | `≈ 7.5 giờ âm thanh · đã tính theo đơn giá V4` | `≈ 25 giờ âm thanh · đã tính theo đơn giá V4` | Tính theo công thức chuẩn V4 |
| **Thời hạn** | Hiệu lực 6 tháng | Hiệu lực 6 tháng | Hiệu lực 6 tháng | Hiệu lực 6 tháng |
| **Ô Mã giảm giá** | Input `Mã giảm giá` + Nút `[Áp dụng]` | Input `Mã giảm giá` + Nút `[Áp dụng]` | Input `Mã giảm giá` + Nút `[Áp dụng]` | Input `Mã giảm giá` + Nút `[Áp dụng]` |
| **Hành động** | Nút Mua / Nâng cấp ngay bên dưới | Nút Mua / Nâng cấp ngay bên dưới | Nút Mua / Nâng cấp ngay bên dưới | Nút Mua / Nâng cấp ngay bên dưới |

#### 3.8.2. Logic nghiệp vụ & Xử lý (Business Rules)
* **Quy đổi Token sang Thời lượng âm thanh (Model V4):**
  * Từ số liệu trên UI:
    * $400.000 \text{ token} \approx 2 \text{ giờ} \Rightarrow 200.000 \text{ token} / 1 \text{ giờ âm thanh}$ (tương đương $\approx 55,5 \text{ token / giây âm thanh}$).
    * $1.500.000 \text{ token} \approx 7,5 \text{ giờ}$.
    * $5.000.000 \text{ token} \approx 25 \text{ giờ}$.
* **Chính sách nâng cấp hoàn trả theo tỷ lệ (Pro-rata Upgrade):**
  * *"Bạn có thể nâng cấp bất cứ lúc nào — token chưa dùng sẽ được hoàn theo tỉ lệ."* Khi người dùng nâng cấp gói, cộng dồn hoặc khấu trừ giá trị của phần token chưa sử dụng từ gói hiện tại vào giao dịch nâng cấp.
* **Áp dụng Mã giảm giá (Voucher Validation):**
  * Mỗi Card gói cước có ô nhập `Mã giảm giá` và nút `Áp dụng` riêng.
  * Khi nhập mã (VD: `THINHVUONG`), kiểm tra:
    1. Gói áp dụng có nằm trong danh sách hợp lệ không (`CREATOR`, `PRO`, `STUDIO` — nếu nhập ở gói `Starter` thì báo lỗi *"Mã này chỉ áp dụng cho gói Creator, Pro, Studio"*).
    2. Tài khoản đã từng dùng mã này chưa (`max_uses_per_user = 1`).
    3. Thời hạn (`<= 31/12`) và tổng lượt dùng toàn hệ thống còn hiệu lực không.
    4. Nếu hợp lệ, gạch ngang giá gốc và hiển thị giá sau giảm 15% ngay trên Card đó.

---

### 3.9. Module 9: Tài Khoản — API Nhà Phát Triển (Developer Portal & MCP)
* **Tham chiếu hình ảnh:** `image_4664f4.png`
* **Mục đích:** Cung cấp API Keys để lập trình viên tích hợp VieNeu TTS vào ứng dụng bên thứ ba, đồng thời hỗ trợ chuẩn giao thức **MCP (Model Context Protocol)** để kết nối trực tiếp vào Claude, ChatGPT, Cursor, Claude Code.

#### 3.9.1. Thành phần giao diện (UI Components)
1. **Header:**
   * Bên trái: Tiêu đề **API Nhà phát triển** + Phụ đề *Tích hợp VieNeu vào ứng dụng của bạn*.
   * Bên phải: Pill hiển thị số dư token hiện tại: `🪙 Còn lại: 140.574 / 150.000`.
2. **Thanh Điều Hướng Tab (Sub-navigation Tabs):**
   * `[🔑 API Keys]` (Active - gạch chân tím)
   * `[📊 Sử dụng]` (Thống kê request log, lượng token tiêu thụ qua API)
   * `[📄 Tài liệu]` (Tài liệu hướng dẫn REST API endpoints `/v1/...`, SDK, Webhooks)
3. **Khối "Tạo khóa mới" (Create API Key Card):**
   * Bộ chọn Môi trường (Environment Segmented Buttons):
     * `[⚡ Live]` (Active - nền tím: Dùng cho môi trường Production, trừ token thật).
     * `[🧪 Test]` (Dùng cho môi trường Sandbox/Development, giới hạn tốc độ hoặc trả về audio test).
   * Ô nhập Tên khóa (Key Name Input): Placeholder *"Ví dụ: Khóa ứng dụng của tôi"*.
   * Nút `[+ Tạo khóa]` (Nền tím, chỉ active khi ô tên khóa không rỗng).
4. **Danh sách Khóa API đã tạo (API Keys List):**
   * Bộ lọc Tab con: `[⚡ Live]` | `[🧪 Test]`.
   * **Empty State (Khi chưa có khóa):**
     * Icon chìa khóa gạch chéo `🗝️` ở giữa + Text: *"Chưa có khóa API. Tạo một khóa ở trên để bắt đầu."*
   * **Khi có khóa API:** Hiển thị bảng gồm Tên khóa, Prefix khóa (`vn_live_xxxx...` hoặc `vn_test_xxxx...`), Ngày tạo, Lần dùng cuối, và nút Thu hồi/Xóa khóa (`Revoke`). Lưu ý: Secret Key đầy đủ chỉ hiển thị duy nhất 1 lần ngay sau khi bấm `+ Tạo khóa` kèm nút Sao chép.
5. **Khối Tích hợp MCP — "Dùng VieNeu trong Claude, ChatGPT" (MCP Connector Card):**
   * Tiêu đề: **Dùng VieNeu trong Claude, ChatGPT**
   * Mô tả: *"Thêm địa chỉ này làm connector, đăng nhập VieNeu, rồi nhờ trợ lý đọc văn bản bằng giọng bạn chọn."*
   * **Hộp URL MCP Endpoint:**
     * Hiển thị URL cố định dạng read-only monospace: `https://api.vieneu.io/mcp`
     * Nút `[📋 Sao chép]` bên phải (Click để copy URL vào clipboard và hiện toast *"Đã sao chép địa chỉ MCP"*).
   * **Hướng dẫn nhanh bên dưới:**
     * *"Trong Claude: Customize → Connectors → "Add custom connector". ChatGPT, Cursor, Claude Code: [xem hướng dẫn](#)"* (Link mở modal/trang hướng dẫn cấu hình chi tiết từng client).
   * **Danh sách `ỨNG DỤNG ĐÃ KẾT NỐI` (Connected OAuth/MCP Clients):**
     * Hiển thị các ứng dụng AI đã xác thực OAuth qua MCP (hoặc text *"Chưa có ứng dụng nào."* nếu chưa kết nối), cho phép người dùng ngắt kết nối (Revoke access) khi cần.

---

### 3.10. Module 10: Tài Khoản — Từ Điển Phát Âm (Pronunciation Dictionary)
* **Tham chiếu hình ảnh:** `image_4664d0.png`
* **Mục đích:** Cho phép người dùng dạy AI Engine cách đọc chính xác các tên riêng, thuật ngữ chuyên ngành, từ nước ngoài hoặc chữ viết tắt theo từng tài khoản.

#### 3.10.1. Thành phần giao diện (UI Components)
1. **Header:**
   * Tiêu đề: **Từ điển phát âm** + Badge `[Theo tài khoản]` (nền tím nhạt).
   * Mô tả: *"Dạy engine cách đọc tên riêng, thuật ngữ, chữ viết tắt. Áp dụng tự động cho mọi lượt tạo trên web: Phòng thu, Truyện, Lồng tiếng và Phát ngay."*
2. **Bố cục 2 Cột (Cột trái 65%: Bảng quản lý luật — Cột phải 35%: Công cụ test & Giải thích):**

   * **Cột Trái — Bảng Quản Lý Luật Phát Âm (Dictionary Rules Table Card):**
     * **Thanh công cụ trên cùng (Toolbar):**
       * Bên trái:
         * `[+ Thêm luật]`: Thêm một dòng quy tắc mới vào đầu bảng.
         * `[📄 Nhập từ tệp]`: Upload file `.txt` hoặc `.csv` chứa danh sách từ điển.
         * `[⬇️ Xuất ra tệp]`: Tải toàn bộ từ điển hiện tại về máy dưới dạng file `.txt`/`.csv`.
       * Bên phải:
         * Bộ đếm giới hạn: `1 luật · tối đa 2000`
         * Nút `[💾 Lưu từ điển]` (Nền tím — Lưu các thay đổi lên server).
     * **Cấu trúc Bảng Luật (Columns):**
       1. `TỪ NHƯ ĐANG VIẾT` (Source Word/Phrase): Ô input nhập từ gốc (VD: `VieNeu`).
       2. `ENGINE ĐỌC LÀ` (Phonetic/Replacement Text): Ô input nhập phiên âm tiếng Việt (VD: `Vi Nơi`).
       3. `CẢ TỪ` (Whole Word Match): Checkbox (`[v]`). Nếu bật, chỉ khớp khi từ đó đứng độc lập (có ranh giới từ word boundary), không thay thế nếu nó nằm bên trong một từ dài hơn.
       4. `PHÂN BIỆT HOA/THƯỜNG` (Case Sensitive): Checkbox (`[ ]`). Nếu bật, chỉ khớp đúng chữ hoa/thường như đã nhập.
       5. **Cột Hành động:**
          * Toggle Switch Bật/Tắt luật (`[●]`) — cho phép tạm ngưng một luật mà không cần xóa.
          * Nút Xóa luật (`[🗑️]`).

   * **Cột Phải (Trên) — Card "Nghe thử cách đọc" (Live Sandbox Preview):**
     * Tiêu đề: **Nghe thử cách đọc**
     * Mô tả: *"Gõ một câu có chứa từ trong từ điển. Kết quả bên dưới là văn bản engine sẽ nhận (đang tính theo bảng hiện tại, kể cả chưa lưu)."*
     * **Ô Input Câu thử nghiệm:**
       * VD: `Bản VieNeu 2.0 chạy trên GPU, nhanh hơn 5 km/h.`
     * **Khối Kết quả `Engine đọc:` (Viền tím, nền tím đen):**
       * Hiển thị real-time kết quả sau khi chạy bộ thay thế từ điển:
       * VD: `Bản Vi Nơi 2.0 chạy trên GPU, nhanh hơn 5 km/h.` (Từ `VieNeu` đã được biến đổi thành `Vi Nơi` ngay lập tức trên client mà chưa cần bấm Lưu).

   * **Cột Phải (Dưới) — Card "Cách hoạt động" (Technical Specification Box):**
     Hiển thị rõ ràng quy tắc thuật toán xử lý từ điển (đây cũng chính là yêu cầu kỹ thuật bắt buộc cho đội ngũ lập trình):
     * **Quy tắc 1 (Longest Match First):** *"Từ dài hơn được ưu tiên: có cả 'km' và 'km/h' thì '5 km/h' đọc theo luật 'km/h'."*
     * **Quy tắc 2 (Single-Pass / Non-Recursive):** *"Kết quả không bị quét lại, nên luật không bao giờ tự lặp hay gọi luật khác."*
     * **Quy tắc 3 (Pipeline Order & Original Text Preservation):** *"Áp dụng sau bước AI chỉnh văn bản và trước khi gửi engine. Văn bản gốc trong thư viện vẫn giữ nguyên như bạn gõ."*
     * **Quy tắc 4 (Scope Limitation):** *"Chưa áp dụng cho API nhà phát triển (/v1) và ứng dụng máy tính — app có từ điển riêng trên máy."*
     * **Quy tắc 5 (Import Format & Conflict Resolution):** *"Tệp .txt hoặc .csv, mỗi dòng 'từ = cách đọc' (cũng nhận '→', tab hoặc dấu phẩy). Dòng bắt đầu bằng # bị bỏ qua. Luật nhập vào được xếp lên đầu nên sẽ đè luật cũ trùng từ."*

#### 3.10.2. Đặc tả Thuật toán Xử lý Từ Điển Phát Âm (Dành cho Dev Frontend & Backend)
Để đảm bảo tính nhất quán tuyệt đối giữa khung **Nghe thử cách đọc** (Frontend) và **Text Preprocessing Pipeline** (Backend):

1. **Giới hạn:** Tối đa `2.000` luật trên mỗi tài khoản (`max_rules = 2000`).
2. **Thuật toán Single-Pass Longest-Match Replacement:**
   * Lọc lấy các luật đang bật (`is_enabled == true`) và có `source_text` khác rỗng.
   * Sắp xếp danh sách luật theo độ dài của `source_text` giảm dần (`length DESC`). Nếu cùng độ dài, ưu tiên luật nằm ở phía trên (luật mới nhập đè luật cũ).
   * Thực hiện quét văn bản **một lần duy nhất (Single-pass tokenization/regex)**:
     * Với mỗi luật:
       * Nếu `whole_word = true`: Kiểm tra ranh giới từ (Unicode word boundary `(?<![\p{L}\p{N}_])` và `(?![\p{L}\p{N}_])`, lưu ý xử lý đúng ký tự tiếng Việt có dấu và ký hiệu đặc biệt như `km/h`).
       * Nếu `case_sensitive = false`: So khớp không phân biệt hoa thường (`i` flag).
     * Khi một đoạn văn bản đã khớp với một luật và được thay thế bằng `target_text`, đánh dấu token đó là **đã xử lý** để các luật tiếp theo không bao giờ quét lại vào phần `target_text` vừa sinh ra (tránh vòng lặp vô hạn như `A -> AB` hoặc luật chồng chéo).
3. **Trình phân tích tệp Nhập (File Import Parser `.txt` / `.csv`):**
   * Đọc từng dòng (`\r?\n`), `trim()` khoảng trắng 2 đầu.
   * Bỏ qua dòng rỗng hoặc dòng bắt đầu bằng ký tự `#` (comment).
   * Tách cặp `(source, target)` theo thứ tự dấu phân cách ưu tiên: `=`, `→`, `\t` (Tab), hoặc `,` (Dấu phẩy).
   * Chèn các luật hợp lệ mới lên **đầu danh sách**; nếu trùng `source` (xét theo `case_sensitive`), ghi đè (override) hoặc loại bỏ luật cũ bên dưới.

---

## 4. Thiết Kế Cơ Sở Dữ Liệu Đề Xuất (Database Schema Specification)

Dưới đây là cấu trúc các bảng dữ liệu cốt lõi (PostgreSQL) phục vụ toàn bộ các màn hình trên:

```sql
-- 1. Bảng Người dùng & Quỹ Token (Users & Token Quotas)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    plan_tier VARCHAR(32) NOT NULL DEFAULT 'TRIAL', -- 'TRIAL', 'STARTER', 'CREATOR', 'PRO', 'STUDIO'
    token_balance BIGINT NOT NULL DEFAULT 150000,
    token_quota_total BIGINT NOT NULL DEFAULT 150000,
    daily_char_limit INT NOT NULL DEFAULT 50000,
    daily_char_remaining INT NOT NULL DEFAULT 50000,
    plan_expires_at TIMESTAMPTZ,
    has_desktop_license BOOLEAN NOT NULL DEFAULT FALSE,
    has_accepted_tts_terms BOOLEAN NOT NULL DEFAULT FALSE,
    terms_accepted_at TIMESTAMPTZ,
    ui_theme VARCHAR(16) DEFAULT 'dark',
    ui_language VARCHAR(8) DEFAULT 'vi',
    onboarding_step_completed INT DEFAULT 0,
    onboarding_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng Danh mục Giọng đọc Hệ thống (System & Cloned Voices)
CREATE TABLE voices (
    id VARCHAR(64) PRIMARY KEY, -- VD: 'minh-quan', 'ngoc-lan', 'adam-top-top'
    name VARCHAR(120) NOT NULL,
    avatar_url TEXT,
    initials VARCHAR(4),
    gender VARCHAR(16) NOT NULL, -- 'NAM', 'NU'
    region VARCHAR(32) NOT NULL, -- 'MIEN_BAC', 'MIEN_TRUNG', 'MIEN_NAM'
    language_code VARCHAR(16) NOT NULL DEFAULT 'vi-VN',
    model_version VARCHAR(16) NOT NULL DEFAULT 'V4',
    tags TEXT[], -- VD: ARRAY['Cảm xúc', 'Không nghiêm túc', 'Tốp Tốp', 'Tấu hài']
    sample_audio_url TEXT NOT NULL,
    supported_styles TEXT[] DEFAULT ARRAY['Tự nhiên'],
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bảng Bản ghi Âm thanh Đơn giọng (TTS Audio Recordings - Phòng thu & Thư viện)
CREATE TABLE tts_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voice_id VARCHAR(64) NOT NULL REFERENCES voices(id),
    model_version VARCHAR(16) NOT NULL DEFAULT 'V4',
    original_text TEXT NOT NULL, -- Giữ nguyên văn bản gốc trước khi qua từ điển
    normalized_text TEXT,        -- Văn bản sau khi chuẩn hóa Toán/Hóa & Từ điển
    speed DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    bg_music_id VARCHAR(64),
    char_count INT NOT NULL,
    tokens_used INT NOT NULL,
    duration_seconds DECIMAL(8,1) NOT NULL, -- VD: 146.0, 147.3
    audio_url TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'SUCCESS', -- 'PENDING', 'SUCCESS', 'FAILED'
    failure_reason TEXT,
    source_module VARCHAR(32) NOT NULL DEFAULT 'STUDIO', -- 'STUDIO', 'PODCAST', 'STORY', 'API'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Bảng Dự án Podcast & Lượt thoại (Podcasts & Dialogue Turns)
CREATE TABLE podcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    settings_json JSONB DEFAULT '{}'::jsonb,
    total_turns INT NOT NULL DEFAULT 0,
    total_chars INT NOT NULL DEFAULT 0,
    duration_seconds DECIMAL(8,1),
    merged_audio_url TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'PROCESSING', 'COMPLETED', 'FAILED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE podcast_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    podcast_id UUID NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    turn_order INT NOT NULL,
    speaker_role VARCHAR(100) NOT NULL, -- VD: 'Host', 'Guest'
    voice_id VARCHAR(64) NOT NULL REFERENCES voices(id),
    style VARCHAR(64) NOT NULL DEFAULT 'Tự nhiên',
    content TEXT NOT NULL,
    segment_audio_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Bảng Dự án Truyện, Nhân vật & Phân đoạn (Story Studio)
CREATE TABLE story_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Truyện mới',
    model_version VARCHAR(16) NOT NULL DEFAULT 'V4',
    segment_count INT NOT NULL DEFAULT 0,
    exported_audio_url TEXT,
    exported_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE story_characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES story_projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- VD: 'Người kể', 'Phương', 'Long'
    voice_id VARCHAR(64) NOT NULL REFERENCES voices(id),
    color_hex VARCHAR(16) NOT NULL DEFAULT '#7C5CFC',
    default_style VARCHAR(64) NOT NULL DEFAULT 'Tự nhiên'
);

CREATE TABLE story_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES story_projects(id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES story_characters(id),
    sort_order INT NOT NULL,
    content TEXT NOT NULL,
    audio_url TEXT,
    duration_seconds DECIMAL(8,1),
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'READY', 'STALE'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Bảng Từ điển Phát âm theo Tài khoản (Pronunciation Dictionary)
CREATE TABLE pronunciation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_term VARCHAR(255) NOT NULL, -- 'VieNeu'
    phonetic_replacement VARCHAR(255) NOT NULL, -- 'Vi Nơi'
    match_whole_word BOOLEAN NOT NULL DEFAULT TRUE,
    case_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    priority_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Bảng Khóa API Nhà phát triển (Developer API Keys)
CREATE TABLE developer_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    environment VARCHAR(16) NOT NULL CHECK (environment IN ('LIVE', 'TEST')),
    key_prefix VARCHAR(24) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 5. Danh Sách REST API Endpoints Cốt Lõi (Backend API Contract)

### 5.1. Nhóm API Người Dùng, Điều Khoản & Dashboard
* `GET /api/v1/user/profile`: Lấy thông tin user, số dư token (`140.574 / 150.000`), hạn mức ngày (`50.000`), trạng thái `has_accepted_tts_terms` và tiến độ Onboarding (`Đã xong 2/4`).
* `POST /api/v1/user/terms/accept`: Ghi nhận người dùng đã tích chọn và đồng ý *Điều khoản tạo giọng nói*.
* `GET /api/v1/user/dashboard`: Trả về dữ liệu tổng hợp cho trang **Bảng điều khiển**:
  * Số dư token & hạn dùng.
  * 4 thẻ KPI: `today_count`, `week_sparkline[]`, `month_count`, `total_audio_duration_sec`, `success_rate_percent`.
  * Biểu đồ 7 ngày (`daily_activity`: mảng 7 ngày gồm `success_count`, `failed_count`).
  * Danh sách bản ghi gần đây (`recent_recordings`: top 5).
  * Phân bổ theo giọng (`voice_distribution`: mảng `{ voice_name, count, percentage }`).

### 5.2. Nhóm API Phòng Thu (TTS Studio) & Thư Viện Giọng Nói
* `POST /api/v1/tts/stream`: (`[⚡ Phát ngay]`) Kiểm duyệt AI -> Áp dụng chuẩn hóa Toán/Hóa -> Áp dụng Từ điển phát âm -> Stream audio chunk về client.
* `POST /api/v1/tts/generate`: (`[🔊 Tạo giọng nói]`) Tạo bản ghi hoàn chỉnh, trừ token & hạn mức ký tự ngày, lưu vào `tts_recordings` (vẫn giữ nguyên `original_text` để hiển thị trong thư viện).
* `GET /api/v1/tts/recordings`: Lấy danh sách bản ghi cho mục *Các bản ghi gần đây* và trang *Giọng nói của tôi* (Hỗ trợ query `?search=...&voice_id=...&page=1&limit=20`). Trả về kèm `total_count` và `total_duration_seconds`.
* `DELETE /api/v1/tts/recordings/:id`: Xóa bản ghi âm thanh.

### 5.3. Nhóm API Podcast Studio
* `POST /api/v1/podcasts/parse-script`: (`[📋 Dán kịch bản]`) Phân tích văn bản kịch bản thô thành mảng các lượt thoại `{ speaker_role, content }`.
* `POST /api/v1/podcasts/ai-generate-script`: (`[✨ Viết kịch bản bằng AI]`) Sinh kịch bản hội thoại tự động bằng LLM theo chủ đề người dùng nhập.
* `POST /api/v1/podcasts`: (`[🎙️ Tạo podcast]`) Gửi danh sách lượt thoại (tối đa 200 lượt cho gói thường, 1.000 lượt cho gói trả phí) để tổng hợp và ghép thành tập podcast hoàn chỉnh.
* `GET /api/v1/podcasts`: Lấy danh sách `PODCAST ĐÃ TẠO`.

### 5.4. Nhóm API Phòng Thu Truyện (Story Studio)
* `GET /api/v1/stories` & `POST /api/v1/stories`: Lấy danh sách dự án truyện ở cột trái và tạo `+ Truyện mới`.
* `POST /api/v1/stories/:id/characters`: Thêm/cập nhật nhân vật kèm giọng đọc và màu sắc đánh dấu.
* `POST /api/v1/stories/:id/segments/:segmentId/generate`: Tạo hoặc tạo lại giọng nói cho **đúng 1 phân đoạn** mà không ảnh hưởng tới các phân đoạn khác.
* `PUT /api/v1/stories/:id/segments/reorder`: Cập nhật thứ tự kéo-thả (`sort_order`) của các phân đoạn.
* `POST /api/v1/stories/:id/export`: Ghép toàn bộ các phân đoạn thành **MỘT file âm thanh liền mạch**.

### 5.5. Nhóm API Bảng Xếp Hạng Giọng (Voice Leaderboard)
* `GET /api/v1/voices/leaderboard`:
  * Query params: `period` (`7d` | `all`), `gender` (`ALL` | `NU` | `NAM`), `region` (`ALL` | `BAC` | `TRUNG` | `NAM`).
  * Trả về: `total_voices` (`50`), `updated_at` (`06:20 01-11`), và mảng xếp hạng gồm Top 3 Podium + danh sách hạng 4–50 với tỷ lệ `popularity_ratio` tính theo số người dùng duy nhất (`unique_users`).

### 5.6. Nhóm API Thanh Toán & Đăng Ký (Billing)
* `GET /api/v1/billing/plans`: Lấy danh sách gói token (`Starter`, `Creator`, `Pro`, `Studio`), thông tin quy đổi giờ âm thanh V4 và trạng thái bản quyền Desktop App.
* `POST /api/v1/billing/vouchers/validate`: Kiểm tra mã giảm giá (VD: `THINHVUONG` giảm 15% cho `CREATOR`, `PRO`, `STUDIO`) và trả về giá sau giảm.
* `POST /api/v1/billing/checkout`: Khởi tạo giao dịch mua/nâng cấp gói token (có tính hoàn trả token chưa dùng theo tỷ lệ pro-rata).

### 5.7. Nhóm API Nhà Phát Triển & Từ Điển Phát Âm
* `GET /api/v1/developer/keys` & `POST /api/v1/developer/keys`: Quản lý khóa API theo môi trường `LIVE` và `TEST`.
* `GET /api/v1/developer/mcp-connections`: Lấy danh sách ứng dụng AI đã kết nối qua `https://api.vieneu.io/mcp`.
* `GET /api/v1/dictionary` & `PUT /api/v1/dictionary`: Lấy và lưu danh sách tối đa 2.000 luật phát âm của tài khoản.
* `POST /api/v1/dictionary/import` & `GET /api/v1/dictionary/export`: Nhập/xuất tệp `.txt` hoặc `.csv` theo đúng quy chuẩn phân tách `=`, `→`, `\t`, `,` và bỏ qua dòng `#`.

---

## 6. Checklist Nghiệm Thu Dành Cho QA & Frontend/Backend (Acceptance Criteria)

1. **Kiểm duyệt & Điều khoản:** Người dùng chưa đồng ý điều khoản bắt buộc phải thấy Modal *Điều khoản tạo giọng nói* và không thể bấm tiếp tục nếu chưa tích chọn checkbox.
2. **Đếm Token & Hạn mức Real-time:** Mọi thay đổi văn bản trong *Phòng thu* và *Podcast* phải cập nhật số ký tự và ước tính token ngay lập tức; hiển thị chính xác hạn mức `50.000 ký tự hôm nay`.
3. **Chuẩn hóa Công thức & Từ điển:**
   * Gõ công thức toán/hóa học (`ax² + bx + c = 0`, `2H2 + O2 → 2H2O`) phải được đọc đúng tự nhiên.
   * Từ điển phát âm phải ưu tiên từ dài hơn (`km/h` trước `km`), không quét lặp đệ quy, giữ nguyên văn bản gốc trong lịch sử thư viện, và không áp dụng vào `/v1` Developer API.
4. **Tính độc lập của Phân đoạn Truyện:** Sửa một đoạn trong *Phòng thu Truyện* chỉ yêu cầu tạo lại đúng đoạn đó; kéo-thả đổi vị trí bằng icon `⠿` và bấm *Xuất truyện* phải ghép đúng thứ tự mới.
5. **Độ chính xác Bảng xếp hạng:** Bảng xếp hạng chỉ tính mỗi `user_id` tối đa 1 lần cho mỗi giọng trong kỳ (7 ngày hoặc mọi lúc), lọc tức thì khi bấm tổ hợp Giới tính + Vùng miền.
