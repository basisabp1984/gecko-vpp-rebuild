# VOICE_AGENT_INSTRUCTIONS.md — Voice agent specialist lead

**Owner role:** Voice agent lead (separate from text AI agents — see `AI_AGENTS_INSTRUCTIONS.md` for those).
**Phase:** Phase 4.9 (per `ARCHITECTURE.md` §12).
**Authoritative parents:** `ARCHITECTURE.md` §7.5, §4.8 (`GET /api/v1/agents/voice/session`), §11 FMEA F10, F18, §14.5. `PRODUCT_BRIEF.md` acceptance criterion §11.16 (verbatim: *"Voice agent: ≥1 voice agent accessible from topbar (push-to-talk). OpenAI Realtime / Whisper+TTS / Eleven Labs — Phase 3 chooses. Covers 3–5 базових сценаріїв українською («що сьогодні з виробництвом?», «коли заряджати батарею?», «коли наступний небаланс?», etc.)."*).
**User hard constraint** (`PROGRESS.md` Hard constraints): *"Voice agent: stub by default (no paid OpenAI API without explicit auth). Architectural contract supports real Realtime API when user supplies key."* — non-negotiable.
**Status:** locked by Senior Detailed Architect on 2026-05-23.

---

## 0. Goal

Ship a Ukrainian-speaking push-to-talk voice agent visible on every persona surface that:
1. **Default deploy** (no `OPENAI_API_KEY`, no `VOICE_PROVIDER` env override): works in Chrome / Edge using browser-native **Web Speech API** (STT via `SpeechRecognition`, TTS via `SpeechSynthesisUtterance`). Transcript flows through the existing text-agent endpoint `POST /api/v1/agents/{persona}/query`; the response is read aloud client-side. Zero external API spend, zero new server-side dependencies.
2. **Opt-in upgrade** (`VOICE_PROVIDER=openai-realtime` AND `OPENAI_API_KEY=sk-…` present at backend startup): `GET /api/v1/agents/voice/session` returns an OpenAI Realtime ephemeral session token + WebSocket URL. The browser opens a direct WSS to OpenAI. The text-agent path is bypassed. Cost is gated by both an env-var switch and the user's explicit click on the voice button.
3. **Browser falls back to text-only** when `SpeechRecognition` is not available (Firefox, Safari, mobile Safari) — input field appears, transcript is sent through the same POST.

Scope of this instructions file:
- Backend: `apps/api/app/agents/voice.py`, the route handler for `GET /api/v1/agents/voice/session`, env-var plumbing, ephemeral-token issuance (Realtime path only).
- Frontend: `apps/web/src/components/voice/VoiceButton.tsx`, `VoiceSession.tsx`, `useSpeechRecognition.ts` hook, ARIA-live caption pane, fallback text input.
- 5 canned scenarios pre-rendered as visible test cases in the dev portal (`/developer/voice/`).
- Rate-limit guard (5 sessions per IP per hour, even in stub mode, for symmetry with Realtime mode).

Out of scope:
- Whisper-based STT on the backend (BRIEF §11.16 lists it as an option, ARCH §7.5 explicitly chose Realtime; we do NOT implement Whisper).
- Eleven Labs (same — not chosen).
- Server-side TTS of any kind.
- A voice agent for `/admin/*` (only the three persona surfaces `/producer/`, `/c-i/`, `/storage/` get the button per §11.16; `/admin/` is operator-internal).
- Recording or persisting audio (privacy + no file upload per ARCH §9.10).

---

## 1. Success criteria (measurable)

Mirrors `PRODUCT_BRIEF.md` §11.16 plus ARCH §14.5 checklist.

