# Hướng dẫn sử dụng

Cách dùng trang quản trị web VieNeu và API giọng nói với API key, từ điển và bộ tiền xử lý truyện. Mọi route, giới hạn và thiết lập được liệt kê trong tài liệu tham chiếu **Chức năng trang quản trị web** (Help → Web admin functions, file `docs/web-admin-functions.vi.md`). Bản tiếng Anh: `docs/user-guide.md`.

> **Trước khi nâng cấp một server đang chạy.** Khi trang quản trị bật (mặc định), API giọng nói trả `401` cho mọi lệnh gọi không có key hợp lệ, kể cả khi chưa có key nào. Hãy tạo key trước, hoặc đặt `VIENEU_ADMIN=0` để giữ API không cần khoá như cũ. CSDL mới cũng cần `VIENEU_ADMIN_USER` và `VIENEU_ADMIN_PASSWORD` ở lần khởi động đầu, nếu không server dừng kèm thông báo lỗi.

## 1. Khởi động server và đăng nhập

### Lần khởi động đầu

```bash
# Chạy từ repo
VIENEU_ADMIN_USER=admin VIENEU_ADMIN_PASSWORD='doi-mat-khau-nay' uv run python -m apps.openai_speech
# hoặc dùng Makefile
VIENEU_ADMIN_USER=admin VIENEU_ADMIN_PASSWORD='doi-mat-khau-nay' make api
```

Docker: ghi hai biến vào `docker/.env` (hoặc export trong shell), rồi chạy một profile:

```bash
docker compose -f docker/docker-compose.yml --profile api-gpu up   # hoặc --profile api-cpu
```

CSDL nằm trong volume `vieneu_data`, nên hai biến chỉ cần ở lần đầu với volume mới. Khi đã có admin, chúng bị bỏ qua, và đổi giá trị của chúng không đổi mật khẩu.

Thay cho biến môi trường, có thể tạo admin bằng CLI trước lần khởi động đầu:

```bash
uv run python -m vieneu_admin create-admin admin      # hỏi mật khẩu hai lần
```

### Đăng nhập

1. Mở `http://<host>:8000/admin` (`http://<host>:8000/` tự chuyển tới đó).
2. Nhập username và mật khẩu. Username dài 3–40 ký tự (chữ, số, `.`, `_`, `-`); mật khẩu ít nhất 8 ký tự.
3. Sai mật khẩu 5 lần cho cùng username từ cùng địa chỉ trong 5 phút thì username đó bị khoá vài phút trên địa chỉ đó.

Dashboard cho biết bạn có bao nhiêu key đang hoạt động, từ điển nào đang bật, và engine giọng nói đã nạp chưa.

### Đổi mật khẩu

**Change password** (menu trên cùng) → nhập mật khẩu hiện tại và mật khẩu mới hai lần. Các phiên khác của bạn (trình duyệt khác, thiết bị khác) bị đăng xuất; phiên hiện tại vẫn giữ.

## 2. API key

### Tạo key

1. **API keys** → gõ tên cho biết key dùng ở đâu (ví dụ `laptop` hoặc `bot-prod`) → **Create key**.
2. Key đầy đủ (`vn_…`) chỉ hiện **một lần**. Chép ngay; sau đó danh sách chỉ hiện vài ký tự đầu. Nếu làm mất, hãy thu hồi và tạo key mới.

### Thu hồi key

**API keys** → **Revoke** ở dòng của key. Lệnh gọi dùng key đó nhận `401` ngay. Bạn chỉ thu hồi được key của mình; admin thấy và thu hồi được key của mọi người.

## 3. Gọi API giọng nói

Các ví dụ dùng key trong biến shell `VIENEU_KEY`.

### curl

