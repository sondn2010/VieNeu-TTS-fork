# 09. Tiêu Chí Nghiệm Thu & Kịch Bản Kiểm Thử (QA/QC Acceptance Criteria)

* **Phiên bản:** 1.0
* **Đối tượng:** QA/QC Engineers, Product Owner, Frontend/Backend Developers

---

## 1. Bảng Kiểm Thử Chức Năng Theo Từng Màn Hình (Functional Test Matrix)

| Mã Test | Phân Hệ | Kịch Bản Kiểm Thử (Test Scenario) | Kết Quả Mong Đợi (Expected Result) |
| :--- | :--- | :--- | :--- |
| **TC-01** | **Modal Điều Khoản** | Mở Phòng thu bằng tài khoản mới chưa đồng ý điều khoản; thử bỏ chọn Checkbox. | Modal *Điều khoản tạo giọng nói* hiện lên khóa màn hình; khi bỏ tích Checkbox, nút `Đồng ý và tiếp tục` bị vô hiệu hóa (`disabled`). |
| **TC-02** | **Kiểm Duyệt AI** | Nhập nội dung vi phạm 1 trong 5 mục *Không được phép* và bấm `Tạo giọng nói`. | Hệ thống chặn yêu cầu, hiển thị thông báo vi phạm điều khoản và **không trừ** số dư token hay hạn mức ký tự ngày của người dùng. |
| **TC-03** | **Phòng Thu** | Đặt con trỏ vào giữa câu trong ô văn bản, bấm nút cảm xúc `[Cười]`. | Tag cảm xúc được chèn đúng vào vị trí con trỏ; bộ đếm ký tự và ước tính token ở góc trái dưới cập nhật tức thì. |
| **TC-04** | **Phòng Thu (Toán/Hóa)** | Nhập `Giải phương trình ax² + bx + c = 0 với Δ ≥ 0, x ∈ ℝ và phản ứng 2H2 + O2 → 2H2O`. | Hệ thống tự nhận diện và phát âm chính xác toàn bộ ký hiệu lũy thừa, bất đẳng thức, tập hợp số thực và phương trình hóa học bằng tiếng Việt tự nhiên. |
| **TC-05** | **Podcast Studio** | Kiểm tra giới hạn số lượt thoại trên tài khoản gói thường và gói trả phí. | Gói thường cho phép thêm tối đa `200 lượt`; gói trả phí cho phép tối đa `1.000 lượt`. Bấm `Tạo podcast` ghép các lượt thoại thành 1 tập hoàn chỉnh. |
| **TC-06** | **Phòng Thu Truyện** | Tạo dự án truyện có 3 phân đoạn đã tạo giọng; sửa văn bản ở phân đoạn 2 và kéo-thả phân đoạn 3 lên trước phân đoạn 2. | Chỉ phân đoạn 2 cần bấm `Tạo giọng` lại (đoạn 1 và 3 giữ nguyên audio không tốn lại token); khi bấm `Xuất truyện`, file audio xuất ra ghép đúng thứ tự `Đoạn 3 -> Đoạn 2 -> Đoạn 1`. |
| **TC-07** | **Giọng Nói Của Tôi** | Nhập từ khóa vào ô tìm kiếm hoặc chọn lọc theo giọng `Minh Quân`. | Danh sách lọc tức thì; thanh trạng thái dưới đáy cập nhật đúng `X trong số Y giọng nói` và cộng đúng `Tổng thời lượng: ...s`. |
| **TC-08** | **Bảng Xếp Hạng** | Một tài khoản tạo 100 bản ghi bằng giọng *Minh Quân* trong 7 ngày qua. | Trên *Bảng xếp hạng giọng*, tài khoản đó chỉ được tính là **1 người dùng** cho giọng *Minh Quân* (đúng quy tắc *"một người tạo nhiều cũng chỉ tính một"*). |
| **TC-09** | **Bảng Điều Khiển** | Đối chiếu số liệu giữa Sidebar, trang *Bảng điều khiển* và trang *Thanh toán*. | Số dư token (`140.574 / 150.000`), hạn mức ngày (`50.000`), ngày hết hạn (`6/11/2026`), số bản ghi thành công và tổng thời lượng (`2m 27s`) phải khớp nhau 100%. |
| **TC-10** | **Thanh Toán & Voucher** | Nhập mã `THINHVUONG` vào gói `Starter` và gói `Pro`. | Ở gói `Starter` báo lỗi không áp dụng; ở gói `Pro` (và `Creator`, `Studio`) giảm đúng `15%` giá tiền (mỗi tài khoản chỉ dùng được 1 lần trước hết ngày `31/12`). |
| **TC-11** | **API Nhà Phát Triển** | Bấm `+ Tạo khóa` ở tab `Live` và bấm `Sao chép` địa chỉ MCP `https://api.vieneu.io/mcp`. | Khóa `Live` được sinh ra và hiển thị trong danh sách; nút `Sao chép` copy chính xác chuỗi `https://api.vieneu.io/mcp` vào clipboard. |
| **TC-12** | **Từ Điển Phát Âm (Ưu tiên từ dài)** | Thêm 2 luật: `km` = `ki lô mét` và `km/h` = `ki lô mét trên giờ`. Gõ `Tốc độ 5 km/h` vào ô *Nghe thử cách đọc*. | Kết quả `Engine đọc:` phải hiển thị `Tốc độ 5 ki lô mét trên giờ` (ưu tiên luật dài hơn `km/h` thay vì bị cắt ở `km`). |
| **TC-13** | **Từ Điển Phát Âm (Không quét lặp)** | Thêm luật 1: `A` = `AB` và luật 2: `B` = `C`. Gõ `A` vào ô *Nghe thử cách đọc*. | Kết quả `Engine đọc:` hiển thị `AB` (không bị quét lại lần 2 thành `AC` và không bao giờ bị lặp vô hạn). |
| **TC-14** | **Từ Điển Phát Âm (Import File)** | Nhập file `.txt` có dòng `# comment`, dòng `GPU = Gờ Pê U` và dòng trùng từ `VieNeu = Vi Nêu Mới`. | Dòng `#` bị bỏ qua; các luật mới được xếp lên đầu bảng và luật `VieNeu = Vi Nêu Mới` đè lên luật `VieNeu` cũ. |
