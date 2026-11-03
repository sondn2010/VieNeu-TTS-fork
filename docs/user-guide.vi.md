# Hướng dẫn sử dụng

Cách dùng portal người dùng của VieNeu: đăng ký, đồng ý điều khoản, tạo
giọng nói ở Phòng thu, và quản lý bản ghi ở Giọng nói của tôi. Các nội dung
dành cho người vận hành (biến môi trường, khu vực quản trị, quy trình di
chuyển dữ liệu SQLite) nằm ở **Vận hành Portal** (`docs/portal-operations.vi.md`).
Bản tiếng Anh: `docs/user-guide.md`.

## 1. Đăng ký và đăng nhập

1. Mở portal (mặc định `http://<host>:8100/`) và chọn **Đăng ký**. Chỉ cần
   email và mật khẩu ít nhất 10 ký tự — tên người dùng là tuỳ chọn, mặc
   định lấy phần trước `@` trong email.
2. Đăng ký xong sẽ tự đăng nhập và chuyển vào Phòng thu.
3. Đã có tài khoản? Chọn **Đăng nhập** với email và mật khẩu đó.

Nếu đăng ký đang tạm đóng (`SIGNUP_DISABLED`, ví dụ khi người vận hành đang
bảo trì) hoặc bạn đăng ký quá nhiều lần (`SIGNUP_RATE_LIMITED`), form sẽ
hiện rõ lý do.

## 2. Modal điều khoản

Lần đầu bạn thử tạo giọng nói, một modal sẽ yêu cầu đồng ý điều khoản hiện
hành. Modal này không thể đóng bằng cách bấm ra ngoài hoặc nhấn Escape — hãy
đọc kỹ, tích vào ô xác nhận, rồi bấm **Đồng ý và tiếp tục**. Mọi văn bản bạn
gửi đều được hệ thống kiểm duyệt trước khi tới speech engine; nội dung vi
phạm một trong năm nhóm được liệt kê sẽ bị từ chối (`422`) và **không bao
giờ trừ số dư token hay hạn mức ký tự ngày**. Nếu điều khoản được cập nhật
sau này, modal sẽ hiện lại trước lần tạo giọng tiếp theo.

## 3. Phòng thu (`/studio/`)

Phòng thu là nơi bạn chuyển văn bản thành giọng nói.

### Thanh công cụ

- **Chọn giọng nói**: chọn một giọng từ danh mục; bấm icon play cạnh một
  giọng trong danh sách để nghe thử trước khi chọn.
- **Tốc độ**: từ `0.5x` đến `2.0x`. Tốc độ chỉ áp dụng cho **Tạo giọng nói**,
  không áp dụng cho **Phát ngay** (stream) — ghi chú cạnh nút đã nói rõ.
- **Thẻ cảm xúc**: `[Cười]`, `[Thở dài]`, `[Hắng giọng]` chèn
  `[cười]`/`[thở dài]`/`[hắng giọng]` vào đúng vị trí con trỏ (hoặc cuối văn
  bản nếu ô soạn thảo không được focus), bộ đếm ký tự/token cập nhật ngay.
- **Tải tệp**: nạp `.txt`, `.srt` (dòng số thứ tự/thời gian được tự động
  loại bỏ) hoặc `.docx` vào ô soạn thảo. Cũng có thể kéo-thả trực tiếp một
  tệp `.txt` vào vùng soạn thảo.
- **Nhạc nền**, **Từ điển**: hiện kèm nhãn "Sắp có" — chưa khả dụng ở bản
  này.

### Soạn văn bản

- Banner toán/hóa (có thể đóng, sẽ nhớ trạng thái đã đóng) nhắc rằng engine
  đọc đúng các công thức như `ax² + bx + c = 0`, `Δ ≥ 0`, `x ∈ ℝ` và
  `2H2 + O2 → 2H2O` mà không cần đánh dấu gì đặc biệt.
- **Chèn câu mẫu** điền một câu ví dụ ngẫu nhiên vào ô soạn thảo nếu bạn
  chỉ muốn thử Phòng thu.
- Thanh đếm dưới ô soạn thảo (`N ký tự · ~T token · còn D`) hiện số ký tự,
  số token ước tính, và số ký tự còn lại trong hôm nay. Thanh này chuyển
  màu đỏ và vô hiệu hóa nút **Tạo giọng nói** khi văn bản vượt số dư token
  hoặc hạn mức ký tự ngày.

### Phát ngay và Tạo giọng nói

