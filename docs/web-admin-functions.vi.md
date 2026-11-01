# Chức năng trang quản trị web

Tài liệu tham chiếu cho người vận hành và người bảo trì trang quản trị VieNeu, từ điển phát âm và bộ tiền xử lý truyện. Muốn làm theo từng bước, đọc **Hướng dẫn sử dụng** (Help → User guide, file `docs/user-guide.vi.md`). Bản tiếng Anh: `docs/web-admin-functions.md`.

> **Thay đổi không tương thích với cách chạy API không cần khoá.** Khi trang quản trị bật (mặc định, `VIENEU_ADMIN=1`), **mọi** lệnh gọi `/v1/*` đều cần API key, kể cả khi chưa có key nào: các lệnh gọi đầu tiên sau khi nâng cấp nhận `401` cho tới khi bạn tạo key ở `/admin/keys` hoặc đặt `VIENEU_API_KEY`. `VIENEU_ADMIN=0` khôi phục đúng hành vi cũ (API mở nếu không đặt `VIENEU_API_KEY`).
>
> Với **CSDL mới** chưa có tài khoản admin, server **từ chối khởi động** nếu không đặt `VIENEU_ADMIN_USER` và `VIENEU_ADMIN_PASSWORD` (hoặc chưa chạy `python -m vieneu_admin create-admin <user>` trước). Điều này ảnh hưởng tới Docker: các service `api-gpu`, `api-cpu` và `api` (prod) giữ CSDL trong volume bền vững `vieneu_data`, nên lần chạy đầu với volume mới cần hai biến đó. Sau reverse proxy, đặt `FORWARDED_ALLOW_IPS` bằng địa chỉ của proxy, nếu không cơ chế khoá đăng nhập sẽ coi mọi client là proxy.

## 1. Kiến trúc

Một tiến trình (`apps/openai_speech.py`, một worker uvicorn) phục vụ cả API giọng nói tương thích OpenAI lẫn trang quản trị. Gói `src/vieneu_admin/` không bao giờ import engine; API trao cho nó một engine provider để dùng trong Script Lab.

```text
 API client ──Bearer key──▶ /v1/audio/speech ──▶ kiểm tra key ─┐
                                 │                              │
                                 │ preprocess=true              ▼
                                 ▼                     SQLite (vieneu_data/admin.sqlite3)
                     vieneu_preprocess.preprocess ◀── các từ điển đang bật (lexicon)
                                 │ text có thẻ [x.xx]             ▲
                                 ▼                                │
                     VieNeuV3Turbo.infer_stream          users, keys, sessions,
                                                         dictionaries
 Trình duyệt ──cookie phiên──▶ /admin (Jinja2 + HTMX) ────────────┘
                                 │ Script Lab render
                                 ▼
                     vieneu_preprocess.render (giọng, tốc độ, khoảng nghỉ theo chunk)
                                 │ một stream slot, qua infer_stream
                                 ▼
                              engine
 /admin/help ──▶ docs/web-admin-functions[.vi].md, docs/user-guide[.vi].md
```

Thứ tự khởi động: mở CSDL, chạy migration, nạp từ điển mẫu nếu CSDL chưa có từ điển nào, bảo đảm có một admin đang hoạt động (nếu không thì dừng), gắn `/admin`, rồi mới nạp model. Vì vậy lỗi cấu hình làm server dừng trước khi tốn thời gian nạp model.

## 2. Các trang và route

Mọi route quản trị nằm dưới `/admin`. "User" là bất kỳ tài khoản đang hoạt động nào đã đăng nhập; "Admin" là vai trò `admin`. Mọi `POST` cần CSRF token hợp lệ (trường form `csrf_token` hoặc header `X-CSRF-Token`), nếu không trả `403`. Khi chưa có phiên, trang chuyển hướng tới `/admin/login` (`303`); request HTMX nhận `401` kèm header `HX-Redirect`. Người không phải admin vào route chỉ dành cho admin nhận `403`.

### Tài khoản

