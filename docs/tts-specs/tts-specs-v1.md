# Đặc Tả Kỹ Thuật (Specification): Công Cụ Tiền Xử Lý & Điều Khiển Ngắt Nghỉ Tự Động Cho Dịch Vụ Đọc Truyện Với VieNeu-TTS

## 1. Mục Tiêu & Phạm Vi Hệ Thống — Tạo Nhịp Đọc Giàu Cảm Xúc Mà Không Cần Fine-Tune Mô Hình

Tài liệu này quy định kiến trúc, bộ quy tắc ngôn ngữ học và luồng xử lý của **Prosody & Script Preprocessor Tool** — công cụ tự động chuẩn hóa văn bản truyện, phân vai nhân vật và chèn cú pháp điều khiển nhịp ngắt nghỉ/biểu cảm đầu vào cho engine [VieNeu-TTS v3 Turbo](https://github.com/pnnbao97/VieNeu-TTS/blob/main/README.vi.md).

Hệ thống được thiết kế dựa trên phân tích thực nghiệm từ hai mẫu văn bản tiểu thuyết có cấu trúc phức tạp:
1. **Mẫu 1 — [The Chronicles of the Ash Land](https://file5.bkglobal.vn/techbkglobal/The_Chronicles_of_the_Ash_Land/index.html):** Tiểu thuyết kỳ huyễn lấy bối cảnh Trung Địa với câu đại tự sự dài (40–70 từ), mật độ dấu gạch ngang dài (`—`) dày đặc, danh từ riêng giả tưởng (`Udûn-gath`, `Muzgash`, `Gorgûl`) và hội thoại định dạng chuẩn Việt – Pháp (`"..." — Nhân vật`).
2. **Mẫu 2 — Tiểu thuyết *Hogwarts / Dracaena Malfoy*:** Văn bản giàu kịch tính với nhịp câu biến thiên mạnh (từ câu đại cảnh dài 60 từ xuống chuỗi câu đếm giây chỉ 2–4 từ), hội thoại định dạng chuẩn Anh – Mỹ (`"...", lời dẫn. "..."`), lời hô vang viết hoa toàn bộ (`"GRYFFINDOR!"`), và **độc thoại nội tâm / thần giao cách cảm không có dấu ngoặc kép** (cuộc đối thoại trong tâm trí với Chiếc Nón Phân Loại).

---

## 2. Sáu Phát Hiện Mới Từ Đoạn Mẫu *Hogwarts / Dracaena Malfoy* & Giải Pháp Kỹ Thuật

Khi đối chiếu đoạn văn bản *Dracaena Malfoy tại lễ Phân Loại* với mẫu [The Chronicles of the Ash Land](https://file5.bkglobal.vn/techbkglobal/The_Chronicles_of_the_Ash_Land/index.html), bộ tiền xử lý cần giải quyết thêm 6 trường hợp biên (edge cases) quan trọng để tránh đọc đều đều hoặc đứt gãy ngữ điệu:

| STT | Hiện tượng trong văn bản mẫu | Rủi ro nếu đưa thẳng vào VieNeu-TTS | Quy tắc xử lý trong Tool (Preprocessor Rule) |
| :--- | :--- | :--- | :--- |
| **1** | **Lỗi mất chữ cái đầu chương do Drop Cap UI** (`"ặt nước Hồ Đen vào đêm..."` mất chữ `M`) | Bộ phiên âm đọc thành từ vô nghĩa *"ặt nước"*. | **Drop-Cap Recovery Filter:** Kiểm tra từ đầu tiên của chương; nếu bắt đầu bằng chữ thường hoặc vần khuyết phụ âm đầu (`ặt nước`, `hi ông Bilbo`), tự động ghép với ký tự Drop Cap bị tách rời trên DOM hoặc khôi phục từ từ điển cụm từ mở đầu (`Mặt nước`, `Khi ông`). |
| **2** | **Đối thoại trong tâm trí không có ngoặc kép** (`Chà, một người nhà Malfoy nữa... Tôi là một Malfoy.`) | TTS đọc trộn lẫn lời dẫn ngôi thứ 3 (`Dracaena ngồi im.`) với tiếng nói của Chiếc Nón và suy nghĩ của Dracaena bằng cùng một nhịp. | **Telepathic / Inner-Voice Detector:** Nhận diện dấu hai chấm mở đầu nội tâm (`vang lên trong tâm trí cô:`) và các cụm dẫn thoại chen giữa (`, chiếc nón thì thầm.`, `, giọng nói tiếp tục,`) kèm đại từ ngôi thứ nhất/hai (`Tôi`, `Con`, `Chà,`, `Đúng vậy,`) để tách nhịp nghỉ `[0.4]` và đổi sang giọng nội tâm hoặc giảm tốc độ `speed=0.92`. |
| **3** | **Chuỗi câu cực ngắn đếm thời gian / dồn nén** (`Một giây trôi qua. Năm giây. Mười giây. Ba mươi giây.`) | Quy tắc câu ngắn thông thường chỉ nghỉ `0.3s` khiến TTS đọc lướt quá nhanh, làm mất hoàn toàn sự hồi hộp của 30 giây chờ đợi. | **Progressive Dramatic Pause (Ngắt tăng tiến):** Khi gặp chuỗi `>= 3` câu ngắn liên tiếp (`<= 5 từ/câu`) hoặc có từ chỉ thời gian (`giây`, `phút`, `im lặng`), tự động tăng dần thẻ nghỉ theo cấp số cộng: `[0.6]` → `[0.85]` → `[1.1]` → `[1.4]`. |
| **4** | **Tiếng hô vang viết IN HOA toàn bộ & Gọi tên** (`"Granger, Hermione!"`, `"GRYFFINDOR!"`, `"SLYTHERIN!"`) | Chữ IN HOA dài dễ bị G2P hiểu nhầm là từ viết tắt (đánh vần từng chữ cái); dấu phẩy giữa `"Họ, Tên!"` bị đọc lướt mất vẻ trang trọng. | **Shout & Roll-Call Normalizer:** Hạ chữ IN HOA về dạng Title Case (`"Gryffindor!"`) hoặc phiên âm trước khi qua G2P, gắn cờ `emphasis="high"`, thêm nghỉ chờ hồi hộp `[0.65]` trước tiếng hô và `[0.9]` sau tiếng hô; với mẫu `"Họ, Tên!"`, đổi dấu `,` thành `... [0.25]`. |
| **5** | **Hội thoại chuẩn Anh – Mỹ có lời dẫn chen giữa** (`"Trần nhà không có thật đâu," cô bé thì thầm. "Nó chỉ được yểm bùa..."`) | Dấu phẩy nằm trong ngoặc kép `,"` làm lệch bộ cắt câu; câu thoại thứ hai dễ bị gán nhầm cho giọng người dẫn. | **Split-Dialogue Linker:** Chuẩn hóa `,"` và `."` trước khi tách chunk; nếu cấu trúc là `[Thoại 1] + [Lời dẫn ngắn kết thúc bằng dấu chấm] + [Thoại 2]`, tự động gán `Thoại 2` cho cùng nhân vật của `Thoại 1`. |
| **6** | **Câu trích dẫn lồng trong câu tự sự** (`câu nói "Chính xác là người mà con được kỳ vọng phải trở thành" vẫn vương lại...`) | Bộ tách hội thoại nhầm cụm `"..."` là một lượt nhân vật phát ngôn độc lập, làm đứt mạch câu trần thuật. | **Embedded Quote Guard:** Nếu cụm `"..."` đứng ngay sau danh từ (`câu nói`, `chữ`, `cụm từ`), bắt đầu và kết thúc giữa câu mà không có dấu kết câu hay gạch ngang `—`, giữ nguyên giọng `Narrator` và chỉ bọc nhẹ bằng `... [0.2] "..." [0.25]`. |

---

## 3. Kiến Trúc Tổng Thể Của Công Cụ (5-Stage Pipeline)

Công cụ được thiết kế theo mô hình **Hybrid Rule-based & Prosodic Heuristic** (không phụ thuộc LLM khi chạy thời gian thực, tốc độ xử lý `< 20ms/chương`, có thể mở rộng thêm mô-đun LLM Annotator cho chế độ dựng sẵn Audiobook):

```text
[Văn bản gốc (.md / HTML)]
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ TẦNG 1: Text & DOM Sanitizer (Làm sạch & Khôi phục)      │
│ - Lọc bỏ Metadata đầu chương (số từ, thời gian đọc, CSV) │
│ - Khôi phục ký tự Drop Cap đầu đoạn ("ặt nước" -> "Mặt") │
│ - Chuẩn hóa bảng mã Unicode, dấu ngoặc kép (" "), dấu —  │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ TẦNG 2: Discourse & Dialogue Parser (Phân tách cấu trúc) │
│ - Phân loại đoạn: Trần thuật / Hội thoại trực tiếp /     │
│   Hội thoại nội tâm (Telepathy) / Tiếng hô độc lập       │
│ - Phân biệt "Hội thoại thật" vs "Trích dẫn giữa câu"     │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ TẦNG 3: Prosody & Pause Engine (Điền ngắt nghỉ & Nhịp)   │
│ - Phối hợp Ngắt mềm (dấu `,`, `...`) và Ngắt cứng `[s]`  │
│ - Tính toán thời gian nghỉ theo độ dài câu & nhịp kịch   │
│ - Tự động chèn tag cảm xúc: `[cười]`, `[thở dài]`        │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ TẦNG 4: Lexicon & Phonetic Mapper (Chuẩn hóa phát âm)    │
│ - Ánh xạ tên riêng Trung Địa / Hogwarts sang phiên âm    │
│   tiếng Việt hoặc bọc thẻ `<en>...</en>`                 │
│ - Chuyển từ IN HOA ("SLYTHERIN!") về dạng đọc chuẩn      │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ TẦNG 5: Output Formatter (Xuất đầu ra đa định dạng)      │
│ - Chế độ 1: Văn bản phẳng gắn sẵn tag cho VieNeu Studio  │
│ - Chế độ 2: JSON Chunks kèm `voice`, `speed`, `pause_ms` │
│   để gọi trực tiếp `vieneu.infer()` / `infer_stream()`   │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Bộ Quy Tắc Chi Tiết Tự Động Điền Ngắt Nghỉ & Cảm Xúc (Rulebook)

### 4.1. Quy tắc Phân bổ "Ngắt mềm" (Soft Pause) và "Ngắt cứng" (Hard Pause)

Theo cơ chế của [VieNeu-TTS v3 Turbo](https://github.com/pnnbao97/VieNeu-TTS/blob/main/README.vi.md) và ghi chú kỹ thuật tại [VieNeu Releases v0.18.8 & v0.18.9](https://github.com/pnnbao97/VieNeu-TTS/releases), việc cắt nhỏ câu tại mọi dấu phẩy sẽ làm mất sự liền mạch của ngữ điệu. Do đó, công cụ áp dụng nguyên tắc:
* **Không chèn thẻ `[số_giây]` vào các dấu phẩy thông thường** nối các cụm ngắn (`< 12 từ`).
* **Dùng dấu ba chấm `...` (Ngắt mềm)** khi cần tạo độ ngân, ngập ngừng hoặc hạ giọng ở cuối mệnh đề phụ.
* **Chỉ chèn thẻ `[số_giây]` (Ngắt cứng)** ở ranh giới kết thúc câu, chuyển vai người nói, cặp gạch ngang giải thích, hoặc giữa hai mệnh đề quá dài (`> 18 từ`).

### 4.2. Bảng Ma trận Thời gian Ngắt nghỉ (Pause Duration Matrix)

| Mã Rule | Loại ranh giới / Ngữ cảnh | Điều kiện kích hoạt (Condition) | Cú pháp chèn vào văn bản | Thời lượng nghỉ (Giây) |
| :--- | :--- | :--- | :--- | :--- |
| **P-01** | **Câu trần thuật ngắn (Hành động)** | Kết thúc bằng `.`, độ dài `5 – 14 từ`, không thuộc chuỗi đếm | `[0.35]` | `0.35s` |
| **P-02** | **Câu trần thuật tiêu chuẩn** | Kết thúc bằng `.`, độ dài `15 – 34 từ` | `[0.55]` | `0.55s` |
| **P-03** | **Câu đại tự sự (Miêu tả bối cảnh dài)** | Kết thúc bằng `.`, độ dài `>= 35 từ` (VD: câu mở đầu Hồ Đen / Bilbo) | `[0.85]` | `0.85s` |
| **P-04** | **Câu cực ngắn nhấn mạnh / Độc lập** | Câu `<= 4 từ` đứng đầu hoặc cuối đoạn (`Không ai mỉm cười.`, `Cuộn giấy da được mở ra.`) | `[0.75]` | `0.75s` |
| **P-05** | **Chuỗi câu đếm thời gian / Dồn nén** | `>= 3` câu ngắn liên tiếp hoặc chứa số + `giây / phút / bước` | Tăng tiến: `[0.6]` → `[0.85]` → `[1.1]` → `[1.4]` | `0.60s – 1.40s` |
| **P-06** | **Câu hỏi & Câu cảm thán** | Kết thúc bằng `?`, `!`, `?!` | `[0.65]` | `0.65s` |
| **P-07** | **Tiếng hô phân loại / Gọi tên độc lập** | Câu thoại 1–3 từ đứng riêng 1 dòng (`"GRYFFINDOR!"`, `"Potter, Harry!"`) | Trước câu: `[0.5]` / Sau câu: `[0.9]` | `0.50s` & `0.90s` |
| **P-08** | **Cặp gạch ngang giải thích (`— ... —`)** | Mẫu `A — B — C` nằm trong câu | `A... [0.3] B... [0.35] C` | `0.30s` & `0.35s` |
| **P-09** | **Gạch ngang mở rộng ý cuối câu (`— ... .`)** | Mẫu `A — B.` (VD: `sừng sững trên đỉnh vách đá dựng đứng — một quần thể đồ sộ...`) | `A... [0.4] B.` | `0.40s` |
| **P-10** | **Ngắt lấy hơi giữa câu ghép siêu dài** | Vế trước dấu `,` dài `>= 18 từ` VÀ theo sau bởi từ nối (`nhưng`, `thế nhưng`, `thì`, `khi`, `và phía trên`, `để lại`) | Đổi `,` thành `,... [0.3]` | `0.30s` |
| **P-11** | **Chuyển giữa Lời thoại & Lời dẫn** | Ranh giới `"..." — Lời dẫn` hoặc `"...", lời dẫn.` | `[0.35]` | `0.35s` |
| **P-12** | **Chuyển vào Độc thoại nội tâm** | Sau dấu `:` của câu dẫn tâm trí hoặc trước/sau `, chiếc nón thì thầm.` | `[0.45]` | `0.45s` |
| **P-13** | **Kết thúc đoạn văn (`\n`)** | Xuống dòng sang đoạn văn mới | `[1.0]` | `1.00s` |
| **P-14** | **Chuyển cảnh / Kết chương (`***`)** | Ký hiệu đổi cảnh hoặc chuyển mục | `[1.8]` | `1.80s` |

### 4.3. Quy tắc Tự động Chèn Thẻ Cảm xúc & Điều chỉnh Tốc độ (`speed`)

Công cụ quét phần lời dẫn đi kèm câu thoại (dialogue tag) để tự động gắn thẻ phi ngôn từ của [VieNeu-TTS v3 Turbo](https://github.com/pnnbao97/VieNeu-TTS/blob/main/README.vi.md) và điều chỉnh tham số `speed`:

| Nhóm sắc thái | Từ khóa phát hiện trong lời dẫn (Trigger Keywords) | Thẻ chèn tự động | Hệ số tốc độ (`speed`) |
| :--- | :--- | :--- | :--- |
| **Vui vẻ / Cười** | `cười`, `bật cười`, `khúc khích`, `tủm tỉm`, `hài hước` | Chèn `[cười]` ở đầu hoặc cuối câu thoại | `1.02` |
| **Trầm ngâm / Thở dài** | `thở dài`, `não nề`, `buồn bã`, `trầm ngâm`, `lặng lẽ` | Chèn `[thở dài]` trước câu thoại | `0.92` |
| **Ngập ngừng / Nghiêm giọng** | `hắng giọng`, `de dọa`, `nghiêm nghị`, `lạnh lùng` | Chèn `[hắng giọng]` (nếu phù hợp ngữ cảnh) | `0.95` |
| **Thì thầm / Nói nhanh** | `thì thầm rất nhanh`, `liến thoắng`, `vội vã`, `lao tới` | Giữ câu liền mạch, giảm nghỉ cuối câu còn `[0.25]` | `1.08` |
| **Hô vang / Gào lớn** | `hô lớn`, `hô vang`, `hét vang`, `gào lên`, `reo lên` | Chuyển chữ IN HOA về chữ thường có dấu chấm than `!` | `0.95` (để kéo dài âm vang) |
| **Độc thoại nội tâm / Bí ẩn** | `trong tâm trí`, `trong đầu`, `tự nhủ`, `chiếc nón thì thầm` | Đổi dấu `,` giữa các vế ngắn thành `...` | `0.92` |

### 4.4. Quy tắc Chuẩn hóa Từ vựng & Tên riêng (Lexicon Mapping)

Để bộ phiên âm `sea-g2p` của [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS/blob/main/README.vi.md) đọc mượt mà cả tên riêng tiếng Anh phổ thông lẫn tên giả tưởng cổ ngữ (Elvish / Black Speech / Latin):
1. **Nhóm từ tiếng Anh chuẩn (bọc thẻ `<en>` hoặc giữ nguyên nếu dùng v3 Turbo song ngữ):** `Harry Potter`, `Hogwarts`, `Scotland`, `Weasley`, `Madam Malkin`.
2. **Nhóm danh từ kỳ huyễn / dễ đọc lệch âm (ánh xạ qua từ điển `custom_lexicon.json`):**
   * *The Chronicles of the Ash Land:* `Udûn-gath` → `U-đun gát`, `Gorgûl` → `Go-gun`, `Muzgash` → `Mút-gát`, `Gorgoroth` → `Go-gô-rốt`, `Dorwinion` → `Đo-uy-ni-on`, `Ephel Dúath` → `Ê-phen Đu-át`, `Lugbúrz` → `Lúc-bua`.
   * *Hogwarts / Dracaena Malfoy:* `Dracaena` → `Đờ-ra-xê-na`, `Hermione Granger` → `Hơ-mai-ơ-ni Gờ-ren-giơ`, `McGonagall` → `Mắc-go-na-gôn`, `Gryffindor` → `Gờ-ríp-phin-đo`, `Slytherin` → `Sờ-li-thơ-rin`, `Daphne Greengrass` → `Đáp-ni Gờ-rin-gờ-rát`, `Pansy` → `Pan-xi`.

---

## 5. Minh Họa Kết Quả Xử Lý Thực Tế Trên Đoạn Mẫu *Dracaena Malfoy*

### 5.1. Văn bản đầu vào (Raw Input)

> ặt nước Hồ Đen vào đêm mồng một tháng Chín phẳng lặng và đen nhánh như một tấm gương bằng đá hắc diện thạch khổng lồ, phản chiếu hàng ngàn ngôi sao lấp lánh của vùng cao nguyên Scotland. Khi đoàn thuyền gỗ nhỏ lướt đi êm ru không cần mái chèo dưới sự dẫn đường của lão Hagrid khổng lồ, tòa lâu đài Hogwarts dần hiện ra sừng sững trên đỉnh vách đá dựng đứng — một quần thể đồ sộ gồm những tháp canh nhọn hoắt, những bức tường đá cổ kính rêu phong và hàng trăm ô cửa sổ rực sáng như những viên hồng ngọc treo lơ lửng giữa bầu trời đêm.
> ...
> Vành nón hơi rộng, sụp xuống che khuất tầm mắt. Ngay lập tức, một giọng nói nhỏ nhẹ, khô khốc vang lên trong tâm trí cô:
> Chà, một người nhà Malfoy nữa. Đã lâu rồi đấy.
> Dracaena ngồi im. Thông minh. Rất thông minh, chiếc nón thì thầm. Lòng kiêu hãnh không thiếu. Tham vọng cũng rất rõ ràng. Con biết chính xác mình là ai, phải không? Hoặc ít nhất... con biết rất rõ mình được kỳ vọng phải trở thành ai. Dracaena khẽ nhíu mày dưới vành nón. Tôi là một Malfoy. Tôi thuộc về Slytherin.
> ...
> "Potter, Harry!"
> Dracaena ngẩng đầu lên ngay lập tức. Harry bước lên chiếc ghế đẩu. Dưới ánh nến rực rỡ, cậu trông càng nhỏ bé hơn trong chiếc áo chùng mới. Chiếc nón sụp xuống đầu cậu. Một giây trôi qua. Năm giây. Mười giây. Ba mươi giây.
> Chiếc nón vẫn im lặng. Dracaena nhìn thấy những ngón tay của Harry bấu chặt vào mép ghế gỗ, môi cậu khẽ mấp máy như đang tranh luận điều gì đó với giọng nói bên trong đầu. Rồi chiếc nón hét vang:
> "GRYFFINDOR!"

### 5.2. Văn bản đầu ra Chế độ 1 (Formatted Script cho VieNeu Studio / Kịch bản Sách nói)

```text
// Phân cảnh 1: Hồ Đen & Đại Sảnh Đường
Người dẫn: Mặt nước Hồ Đen vào đêm mồng một tháng Chín phẳng lặng và đen nhánh như một tấm gương bằng đá hắc diện thạch khổng lồ,... [0.3] phản chiếu hàng ngàn ngôi sao lấp lánh của vùng cao nguyên <en>Scotland</en>. [0.85] Khi đoàn thuyền gỗ nhỏ lướt đi êm ru không cần mái chèo dưới sự dẫn đường của lão Ha-gờ-rít khổng lồ,... [0.3] tòa lâu đài Hốc-goát dần hiện ra sừng sững trên đỉnh vách đá dựng đứng... [0.4] một quần thể đồ sộ gồm những tháp canh nhọn hoắt, những bức tường đá cổ kính rêu phong,... [0.3] và hàng trăm ô cửa sổ rực sáng như những viên hồng ngọc treo lơ lửng giữa bầu trời đêm. [1.0]

// Phân cảnh 2: Đối thoại nội tâm với Chiếc Nón Phân Loại
Người dẫn: Vành nón hơi rộng, sụp xuống che khuất tầm mắt. [0.45] Ngay lập tức, một giọng nói nhỏ nhẹ, khô khốc vang lên trong tâm trí cô: [0.6]

Nón Phân Loại: Chà... [0.25] một người nhà Man-phôi nữa. [0.45] Đã lâu rồi đấy. [0.6]

Người dẫn: Đờ-ra-xê-na ngồi im. [0.45]

Nón Phân Loại: Thông minh... [0.3] Rất thông minh. [0.35]

Người dẫn: Chiếc nón thì thầm. [0.4]

Nón Phân Loại: Lòng kiêu hãnh không thiếu. [0.35] Tham vọng cũng rất rõ ràng. [0.45] Con biết chính xác mình là ai, phải không? [0.6] Hoặc ít nhất... [0.35] con biết rất rõ mình được kỳ vọng phải trở thành ai. [0.65]

Người dẫn: Đờ-ra-xê-na khẽ nhíu mày dưới vành nón. [0.45]

Dracaena (Nội tâm): Tôi là một Man-phôi. [0.35] Tôi thuộc về Sờ-li-thơ-rin. [0.7]

// Phân cảnh 3: Cao trào phân loại Harry Potter
McGonagall: Pót-tơ... [0.25] Ha-ri! [0.8]

Người dẫn: Đờ-ra-xê-na ngẩng đầu lên ngay lập tức. [0.35] Ha-ri bước lên chiếc ghế đẩu. [0.35] Dưới ánh nến rực rỡ, cậu trông càng nhỏ bé hơn trong chiếc áo chùng mới. [0.5] Chiếc nón sụp xuống đầu cậu. [0.6] Một giây trôi qua... [0.65] Năm giây... [0.85] Mười giây... [1.1] Ba mươi giây... [1.4]

Người dẫn: Chiếc nón vẫn im lặng. [0.55] Đờ-ra-xê-na nhìn thấy những ngón tay của Ha-ri bấu chặt vào mép ghế gỗ,... [0.3] môi cậu khẽ mấp máy như đang tranh luận điều gì đó với giọng nói bên trong đầu. [0.65] Rồi chiếc nón hét vang: [0.65]

Nón Phân Loại: Gờ-ríp-phin-đo! [1.0]
```

### 5.3. Văn bản đầu ra Chế độ 2 (JSON Payload cho Backend API / Streaming Service)

```json
[
  {
    "chunk_id": "ch01_p13_s01",
    "speaker": "McGonagall",
    "voice_preset": "Đoan Trang",
    "role_type": "dialogue_shout",
    "text": "Pót-tơ... Ha-ri!",
    "speed": 0.95,
    "temperature": 0.8,
    "pause_before_sec": 0.4,
    "pause_after_sec": 0.8
  },
  {
    "chunk_id": "ch01_p14_s05",
    "speaker": "Narrator",
    "voice_preset": "Thiện Minh",
    "role_type": "narration_countdown",
    "text": "Một giây trôi qua...",
    "speed": 0.92,
    "temperature": 0.8,
    "pause_before_sec": 0.0,
    "pause_after_sec": 0.65
  },
  {
    "chunk_id": "ch01_p14_s06",
    "speaker": "Narrator",
    "voice_preset": "Thiện Minh",
    "role_type": "narration_countdown",
    "text": "Năm giây...",
    "speed": 0.90,
    "temperature": 0.8,
    "pause_before_sec": 0.0,
    "pause_after_sec": 0.85
  }
]
```

---

## 6. Cấu Trúc Thư Mục & Giao Diện Dòng Lệnh (CLI / SDK Interface) Dự Kiến

Để dễ dàng tích hợp vào web đọc truyện hiện tại cũng như chạy xử lý hàng loạt cho 65 chương của [The Chronicles of the Ash Land](https://file5.bkglobal.vn/techbkglobal/The_Chronicles_of_the_Ash_Land/index.html), công cụ sẽ được tổ chức thành một module Python độc lập:

```text
vieneu_story_preprocessor/
├── config/
│   ├── pause_rules.yaml          # Tham số thời gian nghỉ (có thể tinh chỉnh nóng)
│   ├── lexicon_middle_earth.json # Từ điển phiên âm The Chronicles of the Ash Land
│   └── lexicon_hogwarts.json     # Từ điển phiên âm Hogwarts / Dracaena
├── core/
│   ├── sanitizer.py              # Lọc metadata, khôi phục Drop Cap, chuẩn hóa dấu câu
│   ├── dialogue_parser.py        # Tách lời dẫn, lời thoại ("..."), nội tâm & trích dẫn
│   ├── prosody_annotator.py      # Điền tag [0.x], dấu ..., [cười], [thở dài]
│   └── lexicon_mapper.py         # Ánh xạ tên riêng & xử lý từ IN HOA
├── exporters/
│   ├── studio_txt_exporter.py    # Xuất file .txt kịch bản cho VieNeu Studio
│   └── sdk_json_exporter.py      # Xuất file .json + hàm đọc trực tiếp với SDK vieneu
└── cli.py                        # Công cụ chạy dòng lệnh cho 1 file hoặc cả thư mục .md
```

---

## 7. Kế Hoạch Triển Khai Tiếp Theo (Implementation Roadmap)

1. **Giai đoạn 1 — Xây dựng Core Preprocessor (Rule-based & Regex):**
   * Hiện thực hóa `sanitizer.py` và `prosody_annotator.py` bao phủ toàn bộ 14 quy tắc ngắt nghỉ (`P-01` đến `P-14`) và bộ khôi phục Drop Cap.
   * Kiểm thử trực tiếp trên Chương 1 của [The Chronicles of the Ash Land](https://file5.bkglobal.vn/techbkglobal/The_Chronicles_of_the_Ash_Land/index.html) và đoạn trích *Dracaena Malfoy*.
2. **Giai đoạn 2 — Xây dựng Bộ Tách Hội Thoại & Nội Tâm (Dialogue & Telepathy Parser):**
   * Nhận diện cả 2 chuẩn ngoặc kép (Việt – Pháp dùng `—` và Anh – Mỹ dùng `,"`), lọc bỏ các cụm trích dẫn giữa câu (`Embedded Quote Guard`) và tách luồng độc thoại nội tâm.
3. **Giai đoạn 3 — Tích hợp Bộ Tổng Hợp Âm Thanh VieNeu-TTS & Cache Audio:**
   * Viết hàm runner kết nối đầu ra JSON với `vieneu.infer()` / `vieneu.infer_batch()` (48 kHz), ghép nối các mảng âm thanh kèm khoảng lặng chính xác đến từng mili-giây và xuất ra MP3/FLAC phục vụ nút **Nghe đọc** trên giao diện web.