- **Phát ngay** truyền âm thanh trực tiếp tới trình duyệt với độ trễ thấp
  và **không** lưu thành bản ghi, không xuất hiện ở Giọng nói của tôi. Vẫn
  tính vào hạn mức, nhưng chỉ sau khi stream hoàn tất — mất kết nối hoặc
  dừng giữa chừng không bao giờ bị trừ.
- **Tạo giọng nói** tạo một bản ghi đầy đủ, lưu lại, và thêm ngay vào "Các
  bản ghi gần đây". Văn bản ngắn được tạo ngay; văn bản dài hơn được xếp
  hàng và hiện trạng thái đang xử lý cho tới khi xong — bạn sẽ thấy trạng
  thái cập nhật mà không cần tải lại trang.
- Mỗi tài khoản chỉ được chạy một trong hai thao tác này cùng lúc; bắt đầu
  thao tác thứ hai khi thao tác đầu chưa xong sẽ bị từ chối
  (`SYNTHESIS_IN_PROGRESS`) chứ không xếp hàng ngầm phía sau.
- Nếu có lỗi, thông báo sẽ nói rõ lý do: nội dung bị kiểm duyệt từ chối,
  văn bản sau khi mở rộng theo từ điển/công thức quá dài, bạn đã hết token
  hoặc hạn mức ngày, cần đồng ý lại điều khoản, hoặc engine đang bận (thử
  lại sau).
- Một bản ghi chưa render xong (server gặp sự cố giữa chừng) sẽ hiện "đã
  gián đoạn, thử lại" và có thể xóa khỏi danh sách.

## 4. Giọng nói của tôi (`/voices/`)

Mọi bản ghi bạn đã tạo bằng **Tạo giọng nói** nằm ở đây (stream từ **Phát
ngay** không được lưu).

- **Tìm kiếm** theo văn bản hoặc tên giọng của bản ghi; **lọc** theo một
  giọng cụ thể bạn đã từng dùng.
- Mỗi thẻ cho phép play/pause, hiện văn bản gốc, giọng đọc, thời lượng và
  ngày tạo, cùng nút **tải xuống** file âm thanh hoặc **xóa** bản ghi (có
  bước xác nhận).
- Tại một thời điểm chỉ một bản ghi được phát trên toàn ứng dụng — phát
  bản khác sẽ tự dừng bản đang phát.
- Thanh dưới đáy luôn hiện số bản ghi khớp với tìm kiếm/lọc hiện tại trên
  tổng số bản ghi, và tổng thời lượng của chúng.
- **+ Tạo mới** đưa bạn quay lại Phòng thu ngay.

## 5. Hạn mức của bạn

Sidebar hiện số dư token dạng `đã dùng / tổng`, và hạn mức ký tự ngày được
đặt lại vào nửa đêm theo múi giờ server cấu hình. Hai số này chỉ thay đổi
khi một bản ghi thực sự thành công — yêu cầu lỗi hoặc bị từ chối không bao
giờ chạm vào chúng, và Phòng thu cập nhật sidebar ngay sau khi tạo giọng
thành công mà không cần tải lại trang.

## 6. Khắc phục sự cố

| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| Kẹt ở màn hình đang tải sau khi đăng nhập | Session có thể đã hết hạn; portal tự chuyển về trang đăng nhập — đăng nhập lại. |
| Modal điều khoản hiện lại liên tục | Phiên bản điều khoản đã đổi từ lần đồng ý trước, hoặc trình duyệt đã xóa local storage; đồng ý lại — chỉ một lần bấm. |
| "Mỗi lần chỉ tạo được một giọng nói" | Một lượt **Phát ngay** hoặc **Tạo giọng nói** trước đó từ tài khoản của bạn vẫn đang chạy; chờ nó xong. |
| "Bạn đã hết hạn mức token hoặc ký tự hôm nay" | Chờ đến lượt đặt lại hằng ngày, hoặc yêu cầu quản trị viên điều chỉnh gói/số dư từ khu vực quản trị. |
| Một bản ghi vừa tạo không thấy xuất hiện | Kiểm tra dòng "đã gián đoạn, thử lại" ở Các bản ghi gần đây/Giọng nói của tôi — có thể quá trình tạo đã lỗi giữa chừng và cần thử lại. |
| Nội dung bị kiểm duyệt từ chối | Đọc lại điều khoản (mục 2); năm nhóm nội dung không được phép áp dụng cho mọi văn bản, kể cả văn bản do một quy tắc từ điển mở rộng ra. |