| Method và đường dẫn | Ai | Chức năng |
|---|---|---|
| `GET /admin/login` | mọi người | Form đăng nhập (đã đăng nhập thì chuyển tới dashboard). |
| `POST /admin/login` | mọi người | Kiểm tra thông tin; sai 5 lần cho cùng cặp (username, IP client) trong 5 phút thì cặp đó bị khoá tới hết cửa sổ thời gian (`429`). |
| `POST /admin/logout` | User | Kết thúc phiên. |
| `GET /admin/` | User | Dashboard: số key đang hoạt động của bạn, các từ điển đang bật, trạng thái engine. |
| `GET /admin/account/password` | User | Form đổi mật khẩu. |
| `POST /admin/account/password` | User | Cần mật khẩu hiện tại; đăng xuất mọi phiên khác của tài khoản. |

### API key

| Method và đường dẫn | Ai | Chức năng |
|---|---|---|
| `GET /admin/keys` | User | Các key của bạn. Admin thấy mọi key, kèm chủ sở hữu. |
| `POST /admin/keys` | User | Tạo key có tên 1–80 ký tự. Key đầy đủ (`vn_…`) chỉ hiện **một lần**, trong chính response này. |
| `POST /admin/keys/{id}/revoke` | User | Thu hồi key của chính bạn; admin thu hồi được mọi key. Key của người khác trả `403`. |

### Người dùng (chỉ admin)

| Method và đường dẫn | Chức năng |
|---|---|
| `GET /admin/users` | Danh sách tài khoản. |
| `POST /admin/users` | Tạo tài khoản (vai trò `user` hoặc `admin`). |
| `POST /admin/users/{id}/role` | Đổi vai trò. |
| `POST /admin/users/{id}/active` | Bật hoặc tắt; tắt sẽ kết thúc các phiên của người đó và key của họ ngừng hoạt động. |
| `POST /admin/users/{id}/password` | Đặt lại mật khẩu; kết thúc các phiên của người đó. |
| `POST /admin/users/{id}/delete` | Xoá tài khoản cùng các key. |

Bảo vệ: admin đang hoạt động cuối cùng không bao giờ bị hạ quyền, tắt hay xoá; admin không thể hạ quyền, tắt, đặt lại mật khẩu hay xoá chính tài khoản của mình ở trang này (đổi mật khẩu của mình bằng **Change password**). Username dài 3–40 ký tự gồm chữ, số, `.`, `_` hoặc `-`; mật khẩu dài 8–256 ký tự.

### Từ điển

| Method và đường dẫn | Ai | Chức năng |
|---|---|---|
| `GET /admin/dictionaries` | User | Danh sách kèm loại, trạng thái, số mục. |
| `POST /admin/dictionaries` | Admin | Tạo từ điển rỗng. |
| `POST /admin/dictionaries/import` | Admin | Tải JSON lên (tối đa 5 MB): `new`, `merge` vào, hoặc `replace` các mục của một từ điển có sẵn. |
| `POST /admin/dictionaries/preview` | User | Tiền xử lý một câu (tối đa 2 000 ký tự) với một từ điển hoặc mọi từ điển đang bật, rồi hiện kết quả có thẻ. |
| `GET /admin/dictionaries/{id}` | User | Các mục, 50 mục mỗi trang, có tìm kiếm. |
| `GET /admin/dictionaries/{id}/export` | User | Tải từ điển dưới dạng JSON `vieneu-dictionary/1`. |
| `POST /admin/dictionaries/{id}/rename` | Admin | Đổi tên và sửa mô tả. |
| `POST /admin/dictionaries/{id}/toggle` | Admin | Bật hoặc tắt. |
| `POST /admin/dictionaries/{id}/delete` | Admin | Xoá cùng mọi mục. |
| `POST /admin/dictionaries/{id}/entries` | Admin | Thêm mục. |
| `GET /admin/dictionaries/{id}/entries/{entry_id}` | User | Một dòng mục (dùng cho sửa tại chỗ). |
| `GET /admin/dictionaries/{id}/entries/{entry_id}/edit` | Admin | Form sửa tại chỗ. |
| `POST /admin/dictionaries/{id}/entries/{entry_id}` | Admin | Lưu mục. |
| `POST /admin/dictionaries/{id}/entries/{entry_id}/delete` | Admin | Xoá mục. |