| # | Criterion | How it is measured | Source |
|---|---|---|---|
| V1 | Push-to-talk button visible in the topbar on every persona surface (`/producer/*`, `/c-i/*`, `/storage/*`) | Playwright smoke test asserts `[data-testid="voice-button"]` exists on 4 representative routes | BRIEF §11.16, ARCH §5.2 |
| V2 | **Default behavior with no env var**: button → browser SpeechRecognition → transcript → POST `/api/v1/agents/{persona}/query` → response read via `speechSynthesis.speak(...)` | Manual cross-browser test against Chrome (Mac + Win) + Edge (Win) records all 3 canned scenarios pass | BRIEF §11.16, ARCH §7.5 |
| V3 | **Upgraded behavior** (env `VOICE_PROVIDER=openai-realtime` + `OPENAI_API_KEY` set): backend returns `provider="openai-realtime"`, ephemeral token, OpenAI WSS URL. Frontend opens the WSS. | Contract test stubs OpenAI ephemeral-key endpoint and asserts response shape; manual test with real key on demand only | ARCH §7.5, §4.8, §14.5 |
| V4 | **No API call to OpenAI happens unless** `VOICE_PROVIDER=openai-realtime` AND `OPENAI_API_KEY` set AND user clicked the button | Backend startup log shows `voice_provider=stub OPENAI_API_KEY=absent`; integration test asserts zero outbound network traffic under default env | User hard constraint, ARCH §14.5 |
| V5 | Button is **keyboard-activatable** (`<button>` element, Space / Enter), has `aria-pressed`, `aria-label="Голосовий помічник"`, response captions render in an `aria-live="polite"` region | Axe-core a11y test passes on `/producer/` | ARCH §5.1, §14.5 |
| V6 | **5 canned scenarios visible** in `/developer/voice/`: clicking each "Run sample" button issues the exact phrase to the voice pipeline and shows the resulting agent response side-by-side | Smoke test verifies the page lists all 5 | ARCH §4.8 canned_scenarios list |
| V7 | **Graceful fallback** on Firefox / Safari iOS: detects missing `window.SpeechRecognition && window.webkitSpeechRecognition`, renders text input, banner: *"Голосовий режим недоступний у вашому браузері. Введіть запит текстом."* | Manual Firefox + iOS Safari test | ARCH §7.5 |
| V8 | **Rate limit** 5 voice sessions per IP per hour, enforced even in stub mode | Integration test bursts 6 GETs from same IP, 6th returns HTTP 429 | ARCH §7.5, §14.5 |
| V9 | **Stub-mode banner** in the voice panel: *"Демонстраційний режим — використовується голосовий рушій браузера. Без оплати зовнішніх API."* | Visible in stub mode; replaced by *"Realtime режим активний — використовується OpenAI Realtime API."* when provider switches | ARCH §14.5 |

---

## 2. Tools — exact stack and justification

### Browser-side
| Concern | Choice | Why this and not the alternative |
|---|---|---|
| STT | `window.SpeechRecognition || window.webkitSpeechRecognition`, `lang="uk-UA"`, `continuous=false`, `interimResults=true` | Browser-native, zero deps, zero API cost. Chrome / Edge use Google's cloud STT under the hood — already paid for by the user's browser vendor, not us. |
| TTS | `window.speechSynthesis`, `SpeechSynthesisUtterance` with `lang="uk-UA"`, voice selection via `speechSynthesis.getVoices().find(v => v.lang === 'uk-UA')` with fallback to `lang.startsWith('uk')` then any voice (and TTS-skip if none — caption-only) | Same reasoning. Note: Chrome on macOS often lacks `uk-UA` voice; fallback to any voice + Cyrillic transliteration is NOT done — we just speak with whatever voice is available, accepting an accent. The caption is the authoritative output. |
| Realtime path WS | Browser-native `WebSocket` API | Standard, no library needed. OpenAI Realtime uses raw WS. |
| State / data fetching | TanStack Query (already in the FE stack per ARCH §5.4) | Existing dep |

### Backend-side
| Concern | Choice | Why |
|---|---|---|
| HTTP client for OpenAI ephemeral-key issuance | `httpx.AsyncClient` (already in FastAPI stack) | No new dep |
| Env-var loading | `pydantic-settings` (already used per ARCH §6) | Existing dep |
| Rate limit | Reuse existing application-level limiter (ARCH §9.5) keyed by IP, 5/hour bucket | Existing infra |

### Forbidden
- **OpenAI Python SDK** — we hit one endpoint (ephemeral key issuance); a 4-line httpx call avoids dragging in the whole SDK and its tokenizer dependencies.
- **Any TTS package** (`gTTS`, `pyttsx3`, `azure-cognitiveservices-speech`, etc.) — Phase 3 explicitly chose Realtime over Whisper+TTS.
- **Eleven Labs SDK** — not chosen.
- **MediaRecorder upload** to backend — ARCH §9.10 forbids file upload; we never send audio bytes to our backend in either mode.

---

