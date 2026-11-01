# 08. Thiết Kế Cơ Sở Dữ Liệu & Đặc Tả RESTful API (Database Schema & API Contracts)

* **Phiên bản:** 1.0
* **Đối tượng:** Backend Engineers, Database Administrators, System Architects

---

## 1. Lược Đồ Cơ Sở Dữ Liệu Quan Hệ (PostgreSQL DDL Schema)

```sql
-- ============================================================================
-- 1. BẢNG NGƯỜI DÙNG & QUẢN LÝ HẠN MỨC TOKEN (USERS)
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    avatar_initials VARCHAR(4) NOT NULL DEFAULT 'US',
    plan_tier VARCHAR(32) NOT NULL DEFAULT 'TRIAL', -- 'TRIAL', 'STARTER', 'CREATOR', 'PRO', 'STUDIO'
    token_balance BIGINT NOT NULL DEFAULT 150000,
    token_quota_total BIGINT NOT NULL DEFAULT 150000,
    daily_char_limit INT NOT NULL DEFAULT 50000,
    daily_char_remaining INT NOT NULL DEFAULT 50000,
    plan_expires_at TIMESTAMPTZ,
    has_desktop_license BOOLEAN NOT NULL DEFAULT FALSE,
    has_accepted_tts_terms BOOLEAN NOT NULL DEFAULT FALSE,
    terms_accepted_at TIMESTAMPTZ,
    onboarding_completed_steps INT NOT NULL DEFAULT 0,
    onboarding_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    ui_theme VARCHAR(16) NOT NULL DEFAULT 'dark',
    ui_language VARCHAR(8) NOT NULL DEFAULT 'vi',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 2. BẢNG DANH MỤC GIỌNG NÓI HỆ THỐNG (VOICES)
-- ============================================================================
CREATE TABLE voices (
    id VARCHAR(64) PRIMARY KEY, -- VD: 'minh-quan', 'ngoc-lan', 'adam-top-top', 'hai-dang'
    name VARCHAR(120) NOT NULL,
    initials VARCHAR(4) NOT NULL,
    avatar_url TEXT,
    gender VARCHAR(16) NOT NULL CHECK (gender IN ('NAM', 'NU')),
    region VARCHAR(32) NOT NULL CHECK (region IN ('MIEN_BAC', 'MIEN_TRUNG', 'MIEN_NAM')),
    language_code VARCHAR(16) NOT NULL DEFAULT 'vi-VN',
    language_label VARCHAR(64) NOT NULL DEFAULT 'Tiếng Việt (VN)',
    model_version VARCHAR(16) NOT NULL DEFAULT 'V4',
    tags TEXT[] NOT NULL DEFAULT '{}',
    supported_styles TEXT[] NOT NULL DEFAULT ARRAY['Tự nhiên'],
    sample_audio_url TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 3. BẢNG BẢN GHI ÂM THANH ĐƠN GIỌNG (TTS_RECORDINGS)
-- ============================================================================
CREATE TABLE tts_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voice_id VARCHAR(64) NOT NULL REFERENCES voices(id),
    model_version VARCHAR(16) NOT NULL DEFAULT 'V4',
    original_text TEXT NOT NULL,     -- Văn bản gốc hiển thị trong Thư viện Giọng nói của tôi
    processed_text TEXT,             -- Văn bản sau khi qua bước chuẩn hóa Toán/Hóa & Từ điển phát âm
    speed DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    bg_music_id VARCHAR(64),
    char_count INT NOT NULL,
    tokens_consumed INT NOT NULL,
    duration_seconds DECIMAL(8,1) NOT NULL DEFAULT 0.0,
    audio_url TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'SUCCESS' CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED')),
    error_code VARCHAR(64),
    source_module VARCHAR(32) NOT NULL DEFAULT 'STUDIO', -- 'STUDIO', 'API', 'MCP'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tts_recordings_user_created ON tts_recordings(user_id, created_at DESC);
CREATE INDEX idx_tts_recordings_voice_created ON tts_recordings(voice_id, created_at DESC);

-- ============================================================================
-- 4. BẢNG PODCAST & CÁC LƯỢT THOẠI (PODCASTS & PODCAST_TURNS)
-- ============================================================================
CREATE TABLE podcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    settings_json JSONB NOT NULL DEFAULT '{"pause_ms": 400, "normalize_lufs": -16}'::jsonb,
    turn_count INT NOT NULL DEFAULT 0,
    total_chars INT NOT NULL DEFAULT 0,
    tokens_consumed INT NOT NULL DEFAULT 0,
    duration_seconds DECIMAL(8,1),
    audio_url TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PROCESSING', 'SUCCESS', 'FAILED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE podcast_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    podcast_id UUID NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    turn_order INT NOT NULL,
    speaker_name VARCHAR(100) NOT NULL, -- 'Host', 'Guest'
    voice_id VARCHAR(64) NOT NULL REFERENCES voices(id),
    style VARCHAR(64) NOT NULL DEFAULT 'Tự nhiên',
    content TEXT NOT NULL,
    turn_audio_url TEXT,
    duration_seconds DECIMAL(8,1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 5. BẢNG DỰ ÁN TRUYỆN NHIỀU GIỌNG (STORY_PROJECTS, CHARACTERS, SEGMENTS)
-- ============================================================================
CREATE TABLE story_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Truyện mới',
    model_version VARCHAR(16) NOT NULL DEFAULT 'V4',
    segment_count INT NOT NULL DEFAULT 0,
    merged_audio_url TEXT,
    total_duration_seconds DECIMAL(8,1),
    last_exported_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE story_characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES story_projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    voice_id VARCHAR(64) NOT NULL REFERENCES voices(id),
    color_hex VARCHAR(16) NOT NULL DEFAULT '#7C5CFC',
    default_style VARCHAR(64) NOT NULL DEFAULT 'Tự nhiên',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE story_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES story_projects(id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES story_characters(id),
    sort_order INT NOT NULL,
    content TEXT NOT NULL,
    audio_url TEXT,
    duration_seconds DECIMAL(8,1),
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'GENERATING', 'READY', 'MODIFIED')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 6. BẢNG TỪ ĐIỂN PHÁT ÂM THEO TÀI KHOẢN (PRONUNCIATION_RULES)
-- ============================================================================
CREATE TABLE pronunciation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_term VARCHAR(255) NOT NULL,
    phonetic_replacement VARCHAR(255) NOT NULL,
    match_whole_word BOOLEAN NOT NULL DEFAULT TRUE,
    case_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pronunciation_rules_user ON pronunciation_rules(user_id, sort_order ASC);

-- ============================================================================
-- 7. BẢNG KHÓA API NHÀ PHÁT TRIỂN & KẾT NỐI MCP (DEVELOPER_API_KEYS & MCP)
-- ============================================================================
CREATE TABLE developer_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    environment VARCHAR(16) NOT NULL CHECK (environment IN ('LIVE', 'TEST')),
    key_prefix VARCHAR(24) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE mcp_connected_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_name VARCHAR(120) NOT NULL, -- 'Claude', 'ChatGPT', 'Cursor', 'Claude Code'
    client_id VARCHAR(255) NOT NULL,
    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

-- ============================================================================
-- 8. BẢNG GÓI CƯỚC & MÃ GIẢM GIÁ (BILLING_PLANS & VOUCHERS)
-- ============================================================================
CREATE TABLE vouchers (
    code VARCHAR(64) PRIMARY KEY, -- VD: 'THINHVUONG'
    discount_percent INT NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
    applicable_plans TEXT[] NOT NULL, -- ARRAY['CREATOR', 'PRO', 'STUDIO']
    max_uses_per_user INT NOT NULL DEFAULT 1,
    total_quota INT,
    used_count INT NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
```