> **Ai xuất được từ điển.** Mọi người dùng đã đăng nhập, không chỉ admin, đều xem được các mục và tải được file JSON xuất. Đừng lưu thông tin bí mật trong từ điển.

### Script Lab

| Method và đường dẫn | Ai | Chức năng |
|---|---|---|
| `GET /admin/script-lab` | User | Trang có ô nhập văn bản và các giới hạn. |
| `POST /admin/script-lab/preprocess` | User | Phân tích tối đa **50 000 ký tự**: kịch bản đã định dạng, người nói, JSON các chunk. |
| `GET /admin/script-lab/download.json` | User | JSON chunk của lần phân tích gần nhất của bạn. |
| `POST /admin/script-lab/render` | User | Tạo audio cho tối đa **3 000 ký tự**, định dạng **WAV** (mặc định) hoặc **FLAC**, mỗi người nói một giọng. Mỗi phiên chỉ một lần render cùng lúc (nếu không trả `429`); không có model thì `503` "Engine not loaded". |
| `GET /admin/script-lab/audio` | User | Nghe (`inline`) hoặc tải (`?download=1`) lần render gần nhất. |

Lần phân tích và lần render gần nhất chỉ được giữ trong bộ nhớ tiến trình theo phiên (trên toàn bộ người dùng: 64 lần phân tích và 8 lần render gần nhất); khởi động lại là mất, nên hãy tải về những gì cần giữ. Văn bản dài hơn thì render bằng CLI `vieneu-preprocess` (mục 8).

### Help và khác

| Method và đường dẫn | Ai | Chức năng |
|---|---|---|
| `GET /admin/help?doc=guide\|functions&lang=en\|vi` | User | Hiển thị tài liệu này hoặc hướng dẫn sử dụng. Chỉ mở được bốn file đó. |
| `GET /admin/static/{name}` | mọi người | Chỉ `htmx.min.js`, `app.js`, `app.css`. |
| `GET /` | mọi người | Chuyển tới `/admin/` khi trang quản trị bật (nếu không thì `404`). |

## 3. Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `VIENEU_ADMIN` | `1` | `0` tắt trang quản trị và khôi phục API không cần khoá (chỉ giá trị `0` mới tắt). |
| `VIENEU_ADMIN_DB` | `vieneu_data/admin.sqlite3` (tính từ thư mục làm việc; Docker `/workspace/vieneu_data/admin.sqlite3`) | Đường dẫn CSDL SQLite. Đã nằm trong `.gitignore`. |
| `VIENEU_ADMIN_USER`, `VIENEU_ADMIN_PASSWORD` | không đặt | Admin đầu tiên khi CSDL chưa có admin đang hoạt động. Bắt buộc với CSDL mới. Bị bỏ qua khi đã có admin đang hoạt động, nên không bao giờ ghi đè mật khẩu đã đổi trong ứng dụng. Mật khẩu không bao giờ được ghi log. |
| `VIENEU_API_KEY` | không đặt | Key dùng chung bổ sung, luôn được chấp nhận dưới dạng `Bearer <key>`. Với `VIENEU_ADMIN=0` và không đặt biến này, API mở. |
| `VIENEU_COOKIE_SECURE` | `0` | `1` đánh dấu cookie phiên và CSRF là `Secure` (đặt khi `/admin` chạy qua HTTPS; request tới bằng `https` tự có cờ này). |
| `VIENEU_DOCS_DIR` | thư mục `docs/` của repo (Docker `/workspace/docs`) | Thư mục trang Help đọc. |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Các proxy được tin header `X-Forwarded-For`, để cơ chế khoá đăng nhập thấy IP thật của client. |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | Địa chỉ lắng nghe. Docker đặt `HOST=0.0.0.0`. |

Các biến của engine (`VIENEU_BACKEND`, `VIENEU_MAX_STREAMS`, `VIENEU_QUEUE`, `VIENEU_QUEUE_TIMEOUT`, …) không đổi; xem `docs/streaming.vi.md`.