## 3. Architecture detail

### 3.1 Frontend component tree

```
apps/web/src/components/voice/
├── VoiceButton.tsx          # the topbar push-to-talk button
├── VoiceSession.tsx         # the popover / drawer that opens when active
├── VoiceCaption.tsx         # aria-live caption pane
├── VoiceFallbackInput.tsx   # text input shown when SpeechRecognition unavailable
├── useSpeechRecognition.ts  # hook wrapping the browser API + state machine
├── useSpeechSynthesis.ts    # hook wrapping speechSynthesis.speak()
├── useVoiceSession.ts       # hook: GET /api/v1/agents/voice/session, decide provider
└── useRealtimeWS.ts         # hook: opens wss://api.openai.com/...; only mounted if provider==='openai-realtime'
```

**Mounting rule:** `<VoiceButton>` is rendered by `<TopBar>` (ARCH §5.2) only on persona surfaces. It is the same button regardless of provider; provider decision is fetched lazily on first click (`useVoiceSession()`).

### 3.2 State machine of `<VoiceSession>`

```
idle  ──click──▶ requesting_permission  ──granted──▶ listening
                                          ──denied──▶ error_no_mic
listening  ──speech_start──▶ recording (RMS meter animates)
recording  ──silence_2s──▶ transcribing  ──result──▶ querying_agent
querying_agent  ──response──▶ speaking  ──end──▶ idle
querying_agent  ──error──▶ error_agent
speaking  ──cancel_click──▶ idle (cancel speechSynthesis)
```

Realtime-mode states overlay this:
```
idle ──click──▶ opening_ws ──open──▶ realtime_active (full duplex; OpenAI drives turn-taking)
realtime_active ──close_click──▶ idle
realtime_active ──ws_error──▶ error_realtime
```

The same `<VoiceSession>` component handles both paths; a provider-discriminated state machine lives in `useVoiceSession.ts`.

### 3.3 Backend module

```
apps/api/app/agents/voice.py     # handle_session_request(...)
apps/api/app/agents/routers/voice.py   # FastAPI route GET /api/v1/agents/voice/session
apps/api/app/core/settings.py    # adds: VOICE_PROVIDER, OPENAI_API_KEY, OPENAI_REALTIME_MODEL
```

### 3.4 Endpoint contract — `GET /api/v1/agents/voice/session`

Already locked in ARCH §4.8. Restating for implementer:

**Request:** GET with `X-Tenant-Id` header. No body.

**Response — stub mode (default):**
```json
{
  "provider": "stub",
  "session_token": "demo-<uuid>",
  "websocket_url": null,
  "stt_lang": "uk-UA",
  "tts_lang": "uk-UA",
  "text_agent_url_template": "/api/v1/agents/{persona}/query",
  "canned_scenarios": [
    {"intent": "today_production",      "trigger": "що сьогодні з виробництвом",
     "persona_suggestion": "dispatcher_analyst"},
    {"intent": "charge_battery_when",   "trigger": "коли заряджати батарею",
     "persona_suggestion": "battery_coach"},
    {"intent": "next_imbalance_window", "trigger": "коли наступний небаланс",
     "persona_suggestion": "dispatcher_analyst"},
    {"intent": "asset_status_overview", "trigger": "покажи стан активів",
     "persona_suggestion": "market_analyst"},
    {"intent": "generate_report_today", "trigger": "сформуй звіт за сьогодні",
     "persona_suggestion": "energy_advisor"}
  ],
  "banner": "Демонстраційний режим — використовується голосовий рушій браузера."
}
```

**Response — openai-realtime mode (`VOICE_PROVIDER=openai-realtime` AND `OPENAI_API_KEY` set):**
```json
{
  "provider": "openai-realtime",
  "session_token": "<ephemeral key from openai>",
  "websocket_url": "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
  "expires_at": "2026-05-23T15:42:00Z",
  "canned_scenarios": [...same 5 items...],
  "banner": "Realtime режим активний — використовується OpenAI Realtime API."
}
```

**Error responses:**
- `429 Too Many Requests` when rate limit exceeded (V8).
- `503` if `VOICE_PROVIDER=openai-realtime` is set but `OPENAI_API_KEY` is absent — defensive (ARCH §7.5 says force to stub; we choose to surface the misconfiguration loudly in dev rather than silently fall back). **Decision rationale:** in production both env vars are set together or neither; surfacing 503 makes a mis-deploy obvious in 30 s. The frontend treats 503 as "no voice today" and shows the fallback input.

