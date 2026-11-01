# 07. Đặc Tả Phân Hệ Từ Điển Phát Âm & Chuẩn Hóa Văn Bản (Pronunciation Dictionary & NLP Pipeline)

* **Tham chiếu hình ảnh:** `../assets/screens/10_tu_dien_phat_am.png` (`image_4664d0.png`)
* **Route:** `/dictionary`

---

## 1. Mục Đích Nghiệp Vụ
Cho phép người dùng tự định nghĩa cách đọc cho các tên riêng, thuật ngữ nước ngoài, ký hiệu kỹ thuật hoặc chữ viết tắt (ví dụ viết `VieNeu` đọc là `Vi Nơi`). Bộ từ điển này gắn theo tài khoản (`[Theo tài khoản]`) và được áp dụng tự động cho mọi lượt tạo giọng nói trên giao diện web: **Phòng thu, Truyện, Lồng tiếng và Phát ngay**.

---

## 2. Đặc Tả Giao Diện (UI Components)

### 2.1. Header Trang
* Tiêu đề: **Từ điển phát âm** (`22px`, Bold) + Badge `[Theo tài khoản]` (nền tím nhạt `rgba(124, 92, 252, 0.15)`, chữ tím `#A78BFA`, `12px`).
* Mô tả dưới tiêu đề:
  > *Dạy engine cách đọc tên riêng, thuật ngữ, chữ viết tắt. Áp dụng tự động cho mọi lượt tạo trên web: Phòng thu, Truyện, Lồng tiếng và Phát ngay.*

### 2.2. Bố Cục 2 Cột Chính (`Grid 64% : 36%`)

#### A. Cột Trái — Khung Quản Lý Danh Sách Luật Phát Âm
1. **Thanh công cụ trên cùng (Dictionary Action Bar):**
   * **Cụm nút bên trái:**
     * `[+ Thêm luật]`: Nền `#1A1A24`, viền `#2E2E42`, thêm một dòng nhập luật mới vào bảng.
     * `[📄 Nhập từ tệp]`: Nền `#1A1A24`, viền `#2E2E42`, mở hộp thoại chọn file `.txt` hoặc `.csv` để import hàng loạt.
     * `⬇️ Xuất ra tệp`: Nút text/icon cho phép tải toàn bộ danh sách luật hiện có về máy.
   * **Cụm trạng thái & Lưu bên phải:**
     * Bộ đếm: `1 luật · tối đa 2000` (`12px`, `#9CA3AF`).
     * Nút `[💾 Lưu từ điển]`: Nền tím `#7C5CFC`, chữ trắng đậm (Lưu toàn bộ thay đổi trên bảng xuống Backend).

2. **Bảng Danh Sách Luật (Rules Table):**
   * **Header Cột (`11px`, in hoa, `#6B7280`, `font-weight: 600`):**
     * Cột 1 (`35%`): `TỪ NHƯ ĐANG VIẾT`
     * Cột 2 (`35%`): `ENGINE ĐỌC LÀ`
     * Cột 3 (`10%`, căn giữa): `CẢ TỪ`
     * Cột 4 (`12%`, căn giữa): `PHÂN BIỆT HOA/THƯỜNG`
     * Cột 5 (`8%`, căn phải): *(Hành động Bật/Tắt & Xóa)*
   * **Dòng Dữ liệu Luật (Rule Row):**
     * **Ô Input 1 (`TỪ NHƯ ĐANG VIẾT`):** Nhập từ gốc trong văn bản, ví dụ `VieNeu`.
     * **Ô Input 2 (`ENGINE ĐỌC LÀ`):** Nhập cách đọc phiên âm tiếng Việt, ví dụ `Vi Nơi`.
     * **Checkbox `CẢ TỪ`:** Mặc định `checked` (`[v]`, nền tím `#7C5CFC`).
     * **Checkbox `PHÂN BIỆT HOA/THƯỜNG`:** Mặc định `unchecked` (`[ ]`).
     * **Hành động bên phải:**
       * Công tắc/Icon Bật-Tắt luật (`[●]`) để tạm vô hiệu hóa luật mà không cần xóa.
       * Nút xóa dòng luật (`[🗑️]`).