Khi khởi động, log ghi rõ chế độ: `admin app at /admin … every /v1/* call requires an API key (N active)`, kèm cảnh báo khi chưa có key nào, hoặc `admin app off (VIENEU_ADMIN=0)` cùng việc `/v1/*` có mở hay không.

## 4. Cơ sở dữ liệu

- File SQLite tại `VIENEU_ADMIN_DB` với các bảng `users`, `api_keys`, `sessions`, `dictionaries`, `dictionary_entries`, `meta`, `schema_version`.
- **Chỉ lưu giá trị băm:** mật khẩu bằng scrypt (`scrypt$N$r$p$salt$hash`), API key và token phiên bằng SHA-256. 8 ký tự đầu của key (`vn_…`) được giữ làm tiền tố hiển thị.
- Phiên kéo dài 12 giờ và tự gia hạn khi đang dùng.
- **Sao lưu trước migration:** trước khi chạy migration schema trên file có sẵn, server checkpoint WAL rồi ghi một bản sao nhất quán bằng online-backup API của SQLite, cạnh CSDL: `admin.sqlite3.bak-v<phiên bản cũ>-<thời điểm>`.
- **Tự sao lưu:** CSDL chạy ở chế độ WAL, nên đừng chỉ chép riêng file `.sqlite3` khi server đang chạy. Dùng `sqlite3 vieneu_data/admin.sqlite3 ".backup backup.sqlite3"`, hoặc dừng server trước. Để từ điển dễ mang đi, hãy xuất thêm chúng (`python -m vieneu_admin export-dicts DIR`).
- **Nạp mẫu:** khi khởi động, nếu CSDL **không có từ điển nào**, mọi file trong `src/vieneu_admin/seed/*.json` được nhập. Vì vậy xoá hết mọi từ điển thì lần khởi động sau từ điển mẫu sẽ quay lại.
- Docker giữ file trong volume `vieneu_data` (`/workspace/vieneu_data`). Xoá volume là xoá người dùng, key và từ điển.

## 5. Thay đổi ở API giọng nói

### Xác thực

| Chế độ | `Authorization` được chấp nhận | Không có key hoặc key sai |
|---|---|---|
| Trang quản trị bật (`VIENEU_ADMIN=1`, mặc định) | `Bearer vn_…` (key đang hoạt động của người dùng đang hoạt động) hoặc `Bearer $VIENEU_API_KEY` | `401`, kể cả khi chưa có key nào |
| Trang quản trị tắt (`VIENEU_ADMIN=0`), có `VIENEU_API_KEY` | `Bearer $VIENEU_API_KEY`, và key trong CSDL nếu file CSDL tồn tại | `401` |
| Trang quản trị tắt, không có `VIENEU_API_KEY` | mọi thứ (mở, như trước) | — |

Key đã thu hồi, hoặc key của người dùng bị tắt, bị từ chối ngay. `GET /health` không bao giờ cần key. Nếu chính việc tra key bị lỗi (lỗi CSDL), API trả `503` kèm `Retry-After: 5`.

### Trường `preprocess`

`POST /v1/audio/speech` nhận `"preprocess": true` (mặc định `false`).

- `false`: `input` tới engine nguyên vẹn từng byte. Từ điển **không** được áp dụng.
- `true`: bộ tiền xử lý truyện chạy trên `input` với mọi từ điển đang bật, engine nhận văn bản một giọng có thẻ nghỉ `[x.xx]`. Response có header `X-VieNeu-Preprocess: 1`. `max_chars` vẫn áp dụng.
- **Fail-open:** nếu tiền xử lý lỗi, server ghi cảnh báo vào log và đọc nguyên `input`; request không lỗi và không có header `X-VieNeu-Preprocess`.
- API stream một giọng. Giọng theo người nói và tốc độ theo chunk của bộ tiền xử lý không được áp dụng ở đây; khi có chunk yêu cầu tốc độ khác 1.0, `X-VieNeu-Ignored` có `speed`. Dùng Script Lab hoặc CLI cho nhiều giọng và tốc độ.

### Thẻ nghỉ dạng số `[x.xx]`

Mọi văn bản gửi tới engine v3 Turbo (API, SDK `infer`/`infer_stream`/batch) đều có thể chứa thẻ nghỉ:

- Cú pháp: một hoặc hai chữ số phần nguyên, phần thập phân tuỳ chọn tới ba chữ số, `s` tuỳ chọn: `[0.5]`, `[1.25]`, `[2s]`, `[ 0.35 ]`.
- Phạm vi: **0 tới 5 giây**. Giá trị lớn hơn bị kẹp về 5 s. Các thẻ liền nhau chỉ cách bởi khoảng trắng cộng lại thành một khoảng nghỉ (`[0.3] [0.5]` → 0.8 s, vẫn kẹp ở 5 s).
- Thẻ không bao giờ được đọc thành lời. Chữ trong ngoặc vuông khác (`[abc]`, `[cười]`) không phải thẻ nghỉ và giữ ý nghĩa cũ (emotion cue). Thẻ nằm trong `<en>…</en>` vẫn là chữ.
- **Thẻ ở đầu và cuối là chính xác:** chèn đúng bấy nhiêu im lặng trước audio đầu tiên hoặc sau audio cuối cùng. Văn bản chỉ gồm thẻ trả về im lặng thuần với độ dài đó.
- **Thẻ giữa các chunk là mức tối thiểu:** bộ nối audio đo khoảng im lặng tự nhiên sẵn có ở cuối chunk trước và đầu chunk sau, rồi chỉ chèn thêm cho đủ độ dài yêu cầu. Giọng có đuôi im lặng tự nhiên dài vì thế có thể nghỉ lâu hơn giá trị thẻ.
- Văn bản không có thẻ cho ra đúng các chunk và khoảng nghỉ như trước.
- Các đường xử lý không mang được im lặng (`normalize_to_chunks_v3` của Gradio, bộ chia chunk v1/v2 cũ) xoá thẻ và coi vị trí đó là ranh giới câu.

## 6. Từ điển

Từ điển là toàn cục: mọi từ điển **đang bật** áp dụng cho mọi request có tiền xử lý (API với `preprocess=true`, Script Lab, preview). Request API thường không bao giờ dùng chúng.

### Định dạng JSON (`vieneu-dictionary/1`)

```json
{
  "format": "vieneu-dictionary/1",
  "name": "Kỳ huyễn: Hogwarts",
  "kind": "name",
  "enabled": true,
  "description": "Tên riêng thế giới Harry Potter.",
  "entries": [
    {"term": "Hogwarts", "replacement": "Hốc-goát", "mode": "phonetic", "case_sensitive": false, "note": ""},
    {"term": "Scotland", "replacement": "", "mode": "en", "case_sensitive": false, "note": "đọc tiếng Anh"},
    {"term": "VTV", "replacement": "vê-tê-vê", "mode": "phonetic", "case_sensitive": true, "note": ""}
  ]
}
```

| Trường | Quy tắc |
|---|---|
| `format` | Phải là `vieneu-dictionary/1`. |
| `name` | 1–80 ký tự, duy nhất (không phân biệt hoa thường) trong CSDL. |
| `kind` | `english`, `term` hoặc `name`. Khi hai từ điển đang bật cùng định nghĩa một term, `name` thắng `term`, `term` thắng `english`; hoà thì theo thứ tự chữ cái của tên từ điển. |
| `enabled` | Boolean, mặc định `true`. |
| `description` | Chuỗi, tuỳ chọn. |
| `entries` | Danh sách, tối đa 20 000. |
| `entries[].term` | 1–80 ký tự, không trùng trong một file (không phân biệt hoa thường trừ khi `case_sensitive`). |
| `entries[].mode` | `phonetic` (mặc định): thay bằng `replacement`. `en`: giữ term và bọc trong `<en>…</en>` để đọc tiếng Anh. |
| `entries[].replacement` | Tối đa 200 ký tự; bắt buộc với `phonetic`. Không được chứa `[`, `]`, `<|`, `|>` hay bất kỳ thẻ `<…>` nào. |
| `entries[].case_sensitive` | Boolean, mặc định `false`. Dùng `true` cho từ viết tắt. |
| `entries[].note` | Chuỗi, tuỳ chọn. |