### 3.5 Ephemeral-key issuance (Realtime path only)

When `VOICE_PROVIDER=openai-realtime`:
1. Backend calls `POST https://api.openai.com/v1/realtime/sessions` with `Authorization: Bearer $OPENAI_API_KEY` and body `{"model":"gpt-4o-realtime-preview","voice":"alloy"}`.
2. OpenAI returns an ephemeral client key (`client_secret.value`) valid ~60 s.
3. Backend returns that key as `session_token` and the WSS URL to the frontend.
4. Frontend opens `new WebSocket(websocket_url, ["openai-insecure-api-key." + session_token, "openai-beta.realtime-v1"])` — exact subprotocol per OpenAI Realtime docs at implementation time.
5. **Backend NEVER stores the ephemeral key.** No DB write, no log line containing the key (mask in structlog).

This is the only code path that hits OpenAI. It runs only when the user clicks the voice button AND the env is set — fully gating the cost.

### 3.6 Cost guardrail

ARCH §7.5 + V8 mandate. Implementation:

| Layer | Mechanism | Trigger |
|---|---|---|
| Env-var | `VOICE_PROVIDER=stub` default; `OPENAI_API_KEY` absent default | Default deploy never spends |
| Endpoint rate-limit | 5 GETs per IP per hour, enforced in `apps/api/app/middleware/rate_limit.py` (shared with `/api/v1/agents/*/query` limiter from ARCH §9.5) | Even a malicious script in stub mode cannot DoS the endpoint |
| Browser confirm | First time user clicks the button in a session, modal: *"Активувати голосовий помічник? У цьому режимі ваш голос обробляється { стандартним рушієм браузера / API OpenAI }."* — provider-aware copy | User intent gate |
| Backend log | Every `provider==openai-realtime` response writes `audit.events` row with `event_type="voice.realtime_session_issued"` and `payload={ip, tenant_id, expires_at}` | Audit trail (ARCH §3.8) |

If `OPENAI_API_KEY` is leaked, the rate limit + the ephemeral token's 60 s lifetime keep blast radius small. If the user manually sets `VOICE_PROVIDER=openai-realtime` for a public demo, ARCH FMEA F18 (key leak) is the relevant control — git-secrets pre-commit + manual rotation.

---

## 4. Browser compatibility matrix

| Browser | OS | STT support | TTS (`uk-UA`) | Behavior we ship |
|---|---|---|---|---|
| Chrome ≥ 110 | macOS / Windows / Linux | YES (`webkitSpeechRecognition` alias) | macOS: often missing (use any voice; caption authoritative). Windows: usually OK. Linux: depends on system. | Full STT + TTS. Stub provider. |
| Edge ≥ 110 | Windows / macOS | YES | YES (uses Windows narrator) | Full STT + TTS. Stub provider. |
| Firefox | All | NO (no `SpeechRecognition` constructor) | YES | **Fallback to text input.** Banner: *"Голосовий режим недоступний у вашому браузері. Введіть запит текстом."* User types; pipeline still calls text agent + reads response. |
| Safari ≥ 17 | macOS | Partial (requires user gesture each session; `webkitSpeechRecognition` API but flaky `uk-UA`) | YES | Try STT; on first error switch to fallback input. |
| Safari iOS | iOS / iPadOS | NO (Apple disabled it post-iOS 14 for privacy) | YES | **Fallback to text input.** Banner as above. Tested on iOS 17 simulator + 1 real iPhone. |
| Mobile Chrome | Android | YES | YES | Full STT + TTS. |

**Detection code (locked snippet — implement verbatim):**

```typescript
// useSpeechRecognition.ts (sketch — implementer expands)
const STTCtor: typeof SpeechRecognition | undefined =
  (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;

export function hasSTT(): boolean { return typeof STTCtor === "function"; }

export function hasTTS(): boolean {
  return typeof window.speechSynthesis === "object"
      && typeof window.SpeechSynthesisUtterance === "function";
}

export function findUkVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();   // may be [] on first call
  return voices.find(v => v.lang === "uk-UA")
      ?? voices.find(v => v.lang.startsWith("uk"))
      ?? null;
}

// Boot path:
if (!hasSTT()) renderFallbackInput();
else startSpeechRecognition({ lang: "uk-UA", continuous: false, interimResults: true });
```