---

## 2. Đặc Tả Chi Tiết RESTful API Endpoints

### 2.1. Tổng hợp các Endpoints theo Module

| Phân Hệ | Method & Endpoint | Mô Tả Chức Năng |
| :--- | :--- | :--- |
| **User & Terms** | `GET /api/v1/user/me` | Trả về thông tin tài khoản, số dư token, hạn mức ký tự ngày, trạng thái đã đồng ý điều khoản và tiến độ Onboarding. |
| **User & Terms** | `POST /api/v1/user/terms/accept` | Lưu xác nhận người dùng đã tích chọn đồng ý *Điều khoản tạo giọng nói*. |
| **Phòng Thu** | `POST /api/v1/tts/preview-stream` | (`[⚡ Phát ngay]`) Kiểm duyệt AI -> Chuẩn hóa Toán/Hóa -> Áp dụng Từ điển -> Stream audio chunk độ trễ thấp. |
| **Phòng Thu** | `POST /api/v1/tts/generate` | (`[🔊 Tạo giọng nói]`) Tạo file âm thanh hoàn chỉnh, trừ token và lưu bản ghi vào `tts_recordings`. |
| **Giọng Nói Của Tôi** | `GET /api/v1/tts/recordings` | Tìm kiếm (`?q=`), lọc theo giọng (`?voice_id=`), phân trang và trả về kèm `total_duration_seconds`. |
| **Giọng Nói Của Tôi** | `DELETE /api/v1/tts/recordings/:id` | Xóa một bản ghi âm thanh khỏi thư viện. |
| **Podcast Studio** | `POST /api/v1/podcasts/ai-script` | (`[✨ Viết kịch bản bằng AI]`) Sinh mảng lượt thoại `Host`/`Guest` từ chủ đề người dùng nhập. |
| **Podcast Studio** | `POST /api/v1/podcasts` | (`[🎙️ Tạo podcast]`) Tổng hợp toàn bộ các lượt thoại và ghép thành 1 tập podcast. |
| **Phòng Thu Truyện** | `GET /api/v1/stories` & `POST /api/v1/stories` | Liệt kê danh sách dự án truyện và khởi tạo `+ Truyện mới`. |
| **Phòng Thu Truyện** | `POST /api/v1/stories/:id/segments/:segId/tts` | Tạo/tạo lại giọng đọc cho **1 phân đoạn độc lập** trong truyện. |
| **Phòng Thu Truyện** | `PUT /api/v1/stories/:id/segments/reorder` | Cập nhật thứ tự kéo-thả (`sort_order`) của các phân đoạn. |
| **Phòng Thu Truyện** | `POST /api/v1/stories/:id/export` | (`[🎬 Xuất truyện]`) Ghép tất cả phân đoạn thành 1 file âm thanh liền mạch. |
| **Bảng Xếp Hạng** | `GET /api/v1/voices/leaderboard` | Lọc bảng xếp hạng 50 giọng theo `period` (`7d`\|`all`), `gender`, `region` dựa trên số người dùng duy nhất. |
| **Bảng Điều Khiển** | `GET /api/v1/dashboard/summary` | Trả về toàn bộ dữ liệu cho trang Dashboard (Token, 4 thẻ KPI, biểu đồ 7 ngày, phân bổ giọng). |
| **Thanh Toán** | `POST /api/v1/billing/vouchers/apply` | Kiểm tra mã giảm giá (VD: `THINHVUONG`) theo gói cước và trả về số tiền được giảm. |
| **Thanh Toán** | `POST /api/v1/billing/checkout` | Tạo phiên thanh toán mua mới hoặc nâng cấp gói token (tính toán hoàn trả pro-rata). |
| **Nhà Phát Triển** | `GET /api/v1/developer/keys` & `POST` | Quản lý danh sách khóa API (`LIVE` / `TEST`). |
| **Từ Điển Phát Âm** | `GET /api/v1/dictionary` & `PUT` | Lấy và lưu toàn bộ bảng luật phát âm (tối đa 2.000 luật) của tài khoản. |

### 2.2. Mẫu Payload JSON Tiêu Chuẩn

#### Request `POST /api/v1/tts/generate`
```json
{
  "voice_id": "minh-quan",
  "text": "Có một sự thật kỳ lạ trong tâm lý con người [thở dài] là khi một mối đe dọa...",
  "speed": 1.0,
  "bg_music_id": null
}
```

#### Response `200 OK`
```json
{
  "recording": {
    "id": "c9a4f812-3b1d-4e92-9102-88a7f12e3011",
    "original_text": "Có một sự thật kỳ lạ trong tâm lý con người [thở dài] là khi một mối đe dọa...",
    "voice": {
      "id": "minh-quan",
      "name": "Minh Quân",
      "language_label": "Tiếng Việt (VN)",
      "model_version": "V4"
    },
    "duration_seconds": 146.0,
    "tokens_consumed": 8110,
    "audio_url": "https://cdn.vieneu.io/recordings/c9a4f812.mp3",
    "created_at": "2026-10-30T16:23:00+07:00"
  },
  "quota": {
    "token_balance": 140574,
    "token_quota_total": 150000,
    "daily_char_remaining": 48920
  }
}
```