JSON hỏng được báo kèm vị trí, ví dụ `Invalid JSON at line 7, column 12: Expecting ',' delimiter`. Lỗi trường nêu đường dẫn, ví dụ `entries[3].replacement: required for phonetic mode`. Cả file bị từ chối; không có chuyện nhập một phần.

### Cách thay thế hoạt động

- Term được so khớp theo đúng ký tự (ký hiệu như `C++`, `C#`, `.NET` an toàn), term dài nhất trước, có ranh giới từ ở phía kết thúc bằng chữ hoặc số.
- Term viết thường khớp ở đầu câu thì phần thay thế giữ chữ hoa đầu.
- Văn bản trong `<en>…</en>`, `[…]` và `<|…|>` không bao giờ bị đổi.
- Sau lexicon, từ VIẾT HOA còn lại dài từ 4 chữ cái trở lên được đổi thành chữ hoa đầu (`GRYFFINDOR` → `Gryffindor`), để từ hét lên không bị đánh vần.

### Chế độ nhập

| Chế độ | Tác dụng |
|---|---|
| `new` | Tạo từ điển (có thể đặt tên khác). Lỗi nếu tên đã tồn tại. |
| `merge` | Thêm term mới vào từ điển đã chọn và ghi đè term đã có. |
| `replace` | Xoá mọi mục của từ điển đã chọn rồi chèn các mục trong file. |

Tên, loại và trạng thái của từ điển không bị `merge` hay `replace` thay đổi.

### Từ điển mẫu

Có sẵn trong `src/vieneu_admin/seed/`, đều được bật trên CSDL mới:

| File | Tên | Loại |
|---|---|---|
| `abbreviations.json` | Từ viết tắt | term |
| `business-finance.json` | Kinh doanh và tài chính | term |
| `english-common.json` | Tiếng Anh thông dụng | english |
| `fantasy-ash-land.json` | Kỳ huyễn: Vùng Đất Tro Tàn | name |
| `fantasy-hogwarts.json` | Kỳ huyễn: Hogwarts | name |
| `it-terms.json` | Thuật ngữ công nghệ | term |
| `medical.json` | Y tế | term |

Hai từ điển kỳ huyễn cũng được bật, phục vụ demo truyện; hãy tắt chúng nếu tên hư cấu không được phép ảnh hưởng tới văn bản thông thường. Cách viết được soạn cho sea-g2p và cần nghe kiểm tra; sửa cách viết sai ngay trong ứng dụng (mục 5 của Hướng dẫn sử dụng) rồi xuất từ điển để giữ bản sửa.

## 7. Bộ tiền xử lý truyện

Bộ tiền xử lý hiện thực `docs/tts-specs/tts-specs-v1.md` theo năm tầng (`src/vieneu_preprocess/pipeline.py`):

| Tầng | Module | Công việc |
|---|---|---|
| 1 Làm sạch | `sanitizer.py` | Thống nhất dấu câu, bỏ metadata chương, chuẩn hoá ngắt cảnh thành `***`, khôi phục chữ cái đầu bị mất do drop-cap. |
| 2 Phân đoạn | `dialogue_parser.py`, `speaker_attribution.py`, `inner_voice_detector.py` | Tách lời dẫn, hội thoại và giọng nội tâm; xác định người nói từ câu dẫn thoại; bảo vệ trích dẫn lồng trong câu. |
| 3 Ngữ điệu | `prosody_annotator.py`, `prosody_clause_splitter.py` | Khoảng nghỉ trước/sau mỗi chunk theo quy tắc P-01…P-14, thang đếm ngược, chuẩn hoá tiếng hét, thẻ cảm xúc và tốc độ. |
| 4 Lexicon | `lexicon_mapper.py` | Áp dụng từ điển (mục 6). |
| 5 Xuất | `exporters.py` | Kịch bản đã định dạng (spec §5.2), JSON chunk (spec §5.3), văn bản có thẻ cho API. |

Mọi thời lượng, ngưỡng và từ khoá đều nằm trong [`src/vieneu_preprocess/config/pause_rules.yaml`](../src/vieneu_preprocess/config/pause_rules.yaml); mã nguồn không tự giữ con số nào. File YAML riêng truyền qua `--rules` (CLI) được trộn sâu lên trên: mapping được trộn, danh sách bị thay thế.