**Voice list bootstrapping quirk:** `getVoices()` returns `[]` until the browser fires `voiceschanged`. The hook MUST listen for that event and re-pick voice on the next render. Common mistake (call out for implementer).

---

## 5. The 5 canned scenarios

The 5 scenarios (per ARCH §4.8 response payload) become both:
- Server-side metadata returned by `/api/v1/agents/voice/session` (data),
- Frontend visible buttons on `/developer/voice/` test page (UI).

| # | UA trigger phrase | Expected intent | Suggested persona | Why this one |
|---|---|---|---|---|
| 1 | «що сьогодні з виробництвом» | `today_production` | `dispatcher_analyst` | BRIEF §11.16 explicit example |
| 2 | «коли заряджати батарею» | `charge_battery_when` | `battery_coach` | BRIEF §11.16 explicit example |
| 3 | «коли наступний небаланс» | `next_imbalance_window` | `dispatcher_analyst` | BRIEF §11.16 explicit example |
| 4 | «покажи стан активів» | `asset_status_overview` | `market_analyst` | Cross-persona intent — proves multi-persona coverage |
| 5 | «сформуй звіт за сьогодні» | `generate_report_today` | `energy_advisor` | Cross-persona intent + verifies the `/zvity` UI link in evidence |

The dev portal page `/developer/voice/` lists them as 5 cards. Each card has:
- The UA phrase (printed)
- A "Run sample" button that simulates the click — sends the phrase as if STT had transcribed it through the same `useVoiceSession` pipeline
- A display of the agent's rendered answer (UI-mirror of what the user would hear)
- A "Listen" button that triggers TTS on the rendered answer

This page doubles as the manual cross-browser test plan: an implementer or QA runs through 5 cards × 4 browsers = 20 manual checks (V2).

---

## 6. UI / a11y contract

### Topbar button (per ARCH §5.2)

```tsx
<button
  type="button"
  data-testid="voice-button"
  aria-pressed={isActive}
  aria-label="Голосовий помічник"
  onClick={toggleVoice}
  className="topbar-icon-btn"
>
  <MicIcon /> {/* lucide-react */}
</button>
```

### Voice panel (drawer / popover)

- Opens to the right of the topbar; constrained width 360 px on desktop, full-width sheet on mobile.
- Top section: provider banner (V9 copy), close button.
- Middle: live caption pane, `<div role="status" aria-live="polite" aria-atomic="false">` — populated with interim transcript, then final transcript, then agent response.
- Bottom: large mic button (re-tap to stop), or in fallback mode the text input + Submit.
- Cancel-speak button: visible when TTS is mid-utterance, calls `speechSynthesis.cancel()`.

### Keyboard

- Topbar mic button: Tab-reachable, Enter / Space activates.
- Inside panel: Esc closes; Cmd/Ctrl+Enter submits in fallback input.

### Visual

- Listening state: pulse animation on mic icon (200 ms cycle).
- Speaking state: progress bar tick under caption pane.
- Both themes (light primary + dark accessibility, per BRIEF §11.1) must render correctly. Reuse design tokens from ARCH §5.1.

---

## 7. Pre-flight check (mandatory before writing code)

Same four-question pattern as the AI agents file (per user template). Implementer answers yes to all four before starting code:

1. **Goal clear?** — Browser-native STT + TTS in stub default; OpenAI Realtime in opt-in; both providers share the same `<VoiceButton>` shell; cost is gated by two env vars + a user click. *Yes / no?*
2. **Criteria measurable?** — V1–V9 in §1 are each binary, runnable from Playwright / axe-core / curl. *Yes / no?*
3. **Tools available?** — Chrome on dev machine (for manual test), no new npm dep beyond what's in `apps/web/package.json`, no new Python dep beyond httpx (already there). Backend `apps/api/app/agents/routers/text.py` already exists (Phase 4.8 — AI agents lead's work). *Yes / no?*
4. **Plan complete?** — §3 component tree, §4 browser matrix, §5 scenarios, §6 a11y all specified; provider switch fully locked. Open questions limited to: which voice OpenAI returns by default (alloy / verse / etc. — punted to deploy-time tuning). *Yes / no?*