```bash
export VIENEU_KEY=vn_key_cua_ban

# Văn bản thường, ra file WAV
curl -s http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer $VIENEU_KEY" -H "Content-Type: application/json" \
  -d '{"model": "vieneu-v3-turbo", "voice": "Mai Anh", "input": "Xin chào các bạn.", "response_format": "wav"}' \
  -o hello.wav

# Khoảng nghỉ tường minh: 0.5 s trước, 0.8 s ở giữa, 1 s sau
curl -s http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer $VIENEU_KEY" -H "Content-Type: application/json" \
  -d '{"input": "[0.5] Một, hai. [0.8] Ba! [1]", "response_format": "wav"}' -o pauses.wav

# Văn bản truyện qua bộ tiền xử lý và các từ điển đang bật
curl -s -D - http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer $VIENEU_KEY" -H "Content-Type: application/json" \
  -d '{"input": "Tòa lâu đài Hogwarts hiện ra. \"Chào mừng các con,\" McGonagall nói.", "preprocess": true, "response_format": "wav"}' \
  -o story.wav
```

Lệnh thứ ba in header của response: `X-VieNeu-Preprocess: 1` nghĩa là bộ tiền xử lý đã được áp dụng. Không có header này nghĩa là tiền xử lý lỗi và văn bản gốc đã được đọc (log server ghi lý do).

### OpenAI SDK (Python)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="vn_key_cua_ban")

# Request thường
with client.audio.speech.with_streaming_response.create(
    model="vieneu-v3-turbo", voice="Mai Anh", input="Xin chào các bạn.", response_format="wav",
) as r:
    r.stream_to_file("hello.wav")

# Văn bản truyện qua bộ tiền xử lý: gửi trường bổ sung bằng extra_body
with client.audio.speech.with_streaming_response.create(
    model="vieneu-v3-turbo", voice="Mai Anh", response_format="wav",
    input="Tòa lâu đài Hogwarts hiện ra. \"Chào mừng các con,\" McGonagall nói.",
    extra_body={"preprocess": True},
) as r:
    r.stream_to_file("story.wav")
```

### Kết quả mong đợi

- **Thẻ nghỉ** `[x.xx]` dùng được trong mọi request, có hay không có `preprocess`: 0 tới 5 giây, giá trị lớn hơn thành 5 s, không bao giờ bị đọc thành lời. Khoảng nghỉ ở ngay đầu hoặc cuối văn bản là chính xác. Khoảng nghỉ giữa hai câu là **mức tối thiểu**: nếu giọng đã có sẵn khoảng lặng tự nhiên ở đó, khoảng nghỉ có thể dài hơn thẻ một chút.
- **`preprocess: true`** thêm khoảng nghỉ theo quy tắc truyện, áp dụng mọi từ điển đang bật, và đọc cả văn bản bằng một giọng. Giọng theo người nói và tốc độ theo chunk bị bỏ qua ở API (header `X-VieNeu-Ignored: speed`); dùng Script Lab cho các tính năng đó.
- **Không có `preprocess`**, từ điển không được áp dụng và văn bản tới engine nguyên vẹn.

## 4. Script Lab

Script Lab biến một câu chuyện thành kịch bản TTS và cho bạn nghe thử một đoạn ngắn.

1. **Script Lab** → dán một chương hoặc một đoạn (tối đa 50 000 ký tự) → **Analyse**.
2. Đọc kết quả:
   - **Script**: mỗi lượt lời một dòng, `Người nói: văn bản [0.35] …`, có chú thích `// Phân cảnh` ở chỗ ngắt cảnh. Kiểm tra mỗi dòng có đúng người nói và khoảng nghỉ có nằm đúng chỗ bạn mong đợi không.
   - **JSON**: mỗi chunk một object (`speaker`, `role_type`, `text`, `speed`, `pause_before_sec`, `pause_after_sec`, `voice_preset`, `temperature`). **Download JSON** để lưu.
   - **Tagged text**: văn bản một giọng mà API sẽ đọc khi `preprocess: true`.
3. Gán giọng: trong **Render preview**, chọn giọng cho từng người nói (`default` dùng giọng mặc định của engine).
4. Chọn **WAV** (mặc định) hoặc **FLAC** rồi bấm **Render audio**. Chỉ render được văn bản tối đa **3 000 ký tự**; văn bản dài hơn thì trang sẽ nhắc dùng CLI.
5. Nghe trong trình phát, hoặc bấm **Download WAV/FLAC**.

Lưu ý:

- Mỗi phiên chỉ chạy một lần render cùng lúc. Render dùng chung engine với người dùng API, nên khi server bận sẽ báo "server busy" (`429`); thử lại sau ít phút.
- Tốc độ chunk được áp dụng bằng resampling, nên chunk chậm hơn cũng nghe trầm hơn một chút, chunk nhanh hơn nghe cao hơn một chút.
- Người nói được lấy từ câu dẫn thoại như `… Hagrid nói.` Dòng không có câu dẫn mang nhãn "Nhân vật". Quy tắc mặc định không chứa gợi ý vai riêng cho truyện nào; ví dụ đoạn mẫu Hogwarts cần các gợi ý trong `tests/fixtures/preprocess/dracaena_cast_rules.yaml` (qua `--rules` của CLI) mới gán được nhãn "Nón Phân Loại" và "McGonagall".
- Lần phân tích và audio gần nhất chỉ nằm trong bộ nhớ server; hãy tải về những gì cần giữ.

### Cả chương: dùng CLI

```bash
# Xuất từ điển từ CSDL, rồi tiền xử lý một thư mục chương
uv run python -m vieneu_admin export-dicts dicts/
uv run vieneu-preprocess chapters/ --dict dicts/*.json --out out/
# Tạo luôn audio bằng model cục bộ (mỗi chương một WAV), kèm gợi ý vai nếu cần
uv run vieneu-preprocess chapters/chapter-01.md --dict dicts/*.json --rules cast.yaml --render --voice "Mai Anh"
```

## 5. Việc của admin

### Người dùng

**Users** (chỉ admin):

- **Create user**: username, mật khẩu, vai trò (`user` hoặc `admin`). Gửi mật khẩu cho người dùng qua kênh an toàn; họ có thể đổi sau khi đăng nhập.
- **Role**: nâng hoặc hạ quyền. **Disable**: người dùng bị đăng xuất và key của họ ngừng hoạt động; **Enable** khôi phục cả hai. **Reset password**: đặt mật khẩu mới và đăng xuất người dùng. **Delete**: xoá tài khoản cùng các key.
- Bạn không thể hạ quyền, tắt, đặt lại mật khẩu hay xoá chính tài khoản của mình ở đây, và admin đang hoạt động cuối cùng luôn được bảo vệ. Hãy nâng quyền một admin thứ hai trước.

Quên mật khẩu của admin duy nhất? Trên server: `uv run python -m vieneu_admin reset-password <admin>`.

### Từ điển

**Dictionaries** liệt kê mọi từ điển; mỗi từ điển đang bật áp dụng cho mọi request có tiền xử lý. Mọi người đều xem và xuất được; chỉ admin sửa được.

- **New dictionary**: tên, loại (`name` cho tên riêng, `term` cho thuật ngữ và từ viết tắt, `english` cho từ đọc tiếng Anh), mô tả.
- **Bật/tắt**: nút chuyển trên danh sách. Từ điển bị tắt bị bỏ qua ở mọi nơi.
- **Mục**: mở một từ điển → **Add** một term cùng cách thay thế (ví dụ `Hogwarts` → `Hốc-goát`), chế độ `phonetic` (thay thế) hoặc `en` (giữ nguyên từ, đọc tiếng Anh), và **Case-sensitive** cho từ viết tắt. **Edit** và **Delete** làm ngay tại dòng. Ô tìm kiếm tìm term, 50 mục mỗi trang.
- **Rename / describe** và **Delete** nằm trên trang của từ điển.

### Nhập và xuất

- **Export JSON** trên một từ điển tải về file `vieneu-dictionary/1`. Hãy giữ các file này trong hệ quản lý phiên bản hoặc làm bản sao lưu.
- **Import JSON** (tối đa 5 MB):
  - **New**: tạo từ điển (có thể đặt tên khác).
  - **Merge into**: thêm term mới và ghi đè term đã có trong từ điển được chọn.
  - **Replace entries of**: xoá mọi mục của từ điển được chọn rồi nạp file.
- File hỏng bị từ chối toàn bộ, kèm vị trí lỗi, ví dụ `Invalid JSON at line 7, column 12`.

### Thử một câu

**Preview** ở cuối trang **Dictionaries**: gõ một câu (tối đa 2 000 ký tự) và chọn một từ điển hoặc "all enabled" ở mục **Using**. Kết quả là văn bản có thẻ mà engine sẽ nhận, nên bạn thấy cả phần thay thế lẫn khoảng nghỉ. Muốn nghe, dán cùng câu đó vào Script Lab và render.

