# Vận hành Portal

Tài liệu tham khảo cho người vận hành **portal người dùng** của VieNeu
(`src/vieneu_portal/`): dịch vụ FastAPI + PostgreSQL phía sau một SPA
Next.js, cùng một tiến trình worker và speech engine. Để biết cách sử dụng
hằng ngày (đăng ký, Phòng thu, Giọng nói của tôi), đọc **User guide**
(`docs/user-guide.vi.md`). Bản tiếng Anh: `docs/portal-operations.md`.

> Tài liệu này thay thế trang quản trị SQLite cũ từng nằm trong speech engine
> (`src/vieneu_admin/`, mount tại `/admin` trên `apps/openai_speech.py`). Gói
> đó không còn tồn tại. Xem mục **Thay đổi phá vỡ tương thích** ở cuối tài
> liệu nếu bạn đang nâng cấp một server từng dùng nó.

## 1. Kiến trúc

```text
 Trình duyệt ──cookie session──▶ Next.js static export (do chính portal phục vụ)
                                 │
                                 ▼
                       portal (FastAPI, src/vieneu_portal/)
                         │                              │
                         │ SQLAlchemy                   │ presigned URL
                         ▼                              ▼
                     PostgreSQL                   Lưu trữ tương thích S3
              (users, voices, recordings,            (MinIO khi dev)
               dictionaries, audit log)
                         ▲
                         │ nhận các dòng PENDING/ASYNC
                     worker (cùng image, `python -m vieneu_portal worker`)
                         │
                         ▼
                  speech engine (apps/openai_speech.py)
                 một VIENEU_API_KEY, không trang quản trị, không CSDL
```

- **portal**: phục vụ `/api/v1/*` và, khi `VIENEU_PORTAL_WEB_DIST_DIR` chỉ
  tới bản build Next.js (`out/`), cả SPA tại `/`. Một tiến trình xử lý cả
  luồng đồng bộ `POST /tts/generate` (văn bản ngắn) và mọi route khác; không
  bao giờ giữ kết nối CSDL trong lúc gọi engine hoặc storage.
- **worker**: cùng image, chạy `python -m vieneu_portal worker`. Nhận các
  dòng bản ghi `ASYNC`/`PENDING` bằng `SELECT ... FOR UPDATE SKIP LOCKED` —
  chính dòng bản ghi là hàng đợi, không có bảng job riêng.
- **engine**: `apps/openai_speech.py`, chỉ portal và worker gọi được, qua
  `POST /internal/v1/render` và `POST /v1/audio/speech`, bảo vệ bằng một
  `VIENEU_API_KEY` chung (phía portal gọi là `VIENEU_ENGINE_SERVICE_KEY`,
  cùng giá trị). Engine không có CSDL và không có trang quản trị riêng.
- **PostgreSQL**: nguồn sự thật duy nhất cho người dùng, session, giọng đọc,
  bản ghi, từ điển (tài khoản + bộ hệ thống) và nhật ký quản trị.
- **Lưu trữ tương thích S3**: âm thanh đã tạo và ảnh/mẫu giọng đọc. CSDL chỉ
  lưu *key* của object, không lưu URL — mỗi lần đọc đều tạo presigned URL
  mới, có hạn (`PRESIGN_TTL_SEC`).

## 2. Biến môi trường

Mỗi cấu hình là một biến môi trường `VIENEU_PORTAL_*`, nạp một lần khi khởi
động tại [`src/vieneu_portal/config.py`](../src/vieneu_portal/config.py) —
file đó là danh sách chuẩn cho tên, giá trị mặc định và kiểm tra hợp lệ; mục
này chỉ nêu những biến ảnh hưởng nhiều nhất tới việc triển khai:

| Biến | Bắt buộc? | Ghi chú |
|---|---|---|
| `VIENEU_PORTAL_SECRET_KEY` | **Có** | Ký session và CSRF; tối thiểu 32 byte. Không có giá trị mặc định cho production — thiếu là dừng ngay khi khởi động. |
| `VIENEU_PORTAL_DATABASE_URL` | **Có** | `postgresql://user:pass@host:port/db`. |
| `VIENEU_PORTAL_ENGINE_URL`, `VIENEU_PORTAL_ENGINE_SERVICE_KEY` | Có (để chạy TTS) | Địa chỉ engine và khoá hai bên cùng dùng. |
| `VIENEU_PORTAL_S3_*` | Có (để chạy TTS) | Endpoint, bucket, thông tin đăng nhập cho bản ghi/ảnh giọng đọc. |
| `VIENEU_PORTAL_FORWARDED_ALLOW_IPS` | Khi có reverse proxy | Địa chỉ proxy được tin `X-Forwarded-For`. Thiếu biến này, mọi client sau proxy dùng chung IP của proxy khi tính khoá đăng nhập theo IP. Mặc định rỗng = không tin proxy nào. |
| `VIENEU_PORTAL_SIGNUP_ENABLED` | Không (mặc định `true`) | Đặt `false` để tắt đăng ký công khai (ví dụ trong lúc migrate — xem mục 6). |
| `VIENEU_PORTAL_COOKIE_SECURE` | Không (mặc định `true`) | Cookie session/CSRF có cờ `Secure`; chỉ tắt khi chạy dev thuần HTTP. |
| `VIENEU_PORTAL_WEB_DIST_DIR` | Không | Đường dẫn bản build tĩnh Next.js (`portal-web/out/`); khi đặt và thư mục tồn tại, portal tự phục vụ SPA. |

## 3. Khởi động nhanh (Docker Compose)

```bash
cp .env.example .env   # đặt VIENEU_PORTAL_SECRET_KEY, VIENEU_ENGINE_SERVICE_KEY
make portal-up         # postgres, minio, portal, worker (docker/docker-compose.portal.yml)
docker compose -f docker/docker-compose.portal.yml --profile cpu up -d engine
```

Portal nghe tại `http://localhost:8100` (`PORTAL_PORT`); SPA Next.js được
phục vụ tại `/` ngay khi giai đoạn build của image đã tạo ra `out/` (xem
`docker/Dockerfile.portal`). `make portal-down` để dừng toàn bộ stack.

## 4. Tài khoản siêu quản trị đầu tiên

Đăng ký luôn tạo tài khoản `USER` thường — không còn cơ chế "admin đầu tiên"
tự bootstrap khi khởi động như trang quản trị cũ. Tạo siêu quản trị đầu tiên
bằng CLI, bên trong container đang chạy:

```bash
docker compose -f docker/docker-compose.portal.yml exec portal \
  python -m vieneu_portal admin create you@example.com --role superadmin
```

Lệnh hỏi mật khẩu hai lần và không bao giờ ghi log mật khẩu. Từ đó, tài
khoản này quản lý mọi thứ khác qua các trang quản trị (`/admin/users/`) hoặc
trực tiếp qua API `/api/v1/admin/*`.

## 5. Tổng quan khu vực quản trị

Mọi route dưới `/admin/*` yêu cầu quyền `ADMIN` hoặc `SUPERADMIN` (layout
`(admin)` tự chuyển một tài khoản `USER` thường về `/studio/`; API cũng tự
kiểm tra độc lập theo đúng ma trận quyền — việc UI ẩn một nút chỉ là tiện
lợi, không bao giờ là lớp bảo vệ thật).

| Khu vực | Route | Chức năng |
|---|---|---|
| Người dùng | `/admin/users/`, `/admin/users/detail/?id=` | Danh sách/tìm/lọc tài khoản; tạo người dùng (ô chọn quyền chỉ hiện với `SUPERADMIN`); sửa email/tên người dùng; khóa/kích hoạt; đặt lại mật khẩu; xóa (xác nhận bằng cách nhập email); điều chỉnh số dư token (số có dấu + lý do bắt buộc); sửa gói (hạng, hạn mức, giới hạn ngày, ngày hết hạn, đặt lại hôm nay). |
| Khóa API | (trên trang chi tiết người dùng) | Xem và thu hồi khóa API developer của một người dùng. Không bao giờ hiện hash của khóa. |
| Bản ghi | (trên trang chi tiết người dùng) | Tìm/lọc bản ghi của một người dùng, kể cả bản `FAILED` kèm mã lỗi; xóa. |
| Từ điển hệ thống | `/admin/dictionaries/`, `/admin/dictionaries/detail/?id=` | Tạo/đổi tên/bật-tắt/xóa bộ từ điển chung; nhập `.json` (bộ mới, hoặc gộp/thay thế vào bộ có sẵn) hoặc `.txt`; xuất `.json`/`.txt`; sửa quy tắc (từ gốc, cách đọc, `REPLACE` hoặc `ENGLISH_FALLBACK`, nguyên từ, phân biệt hoa/thường, ghi chú) có kiểm tra xung đột bằng etag `If-Match` và xem thử ngay trên trình duyệt. |
| Giọng đọc | `/admin/voices/` | Sửa danh mục (tên, giới tính, vùng miền, thẻ, nhãn ngôn ngữ, thứ tự, trạng thái hoạt động); tải lên/xóa ảnh đại diện; tải lên mẫu hoặc tạo mẫu qua engine. |
| Nhật ký quản trị | `/admin/audit-log/` | Chỉ xem. Lọc theo người thực hiện, hành động, loại/ID đối tượng, khoảng ngày; xem chi tiết JSON trước/sau (hiển thị dạng văn bản, không bao giờ là HTML). |