#### B. Cột Phải — Công Cụ Test Trực Tiếp & Hộp Giải Thích Quy Tắc
1. **Card Trên — `Nghe thử cách đọc` (Real-time Rule Preview Box):**
   * Tiêu đề: **Nghe thử cách đọc** (`15px`, Bold).
   * Mô tả: *Gõ một câu có chứa từ trong từ điển. Kết quả bên dưới là văn bản engine sẽ nhận (đang tính theo bảng hiện tại, kể cả chưa lưu).*
   * **Ô Textarea nhập câu thử:**
     * Ví dụ mặc định: `Bản VieNeu 2.0 chạy trên GPU, nhanh hơn 5 km/h.`
   * **Khung hiển thị kết quả (`Engine đọc:`):**
     * Nền tím đen `rgba(124, 92, 252, 0.08)`, viền `1px solid rgba(124, 92, 252, 0.35)`, bo góc `8px`, padding `12px`.
     * Nhãn nhỏ phía trên: `Engine đọc:` (`11px`, màu tím `#A78BFA`).
     * Nội dung kết quả biến đổi tức thì: `Bản Vi Nơi 2.0 chạy trên GPU, nhanh hơn 5 km/h.`

2. **Card Dưới — `Cách hoạt động` (System Specification Notes):**
   * Tiêu đề: **Cách hoạt động** (`15px`, Bold).
   * Danh sách 4 quy tắc cốt lõi:
     * **Từ dài hơn được ưu tiên:** có cả `"km"` và `"km/h"` thì `"5 km/h"` đọc theo luật `"km/h"`.
     * **Kết quả không bị quét lại:** nên luật không bao giờ tự lặp hay gọi luật khác.
     * **Áp dụng sau bước AI chỉnh văn bản và trước khi gửi engine:** Văn bản gốc trong thư viện vẫn giữ nguyên như bạn gõ.
     * **Chưa áp dụng cho API nhà phát triển (`/v1`) và ứng dụng máy tính** — app có từ điển riêng trên máy.
   * Đoạn hướng dẫn định dạng file Import ở đáy Card:
     > *Tệp .txt hoặc .csv, mỗi dòng "từ = cách đọc" (cũng nhận "→", tab hoặc dấu phẩy). Dòng bắt đầu bằng # bị bỏ qua. Luật nhập vào được xếp lên đầu nên sẽ đè luật cũ trùng từ.*

---

## 3. Đặc Tả Kỹ Thuật Thuật Toán NLP & Từ Điển (Implementation Reference)

### 3.1. Thứ tự Pipeline Tiền Xử Lý Văn Bản (Text Preprocessing Pipeline)
Khi người dùng bấm **Phát ngay** hoặc **Tạo giọng nói** trên Web UI, văn bản đầu vào `rawText` đi qua 4 bước tuần tự sau:

```text
[1. rawText (Lưu nguyên bản vào DB tts_recordings.original_text)]
       │
       ▼
[2. AI Content Moderation (Kiểm duyệt 5 nhóm nội dung cấm)]
       │
       ▼
[3. AI Text Normalization (Chuẩn hóa ngày tháng, số đếm, công thức Toán & Hóa học)]
       │  VD: "ax² + bx + c = 0" -> "a x bình phương cộng b x cộng c bằng không"
       │  VD: "2H2 + O2 → 2H2O"  -> "hai H hai cộng O hai tạo thành hai H hai O"
       ▼
[4. User Pronunciation Dictionary (Áp dụng bảng Từ điển phát âm theo tài khoản)]
       │  VD: "VieNeu" -> "Vi Nơi"
       ▼
[5. TTS Acoustic Engine V4 (Tổng hợp giọng nói)]
```

### 3.2. Thuật toán Thay Thế Từ Điển (Single-Pass Longest-Match Algorithm)
Đội ngũ lập trình cần cài đặt cùng một hàm xử lý (bằng TypeScript/JavaScript để chạy chung trên cả Frontend Preview và Backend Node/Python service) đảm bảo đúng 100% các quy tắc trong khung **Cách hoạt động**:

```typescript
export interface PronunciationRule {
  id: string;
  source: string;          // TỪ NHƯ ĐANG VIẾT
  target: string;          // ENGINE ĐỌC LÀ
  wholeWord: boolean;      // CẢ TỪ
  caseSensitive: boolean;  // PHÂN BIỆT HOA/THƯỜNG
  enabled: boolean;
}

/**
 * Thực thi thay thế từ điển phát âm:
 * 1. Ưu tiên từ dài hơn (Longest Match First).
 * 2. Nếu trùng độ dài, ưu tiên luật đứng trước trong danh sách (luật mới nhập xếp lên đầu).
 * 3. Quét 1 lần duy nhất (Single-Pass), không bao giờ quét lại kết quả đã thay thế.
 */
export function applyPronunciationDictionary(
  inputText: string,
  rules: PronunciationRule[]
): string {
  const activeRules = rules
    .map((r, index) => ({ ...r, source: r.source.trim(), originalIndex: index }))
    .filter((r) => r.enabled && r.source.length > 0);

  if (!inputText || activeRules.length === 0) return inputText;

  // Sắp xếp theo độ dài giảm dần; nếu bằng nhau thì giữ thứ tự xuất hiện trên bảng
  activeRules.sort((a, b) => {
    if (b.source.length !== a.source.length) {
      return b.source.length - a.source.length;
    }
    return a.originalIndex - b.originalIndex;
  });

  const isWordChar = (ch: string | undefined): boolean => {
    if (!ch) return false;
    return /[\p{L}\p{N}_]/u.test(ch);
  };

  let result = "";
  let i = 0;
  const n = inputText.length;

  while (i < n) {
    let matchedRule: (typeof activeRules)[0] | null = null;

    for (const rule of activeRules) {
      const len = rule.source.length;
      if (i + len > n) continue;

      const candidate = inputText.slice(i, i + len);
      const isTextMatch = rule.caseSensitive
        ? candidate === rule.source
        : candidate.toLowerCase() === rule.source.toLowerCase();

      if (!isTextMatch) continue;

      if (rule.wholeWord) {
        const prevChar = i > 0 ? inputText[i - 1] : undefined;
        const nextChar = i + len < n ? inputText[i + len] : undefined;
        const leftBoundaryOk = !isWordChar(prevChar);
        const rightBoundaryOk = !isWordChar(nextChar);
        if (!leftBoundaryOk || !rightBoundaryOk) continue;
      }

      matchedRule = rule;
      break; // Đã khớp luật dài nhất và ưu tiên cao nhất tại vị trí i
    }

    if (matchedRule) {
      // Nối trực tiếp target vào result và nhảy con trỏ i qua hết cụm từ gốc (không quét lại target)
      result += matchedRule.target;
      i += matchedRule.source.length;
    } else {
      result += inputText[i];
      i += 1;
    }
  }

  return result;
}
```

### 3.3. Thuật toán Phân Tích Tệp Nhập (`.txt` / `.csv` Import Parser)
* Khi người dùng chọn file qua nút `[📄 Nhập từ tệp]`:
  1. Đọc nội dung file theo bảng mã `UTF-8`.
  2. Tách theo dòng (`/?
/`).
  3. Bỏ qua các dòng trống hoặc dòng có ký tự đầu tiên (sau khi `trim()`) là `#`.
  4. Tách mỗi dòng theo một trong các ký hiệu phân cách: ` = `, `=`, ` → `, `→`, `	`, hoặc `,` (tách tại vị trí xuất hiện đầu tiên của dấu phân cách).
  5. Các luật mới được đưa lên **đầu mảng hiện tại**; nếu trùng `source` với luật cũ, luật mới ở đầu sẽ được ưu tiên (hoặc ghi đè trực tiếp luật cũ trùng từ) và đảm bảo tổng số luật không vượt quá `2.000`.