### Sửa cách phát âm của từ điển mẫu

Server có sẵn bảy từ điển mẫu (từ viết tắt, kinh doanh và tài chính, tiếng Anh thông dụng, hai bộ tên kỳ huyễn, thuật ngữ công nghệ, y tế), đều được bật trên CSDL mới. Cách viết trong đó là phỏng đoán tốt nhất và cần nghe kiểm tra.

1. Render một câu có từ đó trong Script Lab và nghe.
2. Nếu nghe sai, mở từ điển chứa term (dùng ô tìm kiếm), bấm **Edit** và sửa phần thay thế. Viết theo cách người Việt đọc, các âm tiết nối bằng `-` (ví dụ `Sờ-li-thơ-rin`). Với từ tiếng Anh mà engine đã đọc tốt, hãy đổi chế độ sang `en`.
3. Preview lại, render lại, nghe lại.
4. **Export JSON** để giữ file đã sửa. Thay đổi nằm trong CSDL; các file mẫu chỉ được đọc khi CSDL không có từ điển nào.

## 6. Xử lý sự cố

| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| `401 invalid api key` từ `/v1/*` | Thiếu header `Authorization: Bearer …`, gõ sai, key đã bị thu hồi, hoặc chủ key bị tắt. Khi trang quản trị bật, luôn cần key: tạo ở **API keys**, hoặc dùng `VIENEU_API_KEY`. Muốn quay lại API không cần khoá, khởi động với `VIENEU_ADMIN=0`. |
| `401` ngay sau khi nâng cấp | Đúng như dự kiến: xem ghi chú ở đầu trang. |
| Server dừng khi khởi động với thông báo "has no active admin account" | CSDL mới chưa có admin. Đặt `VIENEU_ADMIN_USER` và `VIENEU_ADMIN_PASSWORD` cho lần đầu, chạy `python -m vieneu_admin create-admin <user>`, hoặc đặt `VIENEU_ADMIN=0`. Trong Docker, điều này xảy ra với mỗi volume `vieneu_data` mới. |
| `429` ở API hoặc "server busy" trong Script Lab | Mọi stream slot đều bận và hàng đợi đầy hoặc quá thời gian chờ. Thử lại sau khoảng `Retry-After`, hoặc tăng `VIENEU_MAX_STREAMS` / `VIENEU_QUEUE` nếu phần cứng cho phép. |
| "A render is already running." | Lần render Script Lab trước của bạn chưa xong; hãy chờ. |
| Trang đăng nhập báo "Too many failed attempts" | Sai 5 lần cho username này từ địa chỉ của bạn trong 5 phút. Chờ, hoặc nhờ admin đặt lại mật khẩu. Nếu mọi người dùng cùng bị khoá sau reverse proxy, đặt `FORWARDED_ALLOW_IPS` bằng địa chỉ của proxy. |
| "Engine not loaded." trong Script Lab | Model không sẵn sàng (đang nạp, nạp lỗi, hoặc đã sập). Phân tích vẫn chạy; kiểm tra `GET /health` và log server, khởi động lại server nếu `/health` trả `503`. |
| Help báo "This document is not available on this server" | Thiếu thư mục tài liệu. Đặt `VIENEU_DOCS_DIR` tới thư mục chứa `user-guide.md` và `web-admin-functions.md` (image Docker chép chúng vào `/workspace/docs`). |
| Ngoặc vuông trong văn bản không tạo khoảng nghỉ | Chỉ số mới là thẻ nghỉ (`[0.5]`, `[2s]`, tối đa hai chữ số trước dấu chấm). Chữ trong ngoặc như `[cười]` là emotion cue, xử lý như trước. Thẻ nằm trong `<en>…</en>` vẫn là chữ. |
| Một cái tên bị đọc sai khi dùng `preprocess` | Tìm term trong từ điển (mục 5) và sửa. Không có `preprocess` thì từ điển không được dùng. |
| Bị đăng xuất bất ngờ | Phiên hết hạn sau 12 giờ không hoạt động; đổi mật khẩu, bị đặt lại mật khẩu hoặc bị tắt tài khoản cũng đăng xuất bạn. |