Bảng quy tắc (giá trị nằm trong YAML, khoá ghi ở cột cuối):

| Mã | Tình huống | Khoá YAML |
|---|---|---|
| P-01 / P-02 / P-03 | Kết câu lời dẫn ngắn / chuẩn / dài | `pauses.p01_…`, `p02_…`, `p03_…`, `thresholds.*` |
| P-04 | Câu ngắn nhấn mạnh ở đầu/cuối đoạn | `pauses.p04_emphatic_short` |
| P-05 | Chuỗi câu ngắn đếm ngược | `countdown.ladder` |
| P-06 | Kết thúc bằng `?`, `!`, `?!` | `pauses.p06_question_exclaim` |
| P-07 | Tiếng hét / điểm danh đứng riêng | `pauses.p07_shout_before`, `p07_shout_after` |
| P-08 / P-09 | Cặp gạch ngang và gạch ngang cuối câu | `pauses.p08_…`, `p09_dash_tail` |
| P-10 | Lấy hơi sau mệnh đề dài | `pauses.p10_long_clause_breath` |
| P-11 / P-12 | Ranh giới hội thoại / giọng nội tâm | `pauses.p11_…`, `p12_inner_voice` |
| P-13 / P-14 | Hết đoạn và hết cảnh | `pauses.p13_paragraph`, `p14_scene` |

**Giữa hai chunk**, khoảng nghỉ thực tế là `max(pause_after của chunk trước, pause_before của chunk sau)`, nên một ranh giới không bao giờ bị nghỉ hai lần.

**Người nói và gợi ý vai.** Người nói lấy từ câu dẫn thoại (`… Hagrid nói.`), đại từ được quy về chủ ngữ có tên gần nhất, dòng không xác định được người nói mang nhãn `speakers.unknown_label` ("Nhân vật"). Gợi ý riêng theo truyện **không** nằm trong quy tắc mặc định: `speakers.aliases` rỗng và `speakers.roll_call_speaker` để trống. Với đoạn mẫu Hogwarts, các gợi ý quy "chiếc nón" thành "Nón Phân Loại" và các dòng điểm danh thành "McGonagall" nằm trong fixture kiểm thử `tests/fixtures/preprocess/dracaena_cast_rules.yaml`; truyền file như vậy qua `--rules` để có cùng người nói. Script Lab và API chỉ dùng quy tắc mặc định.

**Tốc độ.** Tốc độ chunk (ví dụ 0.92 khi đếm ngược) chỉ được Script Lab và CLI áp dụng, bằng cách **lấy mẫu lại (resampling)**: audio chạy nhanh hoặc chậm như băng cassette, nên **cao độ thay đổi theo tốc độ**. Thẻ nghỉ bên trong nhóm được đổi tốc độ đã được nhân trước để giữ đúng độ dài. API streaming bỏ qua tốc độ (mục 5).

**Fail-open.** `vieneu_preprocess.preprocess_safely` không bao giờ ném lỗi vì đầu vào xấu: nó trả về văn bản gốc kèm lỗi, và API ghi lỗi đó vào log.

## 8. Công cụ dòng lệnh

### `vieneu-preprocess`

```bash
uv run vieneu-preprocess INPUT [--out DIR] [--format script|json|both] \
    [--dict FILE ...] [--rules FILE] [--render --voice NAME]
```

- `INPUT`: một file `.md`, `.txt`, `.html` hoặc `.htm`, hoặc một thư mục (mọi file như vậy, theo thứ tự tên, đánh số thành các chương).
- Đầu ra (mặc định `<thư mục input>/preprocessed/`): `<tên>.script.txt` và/hoặc `<tên>.json`; với `--render`, thêm `<tên>.wav` (48 kHz) tạo bằng model cục bộ, có áp dụng giọng và tốc độ theo chunk.
- `--dict`: các file JSON từ điển cần dùng. CLI **không** đọc CSDL quản trị; hãy xuất từ điển trước (`python -m vieneu_admin export-dicts DIR`) rồi truyền vào đây.
- `--rules`: YAML trộn lên quy tắc mặc định, ví dụ file gợi ý vai.
- `--voice`: giọng cho các chunk chưa có giọng.