### Quyền và các rào chắn

- `USER`: không có quyền quản trị.
- `ADMIN`: chỉ quản lý tài khoản `USER` — không xem/sửa/khóa/xóa được tài
  khoản `ADMIN`/`SUPERADMIN`, và `POST /admin/users` với `role` khác `USER`
  từ một tài khoản `ADMIN` sẽ nhận `403 FORBIDDEN_ROLE`.
- `SUPERADMIN`: quản lý tất cả; chỉ quyền này mới đổi được quyền hoặc tạo
  được tài khoản `ADMIN`/`SUPERADMIN`.
- Siêu quản trị viên đang hoạt động cuối cùng không bao giờ bị giáng quyền
  hoặc khóa (`409 LAST_SUPERADMIN`), và không ai tự khóa/đặt lại mật
  khẩu/đổi quyền/xóa được chính tài khoản mình từ trang quản trị
  (`409 SELF_MODIFICATION`) — dùng chức năng tự đổi mật khẩu thông thường
  thay thế.
- Mỗi thay đổi ghi đúng một dòng vào nhật ký quản trị, trong cùng transaction
  với thay đổi đó; xem bản ghi của người dùng khác ghi một dòng
  `user.recordings_view` (một dòng mỗi lần xem danh sách, không phải mỗi
  presigned URL). Không route nào trả về mật khẩu hay hash khóa.

## 6. Mỗi người chỉ tạo một giọng nói cùng lúc

Trước khi bắt đầu tạo giọng, portal giữ một "lease" theo người dùng
(`users.synthesis_lock_until`); một lệnh `POST /tts/generate` hoặc
`POST /tts/stream` thứ hai từ cùng tài khoản trong khi lệnh trước chưa xong
sẽ nhận `409 SYNTHESIS_IN_PROGRESS`. Hạn mức token/ký tự được đảm bảo bằng
đúng một câu `UPDATE` có điều kiện, nguyên tử, tại thời điểm trừ — không phải
ở bước kiểm tra trước đó — nên một điều chỉnh token của admin và một lần tạo
giọng của chính người dùng không thể cùng lúc khiến số dư âm.

## 7. Thứ tự ưu tiên từ điển

Ba lớp quy tắc gộp thành một bộ cho mỗi lần tạo giọng: quy tắc riêng của tài
khoản thắng bộ từ điển hệ thống, bộ hệ thống thắng danh sách tiếng Anh dự
phòng (bằng độ dài khớp thì lớp sớm hơn thắng). Các mục `ENGLISH_FALLBACK`
trong bộ hệ thống bọc từ khớp trong `<en>...</en>` thay vì thay thế văn bản,
để engine đọc đúng theo cách đọc tiếng Anh. Lệnh
`python -m vieneu_portal text preview "<văn bản>" [--user EMAIL]` in ra đúng
văn bản engine sẽ nhận, có hoặc không kèm quy tắc riêng của tài khoản — đây
là chức năng thay thế trực tiếp cho Script Lab xem thử của trang quản trị cũ.

## 8. Quy trình di chuyển dữ liệu từ SQLite

