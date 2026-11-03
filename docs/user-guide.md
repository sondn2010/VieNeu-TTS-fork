# User guide

How to use the VieNeu user portal: sign up, accept the terms, generate
speech in the Studio, and manage your recordings in My Voices. For
operator-facing topics (environment variables, the admin area, the SQLite
migration runbook), read **Portal operations** (`docs/portal-operations.md`).
Vietnamese version: `docs/user-guide.vi.md`.

## 1. Sign up and sign in

1. Open the portal (`http://<host>:8100/` by default) and choose **Đăng ký**
   (Sign up). An email and a password of at least 10 characters are enough —
   a username is optional and defaults to the part of your email before `@`.
2. Signing up logs you in immediately and takes you to the Studio.
3. Already have an account? **Đăng nhập** (Log in) with the same email and
   password.

If signup is temporarily closed (`SIGNUP_DISABLED`, e.g. during an
operator's maintenance window) or you've hit the signup rate limit
(`SIGNUP_RATE_LIMITED`), the form shows why.

## 2. The terms modal

The first time you try to generate audio, a modal asks you to accept the
current terms. It cannot be dismissed by clicking outside it or pressing
Escape — read it, tick the checkbox, and press **Đồng ý và tiếp tục** (Agree
and continue). Every text you send is screened by the moderation layer
before it reaches the speech engine; content that violates the five listed
categories is rejected (`422`) and **never charges your token balance or
daily character limit**. If the terms are updated later, you'll see the
modal again before your next generation.

## 3. Studio (`/studio/`)

The Studio is where you turn text into speech.

### Toolbar

- **Voice selector**: pick a voice from the catalog; click the play icon
  next to a voice in the list to hear a short sample before choosing it.
- **Speed**: `0.5x` to `2.0x`. Speed only applies to **Tạo giọng nói**
  (Generate), not to **Phát ngay** (Play now / stream) — the note next to
  the button says so.
- **Emotion tags**: `[Cười]`, `[Thở dài]`, `[Hắng giọng]` insert
  `[cười]`/`[thở dài]`/`[hắng giọng]` at your cursor (or at the end of the
  text if the editor isn't focused), and the character/token counter updates
  immediately.
- **Tải tệp** (Upload file): load `.txt`, `.srt` (subtitle timing/index
  lines are stripped automatically) or `.docx` into the editor. You can also
  drag and drop a `.txt` file directly onto the editor.
- **Nhạc nền** (Background music), **Từ điển** (Dictionary link): shown with
  a "Sắp có" (Coming soon) badge — not available yet in this release.

### Writing

- The math/chemistry banner (dismissible, stays dismissed) is a reminder
  that the engine reads formulas like `ax² + bx + c = 0`, `Δ ≥ 0`,
  `x ∈ ℝ` and `2H2 + O2 → 2H2O` correctly, without any special markup.
- **Chèn câu mẫu** (Insert sample) fills the editor with a random example
  sentence if you just want to try the Studio out.
- The counter pill below the editor (`N ký tự · ~T token · còn D`) shows
  your character count, the estimated token cost, and how many characters
  you have left today. It turns red and disables **Tạo giọng nói** when
  your text would exceed either your remaining token balance or today's
  character limit.

### Phát ngay (Play now) vs Tạo giọng nói (Generate)

- **Phát ngay** streams audio directly to your browser at low latency and
  does **not** save a recording or appear in My Voices. It still counts
  against your quota, but only once the stream finishes — a connection drop
  or a stopped stream never charges you.
- **Tạo giọng nói** renders a full recording, saves it, and adds it to
  "Các bản ghi gần đây" (Recent recordings) right away. Short text renders
  immediately; longer text is queued and shown as in-progress until it
  finishes — you'll see its status update without reloading the page.
- You can only have one of these in flight at a time per account; starting
  a second one while the first is still running is rejected
  (`SYNTHESIS_IN_PROGRESS`) rather than silently queued behind it.
- If something goes wrong, the message tells you why: content rejected by
  moderation, the text grew too long after dictionary/formula expansion,
  you're out of tokens or today's character limit, the terms need accepting
  again, or the engine is temporarily busy (try again shortly).
- A recording that never finished rendering (the server died mid-request)
  shows as "interrupted, try again" and can be deleted from the list.

## 4. My Voices (`/voices/`)

Every recording you've generated with **Tạo giọng nói** lives here (streams
from **Phát ngay** are not saved).

- **Search** by the recording's text or voice name; **filter** by a specific
  voice you've used before.
- Each card plays/pauses, shows the original text, voice, duration and the
  date it was created, and lets you **download** the audio file or
  **delete** the recording (with a confirmation step).
- Only one recording plays at a time across the whole app — starting
  another one stops whatever was already playing.
- The footer always shows how many recordings match your current
  search/filter out of your total, and their combined duration.
- **+ Tạo mới** (Create new) takes you straight back to the Studio.

## 5. Your quota

The sidebar shows your token balance as `used / total` and resets your
daily character limit at midnight in the server's configured timezone. Both
numbers only ever change when a recording actually succeeds — a failed or
rejected request never touches them, and the Studio updates the sidebar
immediately after a successful generate without a page reload.

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Stuck on a loading screen after signing in | Your session may have expired; the portal redirects you to the login page automatically — sign in again. |
| The terms modal keeps reappearing | The terms version changed since you last accepted, or your browser cleared its local storage; accept it again — it takes one click. |
| "Mỗi lần chỉ tạo được một giọng nói" (Only one synthesis at a time) | A previous **Phát ngay** or **Tạo giọng nói** from your account is still running; wait for it to finish. |
| "Bạn đã hết hạn mức token hoặc ký tự hôm nay" (Out of tokens or today's limit) | Wait for the daily reset, or ask an administrator to adjust your plan/balance from the admin area. |
| A generated recording never shows up | Check "interrupted, try again" rows in Recent recordings/My Voices — the render may have failed partway and needs retrying. |
| Content rejected by moderation | Re-read the terms (§2); the five prohibited categories apply to every text, including one a pronunciation rule expanded into. |