### `python -m vieneu_admin`

```bash
uv run python -m vieneu_admin [--db PATH] create-admin USER      # hỏi mật khẩu hai lần
uv run python -m vieneu_admin [--db PATH] reset-password USER    # đồng thời kết thúc các phiên của người đó
uv run python -m vieneu_admin [--db PATH] export-dicts DIR       # mọi từ điển -> DIR/<slug>.json
uv run python -m vieneu_admin [--db PATH] import-dict FILE [--mode new|merge|replace]
```

`--db` mặc định lấy `VIENEU_ADMIN_DB`, sau đó `vieneu_data/admin.sqlite3`. `import-dict --mode merge|replace` nhắm vào từ điển cùng tên và tạo mới nếu chưa có. Mã thoát: `0` thành công, `1` lỗi lệnh, `2` không mở được CSDL, `130` bị huỷ. Trong Docker, chạy bên trong container: `docker compose -f docker/docker-compose.yml --profile api-gpu exec api-gpu python -m vieneu_admin create-admin admin`.

## 9. Ghi chú bảo mật

- **Mật khẩu:** scrypt (N=2^14, r=8, p=1, salt 16 byte). Username không tồn tại tốn thời gian kiểm tra như username có thật.
- **Khoá đăng nhập:** trong bộ nhớ, theo cặp (username, IP client): 5 lần sai trong 5 phút. Khởi động lại thì xoá. Khoá theo cặp nghĩa là kẻ tấn công không thể khoá admin thật đang đăng nhập từ địa chỉ khác. IP client là địa chỉ TCP trừ khi request tới từ một địa chỉ trong `FORWARDED_ALLOW_IPS`; sau proxy mà không đặt biến này, mọi người dùng chung IP của proxy và cơ chế khoá không phân biệt được họ.
- **Phiên:** token ngẫu nhiên 256 bit trong cookie `HttpOnly`, `SameSite=Lax` (`vieneu_session`), `Secure` khi `VIENEU_COOKIE_SECURE=1` hoặc HTTPS; chỉ lưu SHA-256. Đăng xuất, đổi mật khẩu, đặt lại mật khẩu và tắt người dùng đều kết thúc phiên.
- **CSRF:** token double-submit có chữ ký trên mọi `POST`, kể cả `/login`. Trang ẩn danh không tạo dòng nào trong CSDL.
- **API key:** `vn_` + 256 bit ngẫu nhiên, chỉ hiện một lần, lưu dạng SHA-256 và tra theo hash với phép so sánh thời gian hằng. `last_used_at` cập nhật tối đa mỗi phút một lần.
- **Header:** `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` và Content-Security-Policy trên các trang quản trị.
- **Escape đầu ra:** Jinja2 autoescape cho mọi trang; Help hiển thị Markdown với HTML thô bị tắt, nên `<script>` trong tài liệu hiện ra dưới dạng chữ.
- **File Help:** `doc` và `lang` được tra trong bảng cố định, không bao giờ ghép thành đường dẫn, nên chỉ đọc được bốn tài liệu.
- **Giới hạn:** body form quản trị lớn hơn khoảng 5,25 MB bị từ chối (`413`); file từ điển tải lên 5 MB; Script Lab phân tích 50 000 ký tự và render 3 000; preview 2 000.
- **Chèn qua từ điển:** phần thay thế không được chứa `[`, `]`, `<|`, `|>` hay thẻ, nên một mục từ điển không thể thêm khoảng nghỉ, token cảm xúc hay thẻ điều khiển engine.
- **Dùng chung engine:** render của Script Lab đi qua cùng stream slot và hàng đợi với API (`429` khi đầy) và qua `infer_stream`, nên không bao giờ chạy CUDA graph song song với các stream API.
- **Mở ra ngoài:** phục vụ `/admin` qua HTTPS khi máy khác truy cập được, và đặt `VIENEU_COOKIE_SECURE=1`.