Nếu bạn đang nâng cấp một server từng chạy trang quản trị SQLite cũ
(`src/vieneu_admin/`), người dùng, khóa API và từ điển của nó có thể được
chuyển vào CSDL Postgres của portal. Công cụ di chuyển là idempotent theo
nguồn gốc (`legacy_source_id`), nên chạy lại vẫn an toàn, và sẽ dừng ngay khi
có xung đột khóa tự nhiên (ví dụ username đã có người khác dùng) thay vì tự
đoán.

1. Giữ `VIENEU_PORTAL_SIGNUP_ENABLED=false` cho tới khi xác nhận di chuyển
   xong, để không có tài khoản mới nào trùng với tài khoản chưa được chuyển.
2. Luôn sao lưu trước: lệnh tự tạo bản sao online của SQLite nguồn và một
   `pg_dump` của đích trước khi chạm vào bất cứ thứ gì
   (`VIENEU_PORTAL_BACKUP_DIR`, mặc định `vieneu_data/portal_backups`).
3. Chạy thử với `--dry-run`, đọc báo cáo JSON (số lượng, xung đột,
   `lost_rows`), sửa mọi cảnh báo, rồi chạy lại đúng lệnh đó với `--apply`:

   ```bash
   docker compose -f docker/docker-compose.portal.yml exec portal \
     python -m vieneu_portal migrate-sqlite --sqlite /path/to/admin.sqlite3 --dry-run
   docker compose -f docker/docker-compose.portal.yml exec portal \
     python -m vieneu_portal migrate-sqlite --sqlite /path/to/admin.sqlite3 --apply
   ```

4. Tài khoản đã chuyển đăng nhập bằng `<username>@migrated.invalid` — báo
   cho mỗi người username cũ của họ để biết dùng gì, và nhắc họ đổi email
   sau khi đăng nhập vào portal.
5. Chỉ chạy `python -m vieneu_portal system-dict seed` **khi đích không có
   CSDL SQLite nào để di chuyển** — seed sau khi đã di chuyển sẽ tạo ra bộ
   từ điển trùng tên không có nguồn gốc, và lệnh này tự chối chạy nếu đã có
   bất kỳ bộ từ điển hệ thống nào.
6. Bật lại `VIENEU_PORTAL_SIGNUP_ENABLED=true` khi số liệu trong báo cáo đã
   khớp với kỳ vọng.

Một lần chạy thử đúng quy trình này (trên CSDL mẫu, vì môi trường này không
có `vieneu_data/admin.sqlite3` thật) được lưu tại
`plans/reports/261103-migration-rehearsal-dry-run.json`.

## 9. Sao lưu và khôi phục

- **PostgreSQL**: `python -m vieneu_portal db upgrade` tự `pg_dump` trước
  khi áp migration mới (`--no-backup` chỉ dùng khi máy không có `pg_dump`).
  Khôi phục bằng `pg_restore`/`psql` tương ứng với bản dump đó.
- **Lưu trữ object**: sao lưu bucket S3/MinIO riêng; CSDL chỉ lưu key của
  object, nên khôi phục riêng storage cần nội dung bucket khớp với các key
  đã có trong CSDL.

## 10. Thay đổi phá vỡ tương thích so với trang quản trị cũ

- Speech engine không còn route `/admin`, không CSDL, không Script Lab. `/`
  trên engine trả về `404` thuần.
- Engine từ chối khởi động khi `HOST` không phải loopback nếu thiếu
  `VIENEU_API_KEY`; các service Docker Compose của engine giờ bắt buộc biến
  này, không có giá trị mặc định (`${VIENEU_API_KEY:?set VIENEU_API_KEY}`).
- Khóa API do CSDL SQLite cũ cấp (`vn_...`) không còn dùng được trực tiếp
  với engine. Một API dành cho developer (C2, chưa xây) sẽ cấp lại khóa
  tương ứng gắn với portal.
- Một client gọi trực tiếp `POST /v1/audio/speech` của engine (không qua
  portal) không còn được áp từ điển phát âm nào — từ điển chung giờ chỉ áp
  ở portal; `preprocess: true` trên route đó vẫn thêm thẻ ngắt nghỉ/ngôn
  điệu, không gì khác.
- Script Lab được thay bằng `python -m vieneu_portal text preview` (mục 7);
  `vieneu-preprocess` vẫn là công cụ CLI độc lập với matcher riêng, không
  liên quan tới từ điển của portal.
