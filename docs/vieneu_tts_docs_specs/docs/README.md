# Bộ Tài Liệu Đặc Tả Kỹ Thuật & Nghiệp Vụ — Hệ Thống VieNeu TTS (User Portal)

Chào mừng đội ngũ phát triển (Frontend, Backend, AI Engine, QA/QC). Thư mục `docs/` này chứa toàn bộ tài liệu đặc tả chi tiết được tách theo từng phân hệ chức năng và kỹ thuật dựa trên 10 màn hình UI/UX chuẩn của nền tảng **VieNeu**.

## Cấu trúc thư mục `docs/`

```text
docs/
├── README.md                                       # Trang điều hướng & hướng dẫn chung
├── assets/
│   └── screens/                                    # 10 ảnh chụp giao diện gốc đã chuẩn hóa tên
│       ├── 01_modal_dieu_khoan_tao_giong_noi.jpg
│       ├── 02_phong_thu_tts_studio.png
│       ├── 03_podcast_studio.png
│       ├── 04_phong_thu_truyen_story_studio.png
│       ├── 05_thu_vien_giong_noi_cua_toi.png
│       ├── 06_bang_xep_hang_giong.png
│       ├── 07_bang_dieu_khien_dashboard.png
│       ├── 08_thanh_toan_va_dang_ky.png
│       ├── 09_api_nha_phat_trien_mcp.png
│       └── 10_tu_dien_phat_am.png
└── specs/                                          # Thư mục đặc tả chi tiết theo module
    ├── 00_system_overview_and_ui_system.md         # Tổng quan hệ thống, Design Tokens, Sidebar & Global Layout
    ├── 01_terms_and_ai_moderation.md               # Modal Điều khoản tạo giọng nói & Pipeline AI Kiểm duyệt
    ├── 02_tts_studio_single_voice.md               # Phân hệ Phòng thu (TTS đơn giọng, cảm xúc, Toán/Hóa)
    ├── 03_podcast_and_story_studios.md             # Phân hệ Podcast Studio & Phòng thu Truyện nhiều giọng
    ├── 04_voice_library_and_leaderboard.md         # Phân hệ Giọng nói của tôi & Bảng xếp hạng giọng
    ├── 05_dashboard_and_billing.md                 # Phân hệ Bảng điều khiển (Dashboard) & Thanh toán/Gói Token
    ├── 06_developer_api_and_mcp.md                 # Phân hệ API Nhà phát triển (Live/Test Keys) & MCP Connector
    ├── 07_pronunciation_dictionary_and_nlp.md      # Phân hệ Từ điển phát âm & Thuật toán Text Normalization
    ├── 08_database_schema_and_api_contracts.md     # Thiết kế Database (PostgreSQL DDL) & RESTful API Endpoints
    ├── 09_qa_acceptance_criteria.md                # Checklist kiểm thử & Nghiệm thu (QA/QC Test Cases)
    └── vieneu_tts_user_specs.md                    # File tổng hợp toàn bộ đặc tả (All-in-One Master Spec)
```

## Hướng dẫn tra cứu nhanh theo vai trò (Role-based Guide)

* **Frontend Engineers (React/Next.js/Vue):** Xem `00_system_overview_and_ui_system.md` để cấu hình Design System/Layout, sau đó xem từ `01` đến `07` ứng với từng màn hình đang code.
* **Backend Engineers (API/Database/Billing):** Xem `08_database_schema_and_api_contracts.md` làm tài liệu nền tảng, kết hợp với logic nghiệp vụ ở `05_dashboard_and_billing.md` và `06_developer_api_and_mcp.md`.
* **AI / NLP Engineers (TTS Pipeline & Moderation):** Tập trung vào `01_terms_and_ai_moderation.md` (Content Safety) và `07_pronunciation_dictionary_and_nlp.md` (Chuẩn hóa công thức Toán/Hóa và thuật toán thay thế từ điển Single-Pass Longest-Match).
* **QA / Tester:** Sử dụng `09_qa_acceptance_criteria.md` để lập Test Plan và nghiệm thu từng tính năng trước khi release.