If "no" anywhere, STOP. Escalate or log to `difficulties_log.md`.

---

## 8. Branching protocol (what to do when stuck)

Same pattern as `AI_AGENTS_INSTRUCTIONS.md` §9. Voice-specific branches the lead is pre-authorised to take:

| Obstacle | Allowed branch | Re-escalate to user? |
|---|---|---|
| Chrome `uk-UA` voice missing on macOS test machine | Fall back to any voice; caption pane carries the meaning | No — log to difficulties_log |
| `SpeechRecognition` flaky on a specific Chrome version | Tighten the silence-detect threshold from 2 s → 3 s; add a manual "Stop" button | No |
| OpenAI Realtime ephemeral-key API endpoint shape changes between spec date (2026-05) and implementation | Pin to the snapshot of OpenAI docs at impl time; document the exact endpoint URL + response shape in the code comment | No — record version in commit message |
| User on staging asks for Whisper-based STT after all | DO NOT silently add Whisper. Push back: ARCH §7.5 explicitly chose Realtime over Whisper. If user re-confirms, log to difficulties_log AND escalate to architect | **Yes** |
| `audit.events` write fails | Swallow + structlog warn (do not fail the voice request) | No |
| Rate limit triggers in CI E2E test (test bursts 6× by design) | Expected — test asserts 429 on the 6th | No |

All other obstacles → standard difficulties_log entry, one alternative, return to main path.

---

## 9. Hand-off interfaces

### To Backend lead (`BACKEND_INSTRUCTIONS.md`)

Voice lead delivers `apps/api/app/agents/voice.py` (the handler) and `apps/api/app/agents/routers/voice.py` (the route). Backend lead is responsible for:
- Mounting the router in the main FastAPI app under `/api/v1/agents/`.
- Wiring `Settings.voice_provider` and `Settings.openai_api_key` into pydantic-settings.
- Ensuring the shared rate-limit middleware is applied to this route.

### To Frontend lead (`FRONTEND_INSTRUCTIONS.md`)

Voice lead delivers `apps/web/src/components/voice/*`. Frontend lead is responsible for:
- Mounting `<VoiceButton>` in the existing `<TopBar>` component conditioned on `pathname.startsWith("/producer") || pathname.startsWith("/c-i") || pathname.startsWith("/storage")`.
- Wiring the dev portal `/developer/voice/` page to import the same components in demo mode.

### To AI agents lead (`AI_AGENTS_INSTRUCTIONS.md`)

Hard dependency: voice lead's stub-mode happy path requires `POST /api/v1/agents/{persona}/query` to be functional (Phase 4.8 must be DONE before Phase 4.9 ends). The voice lead can build & test against a mock returning a fixed response if Phase 4.8 is delayed, but cannot ship.

### To Testing lead (`TESTING_INSTRUCTIONS.md`)

Voice lead contributes:
- A Playwright test that walks `/developer/voice/` and clicks all 5 "Run sample" buttons, asserting each shows an Ukrainian answer string.
- An axe-core check on the voice panel a11y.
- A unit test that mocks the OpenAI ephemeral-key endpoint and verifies the backend returns the correct envelope shape when `VOICE_PROVIDER=openai-realtime`.

### To DevOps lead (`DEVOPS_INSTRUCTIONS.md`)

`.env.example` entries (already partially specified in ARCH §13.5; voice lead confirms / adds):

```
# Voice agent (default = stub, no external API)
VOICE_PROVIDER=stub
# Opt-in upgrade. Leave BOTH commented to keep stub default.
# VOICE_PROVIDER=openai-realtime
# OPENAI_API_KEY=
# OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
```

---

## 10. Self-review checklist (the voice lead runs this before declaring done)

- [ ] `<VoiceButton>` renders on `/producer/`, `/c-i/`, `/storage/` (verified by Playwright).
- [ ] Click → permission prompt → record → STT → POST to text agent → response → TTS reads aloud (verified manually on Chrome macOS + Chrome Windows + Edge Windows).
- [ ] Firefox shows fallback text input + banner (verified manually).
- [ ] iOS Safari shows fallback text input + banner (verified on real device OR simulator).
- [ ] `GET /api/v1/agents/voice/session` with default env returns `provider:"stub"` and 5 canned scenarios.
- [ ] `GET /api/v1/agents/voice/session` with `VOICE_PROVIDER=openai-realtime` + `OPENAI_API_KEY=sk-test-…` (mocked in integration test) returns `provider:"openai-realtime"` with ephemeral token + WSS URL.
- [ ] `GET /api/v1/agents/voice/session` with `VOICE_PROVIDER=openai-realtime` + no key returns HTTP 503.
- [ ] Bursting 6 GETs from one IP within an hour returns 429 on the 6th.
- [ ] No outbound network call to `api.openai.com` under default env (verified by intercepting httpx in test).
- [ ] `/developer/voice/` page lists 5 scenario cards; each "Run sample" works.
- [ ] axe-core scan of voice panel returns zero critical violations.
- [ ] Topbar button has `aria-pressed`, `aria-label`, is Tab-reachable, Space-activates.
- [ ] Caption pane is `role="status" aria-live="polite"`.
- [ ] Stub-mode banner copy matches V9 verbatim.
- [ ] Realtime-mode banner copy matches V9 verbatim.
- [ ] `.env.example` documents both modes with `VOICE_PROVIDER=stub` as default.
- [ ] No new dependency added beyond what was already in `package.json` / `pyproject.toml`.
- [ ] ARCH §14.5 checklist (7 boxes) all ticked in commit description.
- [ ] PROGRESS.md updated with stage transition entry.

---

## 11. Done definition (binary)

This work-unit is **done** when, against a freshly deployed staging environment with default env (stub mode):

1. Visiting `https://gecko.radai-1984.dev/producer/` on Chrome shows the mic button in the topbar.
2. Clicking it, granting mic permission, saying "що сьогодні з виробництвом" → caption pane shows the transcript → caption pane shows the dispatcher_analyst answer → speech synthesis reads the answer aloud.
3. Visiting same on Firefox shows the fallback text input + banner; typing the same phrase + Submit produces the same answer rendered in the caption pane.
4. `curl -H 'X-Tenant-Id: <producer-1-uuid>' https://api.gecko.radai-1984.dev/api/v1/agents/voice/session` returns `provider:"stub"` and the 5 canned scenarios.
5. Visiting `https://gecko.radai-1984.dev/developer/voice/` shows the 5 scenario cards and "Run sample" works for each.
6. CI E2E suite passes including the rate-limit assertion.
7. ARCH §14.5 checklist ticked in the merge commit description.

---

## Appendix A — Provider-choice rationale (Realtime vs Whisper+TTS vs Eleven Labs)

The architect rejected Whisper+TTS and Eleven Labs in favour of OpenAI Realtime for the **opt-in** path. The voice lead should not relitigate this; the reasoning is recorded for code-review defence:

- **Whisper+TTS** = two API calls per turn + we host the audio plumbing + we pay both legs. Realtime = one duplex WS, no audio bytes on our servers. ARCH §9.10 forbids file upload anyway.
- **Eleven Labs** = TTS-only — would need to be paired with Whisper or browser STT regardless. Higher cost than Realtime for the same quality. Branding-locked voice catalog (cannot guarantee a Ukrainian voice without bespoke training).
- **OpenAI Realtime** = native Ukrainian understanding + Ukrainian speech synthesis in one provider, one auth, one billing line.

The **default** path is browser-native because BRIEF + user-constraint = "no paid API spend without explicit auth". Whisper is also out for the default path: it would need server-side audio handling we don't want.

If the user later asks for a self-hosted voice option (e.g., faster-whisper on the VPS), that becomes a Phase 5+ extension. Do not pre-implement it.

---

## Appendix B — Note on a known Web Speech API quirk for Ukrainian

Chrome's `SpeechRecognition` with `lang="uk-UA"` was added 2018 and is stable, but:
- Cold-start latency on first invocation per browser session can be 600–1200 ms while Chrome boots its remote STT pipeline.
- The API mid-stream pauses if user is silent > 2 s and emits `result.isFinal=true`. The hook MUST treat that as end-of-turn rather than restarting recognition automatically (auto-restart causes mic-permission re-prompts in some configs).
- Mobile Chrome on Android requests mic permission every time (no persistent grant) — UX accepts this trade.

Implementer should NOT add a polyfill or shim for Firefox / Safari STT — fall back to text input as specified. Polyfilling Web Speech API is a 60 kB+ rabbit hole and out of scope.
