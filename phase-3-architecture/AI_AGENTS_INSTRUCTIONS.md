# AI_AGENTS_INSTRUCTIONS.md — Text AI agents specialist lead

**Owner role:** AI agents lead (text only — voice is a separate file `VOICE_AGENT_INSTRUCTIONS.md`).
**Phase:** Phase 4.8 (per `ARCHITECTURE.md` §12).
**Authoritative parents:** `ARCHITECTURE.md` §7.1–§7.4, §3.7, §4.8, §11 (FMEA F11), §14.4. `PRODUCT_BRIEF.md` acceptance criterion §11.15 (verbatim: *"AI text agents — 4 total, persona-aware: Диспетчерський аналітик + Ринковий аналітик on `/producer/`, Енергетичний радник on `/c-i/`, Тренер по батареях on `/storage/`. Shared underlying engine (one classifier + per-persona system prompts). Each answers ≥3 question families with evidence drawn from the live DB, not hard-coded strings."*).
**Status:** locked by Senior Detailed Architect on 2026-05-23. Do not deviate without writing to `difficulties_log.md`.

---

## 0. Goal

Build **four** deterministic, persona-aware Ukrainian text agents served from `POST /api/v1/agents/{persona}/query` (§4.8) over a single classifier + per-persona Jinja2 templates, with every response backed by at least one cited row from the live Postgres dataset. No LLM call. No embeddings. No remote API.

Scope of this instructions file:
- The classifier `apps/api/app/agents/classifier.py`
- 12 intent modules in `apps/api/app/agents/intents/`
- 4 personas in `apps/api/app/agents/personas/`
- Jinja2 template tree `apps/api/app/agents/templates/<intent>__<persona>.j2`
- The 30-question gold-set fixture `apps/api/tests/fixtures/agent_gold_set.yaml`
- The CI test `apps/api/tests/test_agent_classifier_gold_set.py`

Out of scope (other leads own these):
- The route handler skeleton inside `apps/api/app/agents/routers/text.py` — Backend lead wires the FastAPI router, you fill in the agent logic that the handler delegates to (see §10).
- Frontend `<AgentChat>` component — Frontend lead.
- Voice — Voice lead (`VOICE_AGENT_INSTRUCTIONS.md`).

---

## 1. Success criteria (measurable)

Mirrors `PRODUCT_BRIEF.md` §11.15 plus the operational gates fixed by `ARCHITECTURE.md` §14.4. Acceptance is binary — each line is either true or this work-unit is not done.

| # | Criterion | How it is measured | Source |
|---|---|---|---|
| S1 | Each of 4 personas answers **≥ 3 distinct intent families** | `personas.<code>.allowed_intents` length ≥ 3, AND gold-set covers ≥ 3 distinct intents per persona | BRIEF §11.15 |
| S2 | **30-question gold-set passes 100%** in CI | `pytest apps/api/tests/test_agent_classifier_gold_set.py` exits 0 | ARCH §7.2, §14.4 |
| S3 | **Response time < 500 ms p95** on the synthetic dataset (this work-unit's contract is < 100 ms p95 per §14.4; 500 ms is the system-wide budget) | `duration_ms` column in `agents.query_log` over a 100-question replay | ARCH §14.4 |
| S4 | **Every response carries ≥ 1 source-data citation** rendered into the Ukrainian text (e.g., *"На основі даних РДН за 22.05.2026"*) AND ≥ 1 evidence chip in `evidence[]` | Schema test `test_response_has_evidence` asserts both | BRIEF §11.15 ("evidence drawn from the live DB, not hard-coded strings") |
| S5 | **No hard-coded answer strings** — every numeric or temporal slot in the response is derived from a SQL query result. Templates are checked for literal numbers via grep gate. | CI step `grep -nE '[0-9]{2,}' apps/api/app/agents/templates/` must return zero matches except whitelisted tokens (`24` for hour count, `100` for percent ceiling) | BRIEF §11.15 |
| S6 | **Every query writes one row** to `agents.query_log` (tenant_id, persona, classified_intent, confidence, response_text, evidence JSONB, duration_ms) | Integration test inserts and reads back | ARCH §3.7.1 |
| S7 | **Unknown / off-topic question** falls back to `unknown_intent` with `confidence=0.0` and returns a Ukrainian safe response listing 5 sample questions for the current persona | Gold-set includes 2 off-topic items per persona (see §6) | ARCH §7.1, FMEA F11 |
| S8 | **No LLM API call anywhere; no `sentence-transformers` dependency** in `pyproject.toml` | CI grep gate on dependency files + import linter rule `agents-no-llm` | ARCH §14.4 checklist |

---

## 2. Tools — exact stack and justification

| Concern | Choice | Why this and not the alternative |
|---|---|---|
| Language / runtime | Python 3.11+ (matches Backend) | ARCH §6.1 |
| Web framework | FastAPI router stub provided by Backend lead | ARCH §4.8 |
| DB driver | SQLAlchemy 2.0 async + asyncpg (already configured) | ARCH §6.2 |
| Templating | **Jinja2** (≥3.1) — one template file per `(intent, persona)` pair | ARCH §7.4; Jinja2 is already a transitive of FastAPI/Starlette so no new dep |
| Text normalisation | **stdlib only**: `str.casefold()` + `unicodedata.normalize('NFKD', …)` + small stopword set + lexicon dict | Pure Python, zero deps, < 5 ms per call. Sufficient for keyword classification. |
| Ukrainian morphology | **`pymorphy3` (optional, opt-in via setting `AGENTS_USE_MORPHOLOGY=true`)** with `pymorphy3-dicts-uk`. Pure Python, ~12 MB dictionaries, no native compile. | **Decision: ship the dep but default it OFF.** Justification: regex patterns + lexicon already absorb the 8 most common inflection variants per keyword (`прогноз/прогнозу/прогнозом/прогнози/прогнозів/прогнозами/forecast/forecasts`); lemmatisation is a quality nice-to-have, not a correctness requirement for a 12-intent classifier. Leaving it off keeps cold-start < 200 ms (no dictionary load). If the gold-set ever scales past 30 → 100 questions and patterns start to bloat, flip the env var. |
| Test framework | pytest + pytest-asyncio | ARCH §10.2 |
| Property fixture format | YAML (one file per gold-set entry-block) | Human-editable by non-Python contributors |
| Logging | structlog (already in backend stack) | ARCH §6 |

**Forbidden** (per ARCH §14.4 checklist and BRIEF §12):
- `openai`, `anthropic`, `litellm`, any LLM client
- `sentence-transformers`, `transformers`, `torch`, `spacy` (heavy NLP stacks)
- `langchain`, `llama-index` (would imply LLM)
- Any HTTP call to an external service from inside the classifier or intent handler

---

## 3. Architecture detail

### 3.1 Module tree (exact paths)

```
apps/api/app/agents/
├── __init__.py
├── classifier.py              # classify(text, persona) -> ClassifyResult
├── normalise.py               # tokenise + lemma + lexicon expansion
├── personas/
│   ├── __init__.py            # PERSONAS registry dict
│   ├── dispatcher_analyst.py
│   ├── market_analyst.py
│   ├── energy_advisor.py
│   └── battery_coach.py
├── intents/
│   ├── __init__.py            # INTENTS registry dict
│   ├── today_production.py
│   ├── next_imbalance_window.py
│   ├── arbitrage_window_today.py
│   ├── charge_battery_when.py
│   ├── deep_discharge_ok_today.py
│   ├── top_revenue_yesterday.py
│   ├── curtailment_today.py
│   ├── forecast_accuracy_today.py
│   ├── next_settlement_due.py
│   ├── flex_savings_potential.py
│   ├── asset_status_overview.py
│   ├── generate_report_today.py
│   └── unknown_intent.py
├── templates/                 # Jinja2 templates, naming: <intent>__<persona>.j2
│   ├── today_production__dispatcher_analyst.j2
│   ├── today_production__energy_advisor.j2
│   ├── next_imbalance_window__dispatcher_analyst.j2
│   ├── next_imbalance_window__market_analyst.j2
│   ├── ... (one file per allowed combination — see §5 matrix)
│   └── unknown_intent__shared.j2
├── evidence.py                # build_evidence(rows, table, columns, ui_link_fn)
├── audit.py                   # write_query_log(...)
└── service.py                 # orchestrate: normalise -> classify -> SQL -> render -> log

apps/api/tests/
├── fixtures/
│   └── agent_gold_set.yaml
├── test_agent_classifier_gold_set.py
├── test_agent_evidence_required.py
├── test_agent_query_log_persistence.py
└── test_agent_response_latency.py
```

### 3.2 Contract: `classifier.classify`

```python
# apps/api/app/agents/classifier.py — signature only, no implementation here

from dataclasses import dataclass
from typing import Literal

PersonaCode = Literal["dispatcher_analyst", "market_analyst", "energy_advisor", "battery_coach"]

@dataclass(frozen=True)
class ClassifyResult:
    intent: str            # one of the 12 intent codes; or "unknown_intent"
    confidence: float      # 0.0 .. 1.0
    matched_pattern: str   # the regex (or "FALLBACK") that won, for audit log
    normalised_text: str   # post-lexicon token stream, for cache key

def classify(text: str, persona: PersonaCode) -> ClassifyResult: ...
```

**Mechanism (per ARCH §7.1, locked):**
1. **Normalise:** casefold → strip diacritics with NFKD → drop Ukrainian stopwords (`та, і, або, з, по, на, в, у, для, чи, як, що, це, той, ця, ці, цей`) → split on `[\s\-,?!.:;]+`.
2. **Lexicon expand:** map each token through a `dict[str, str]` of synonym groups (e.g., `прогноз|прогнозу|прогнозом|прогнозі|forecast` → token `FORECAST_VERB`; `батарея|батареї|акумулятор|узе|bess|battery` → `BATTERY_NOUN`). The lexicon lives in `normalise.py` as one module-level dict, ~80 entries.
3. **Pattern table:** a Python list of `(priority:int, pattern:re.Pattern, intent:str, persona_whitelist:set[str], confidence_baseline:float)`. Evaluated in descending priority. First match wins.
4. **Persona filter:** if matched intent's `persona_whitelist` does not include the calling persona, demote to `unknown_intent`. The pattern table itself does NOT short-circuit on persona — this keeps the table independent of the persona registry and easier to test.
5. **Fallback:** if no pattern matches, return `ClassifyResult("unknown_intent", 0.0, "FALLBACK", normalised_text)`.

**Confidence baseline rules:**
- Exact phrase match (e.g., `^коли наступний небаланс\??$` after normalisation): 0.95
- Pattern with all required keyword groups present in any order: 0.85
- Pattern with one required keyword group + one optional: 0.70
- Persona-mismatch demotion to `unknown_intent`: 0.0

Gold-set asserts the classifier returns the expected intent AND confidence ≥ 0.7 (per ARCH §7.2 "expected confidence ≥ 0.7").

### 3.3 Contract: intent module

Each `apps/api/app/agents/intents/<intent>.py` exports exactly three callables and one metadata dict:

```python
# Example: apps/api/app/agents/intents/next_imbalance_window.py — contract only

INTENT_META = {
    "code": "next_imbalance_window",
    "personas": {"dispatcher_analyst", "market_analyst"},
    "evidence_tables": ["market.br_settlements"],
    "patterns": [
        # (priority, regex, confidence_baseline)
        (90, r"коли\s+наступн\w+\s+небаланс", 0.95),
        (80, r"наступн\w+\s+небаланс", 0.85),
        (70, r"небаланс\w*\s+(сьогодні|завтра|вікно)", 0.80),
    ],
    "services_acceptance": "BRIEF §11.15 (intent family #2 for producer surface)",
}

async def fetch_slots(session, *, tenant_id, persona, now, context) -> dict:
    """
    Returns the slot dict for template rendering.
    MUST execute the parameterised SQL from INTENT_META and return a serialisable dict.
    MUST attach `_evidence` key containing list[dict] for evidence[] field of response.
    """
    ...

async def render(slots: dict, persona: str) -> str:
    """
    Render apps/api/app/agents/templates/{intent}__{persona}.j2 with slots.
    """
    ...
```

The orchestrator in `service.py` calls `classify` → looks up `INTENTS[result.intent]` → `await fetch_slots(...)` → `await render(...)` → `audit.write_query_log(...)`.

### 3.4 Contract: persona module

```python
# apps/api/app/agents/personas/dispatcher_analyst.py — contract only

PERSONA = {
    "code": "dispatcher_analyst",
    "display_name": "Диспетчерський аналітик",
    "greeting": "Я — Диспетчерський аналітик. Допоможу з виробництвом, диспетчеризацією, прогнозами.",
    "voice": "formal",          # 'formal' | 'coach' | 'peer'
    "allowed_intents": [
        "today_production", "next_imbalance_window", "curtailment_today",
        "forecast_accuracy_today", "asset_status_overview", "generate_report_today",
    ],
    "default_url": "/producer/",
    "fallback_sample_questions": [
        "що сьогодні з виробництвом?",
        "коли наступний небаланс?",
        "чи були обмеження сьогодні?",
        "яка точність прогнозу сьогодні?",
        "покажи стан активів",
    ],
}
```

### 3.5 Contract: `service.handle_query` (top-level orchestrator)

The FastAPI handler that Backend lead writes calls **only** `await service.handle_query(...)` and serialises the returned object. This keeps the agent code testable without spinning up Starlette.

```python
# apps/api/app/agents/service.py — signature only

@dataclass(frozen=True)
class AgentResponse:
    intent: str
    confidence: float
    answer: str                   # Ukrainian rendered text, must contain ≥ 1 citation phrase
    evidence: list[dict]          # see §3.6 evidence shape
    persona: str
    duration_ms: int

async def handle_query(
    session,                      # AsyncSession, RLS already applied by Backend middleware
    *,
    tenant_id: UUID,
    persona: PersonaCode,
    user_text: str,
    context: dict | None = None,  # e.g. {"current_url": "/producer/rynok"}
    now: datetime | None = None,  # injected for deterministic tests
) -> AgentResponse: ...
```

### 3.6 Evidence shape (mirrors ARCH §4.8 response)

```python
{
    "table": "market.br_settlements",
    "row_id": 12345,
    "columns_used": ["our_imbalance_mwh", "price_short_uah_mwh"],
    "ui_link": "/producer/rynok?date=2026-05-24&hour=18",
}
```

Helper `evidence.build_evidence_for(rows, table, columns, ui_link_fn)` in `evidence.py` standardises this so each intent file stays small. The Ukrainian citation phrase inside `answer` is rendered by the template (NOT auto-appended) — this guarantees every persona phrases citations naturally.

---

## 4. The 12 intents — full specification

Below is the locked contract for all 12 intents. Each block is enough that an implementer can mechanically build the file. Patterns are written **after** lexicon expansion (i.e., applied to the normalised token stream after lexicon mapping — `прогнозу` and `прогноз` both already collapsed to `FORECAST_VERB`).

The intents extend ARCH §7.2 table verbatim. The 12-row count is locked.

### Intent 1 — `today_production`
- **Personas:** `dispatcher_analyst`, `energy_advisor`
- **Patterns (priority, after-lexicon-regex):**
  - `(90, r"\bщо\s+сьогодні\s+(з\s+)?(GENERATION_NOUN|PRODUCTION_NOUN)")` → 0.95
  - `(80, r"\b(GENERATION_NOUN|PRODUCTION_NOUN)\s+сьогодні")` → 0.85
  - `(70, r"\bяк\w*\s+(GENERATION_NOUN|PRODUCTION_NOUN)\s+сьогодні")` → 0.80
- **Lexicon keywords:** `GENERATION_NOUN = {генерац*, виробництв*, generation, production}`, `PRODUCTION_NOUN = {вихід*, output, отдача}`
- **SQL template:**
  ```sql
  SELECT
    SUM(t.active_power_mw) FILTER (WHERE a.asset_class IN ('СЕС','ВЕС','ГПУ'))
      AS produced_mwh_today,
    SUM(t.active_power_mw) FILTER (WHERE t.active_power_mw > 0)
      AS injected_mwh_today,
    COUNT(DISTINCT a.id) FILTER (WHERE t.availability_pct < 100)
      AS degraded_asset_count,
    MAX(t.interval_start) AS latest_telemetry_at
  FROM dispatch.telemetry t
  JOIN core.assets a ON a.id = t.asset_id
  WHERE t.tenant_id = $1
    AND t.date = $2     -- date(now() AT TIME ZONE 'Europe/Kyiv')
  ```
- **Template slot list:** `produced_mwh_today`, `injected_mwh_today`, `degraded_asset_count`, `date_ua` (formatted DD.MM.YYYY), `evidence[0].table`
- **Citation phrase (template-baked):** `На основі телеметрії за {{ date_ua }}.`
- **Acceptance link:** services S1 (intent #1 for dispatcher), BRIEF §11.15.

### Intent 2 — `next_imbalance_window`
- **Personas:** `dispatcher_analyst`, `market_analyst`
- **Patterns:**
  - `(90, r"\bколи\s+наступн\w+\s+небаланс")` → 0.95
  - `(80, r"\bнаступн\w+\s+небаланс")` → 0.85
  - `(70, r"\bнебаланс\w*\s+(сьогодні|завтра|вікно)")` → 0.80
- **SQL template:**
  ```sql
  SELECT
    s.date, s.hour, s.our_imbalance_mwh, s.price_short_uah_mwh, s.price_long_uah_mwh,
    s.system_direction, s.id
  FROM market.br_settlements s
  WHERE s.tenant_id = $1
    AND s.interval_start >= $2          -- now()
    AND ABS(s.our_imbalance_mwh) > 0.5
  ORDER BY s.interval_start ASC
  LIMIT 1;
  ```
- **Slots:** `date_ua`, `hour_start`, `hour_end` (= hour), `imbalance_mwh`, `price_short_uah_mwh`, `system_direction`, `asset_name` (NULL allowed — explain when null)
- **Citation phrase:** `Дані БР, рядок #{{ evidence[0].row_id }} за {{ date_ua }}.`
- **Template example (formal, dispatcher):** see ARCH §7.4 — already locked verbatim.
- **Acceptance link:** S1, S4.

### Intent 3 — `arbitrage_window_today`
- **Personas:** `market_analyst`, `battery_coach`
- **Patterns:**
  - `(90, r"\bколи\s+найкращ\w*\s+(вікно\s+)?арбітраж\w*")` → 0.95
  - `(80, r"\bарбітраж\w*\s+(сьогодні|вікно|можлив\w*)")` → 0.85
  - `(70, r"\bкупити\s+дешев\w+\s+продати\s+дорог\w+")` → 0.80
- **SQL template:**
  ```sql
  WITH today AS (
    SELECT hour, price_uah_mwh
    FROM market.rdn_prices
    WHERE tenant_id = $1 AND date = $2
  )
  SELECT
    (SELECT hour FROM today ORDER BY price_uah_mwh ASC LIMIT 1)  AS cheap_hour,
    (SELECT price_uah_mwh FROM today ORDER BY price_uah_mwh ASC LIMIT 1) AS cheap_price,
    (SELECT hour FROM today ORDER BY price_uah_mwh DESC LIMIT 1) AS peak_hour,
    (SELECT price_uah_mwh FROM today ORDER BY price_uah_mwh DESC LIMIT 1) AS peak_price;
  ```
- **Slots:** `cheap_hour`, `peak_hour`, `spread_uah`, `expected_uplift_uah` (= spread × bess_capacity, see BESS join below), `date_ua`
- **Citation:** `На основі даних РДН за {{ date_ua }}.`

### Intent 4 — `charge_battery_when`
- **Personas:** `battery_coach`, `energy_advisor`
- **Patterns:**
  - `(90, r"\bколи\s+зарядж\w*\s+BATTERY_NOUN")` → 0.95
  - `(80, r"\bзарядж\w+\s+BATTERY_NOUN")` → 0.85
  - `(70, r"\bкращ\w*\s+(години|час)\s+зарядк\w*")` → 0.80
- **SQL template:** join cheapest 3 hours of today's `market.rdn_prices` × `core.assets` where `asset_class='УЗЕ'`. Return per-asset recommendation row.
- **Slots:** `asset_name`, `recommended_charge_hours` (list[int]), `cheap_price`, `current_soc_pct`, `date_ua`
- **Citation:** `Рекомендація на основі РДН за {{ date_ua }} та поточного SOC телеметрії.`

### Intent 5 — `deep_discharge_ok_today`
- **Personas:** `battery_coach`
- **Patterns:**
  - `(90, r"\bглибок\w+\s+розряд\w*\s+(сьогодні|підходить)")` → 0.95
  - `(80, r"\bможна\s+глибок\w+\s+розряд")` → 0.85
- **SQL template:** check (a) peak vs trough spread today ≥ threshold, (b) battery `cumulative_cycles` < degradation budget, (c) `capacity_fade_pct` < 15.
- **Slots:** `decision` ("так" / "ні" / "обережно"), `spread_uah`, `cycles_used_today`, `recommended_dod_pct`
- **Citation:** `На основі РДН за {{ date_ua }} та телеметрії БСЕ.`

### Intent 6 — `top_revenue_yesterday`
- **Personas:** `market_analyst`
- **Patterns:**
  - `(90, r"\bхто\s+приніс\s+найбільш\w*\s+доход\w*\s+вчора")` → 0.95
  - `(80, r"\bнайбільш\w*\s+доход\w*\s+вчора")` → 0.85
  - `(70, r"\bтоп\s+(активів|asset)\s+вчора")` → 0.80
- **SQL template:**
  ```sql
  SELECT a.display_name, k.grn_earned_uah, k.asset_id
  FROM ems.kpi_daily k JOIN core.assets a ON a.id = k.asset_id
  WHERE k.tenant_id = $1 AND k.date = $2          -- yesterday
  ORDER BY k.grn_earned_uah DESC LIMIT 3;
  ```
- **Slots:** `top_assets` (list of three rows), `total_uah`, `date_ua`
- **Citation:** `За даними KPI на {{ date_ua }}.`

### Intent 7 — `curtailment_today`
- **Personas:** `dispatcher_analyst`
- **Patterns:**
  - `(90, r"\bчи\s+бул\w*\s+обмеж\w+\s+сьогодні")` → 0.95
  - `(80, r"\bcurtailment\w*\s+(today|сьогодні)")` → 0.85
  - `(70, r"\bобмеж\w*\s+тсо")` → 0.80
- **SQL template:**
  ```sql
  SELECT a.display_name, COUNT(*) AS hours_curtailed,
         SUM(GREATEST(0, COALESCE((t.extras->>'curtailment_cap_mw')::numeric, 0)
             - t.active_power_mw)) AS lost_mwh
  FROM dispatch.telemetry t JOIN core.assets a ON a.id = t.asset_id
  WHERE t.tenant_id = $1 AND t.date = $2
    AND t.status = 'curtailed_by_TSO'
  GROUP BY a.display_name;
  ```
- **Slots:** `events` (list), `total_hours`, `total_lost_mwh`, `date_ua`. If empty list → render "обмежень не зафіксовано".
- **Citation:** `Дані телеметрії за {{ date_ua }}.`

### Intent 8 — `forecast_accuracy_today`
- **Personas:** `dispatcher_analyst`, `energy_advisor`
- **Patterns:**
  - `(90, r"\bяк\w*\s+точн\w+\s+FORECAST_VERB\s+сьогодні")` → 0.95
  - `(80, r"\bmape\s+сьогодні")` → 0.85
  - `(70, r"\bпохибк\w+\s+FORECAST_VERB")` → 0.80
- **SQL template:** join `ems.forecasts` × `ems.forecast_actuals` on `(tenant_id, asset_id, forecast_kind, date, hour)`; compute `MAPE = AVG(|forecast - actual| / NULLIF(actual,0)) * 100` for today.
- **Slots:** `mape_pct`, `worst_hour`, `worst_asset_name`, `date_ua`
- **Citation:** `На основі ems.forecasts vs ems.forecast_actuals за {{ date_ua }}.`

### Intent 9 — `next_settlement_due`
- **Personas:** `market_analyst`
- **Patterns:**
  - `(90, r"\bколи\s+наступн\w+\s+(закритт\w+|розрах\w+)")` → 0.95
  - `(80, r"\bsettlement\s+(due|date|when)")` → 0.85
- **SQL template:** look up next monthly settlement boundary from `regulatory.settlement_periods` (DB schema §3.6) and aggregate currently unsettled `market.bids` value.
- **Slots:** `period_label` (e.g. "Травень 2026"), `cutoff_date_ua`, `pending_uah`
- **Citation:** `За даними regulatory.settlement_periods на {{ date_ua }}.`

### Intent 10 — `flex_savings_potential`
- **Personas:** `energy_advisor`
- **Patterns:**
  - `(90, r"\bскільки\s+можна\s+зекономит\w*\s+(через\s+)?гнучкіст\w*")` → 0.95
  - `(80, r"\b(flex|гнучкіст\w*)\s+(savings|економі\w+)")` → 0.85
- **SQL template:** compute potential savings = sum over today's hourly load × `(peak_price - cheap_price)` for the AktSpozh asset attached to this tenant; uses `dispatch.telemetry` + `market.rdn_prices`.
- **Slots:** `potential_uah_per_day`, `potential_uah_per_month`, `peak_hours_list`, `date_ua`
- **Citation:** `На основі телеметрії навантаження та РДН за {{ date_ua }}.`

### Intent 11 — `asset_status_overview`
- **Personas:** `dispatcher_analyst`, `market_analyst`, `energy_advisor`, `battery_coach` (all four)
- **Patterns:**
  - `(90, r"\bпокажи\s+стан\s+активі\w*")` → 0.95
  - `(80, r"\bстан\s+(порт\w*|активі\w*|fleet)")` → 0.85
  - `(70, r"\b(огляд|overview)\s+портфел\w*")` → 0.80
- **SQL template:** group `core.assets` join latest `dispatch.telemetry` row per asset by status; return counts and degraded list.
- **Slots:** `total_count`, `online_count`, `maintenance_count`, `tripped_count`, `degraded_list`, `now_ua`
- **Citation:** `Стан на {{ now_ua }}.`

### Intent 12 — `generate_report_today`
- **Personas:** all four
- **Patterns:**
  - `(90, r"\bсформуй\s+звіт\s+(за\s+сьогодні|today)")` → 0.95
  - `(80, r"\b(згенеруй|створи)\s+звіт")` → 0.85
- **SQL template:** read `ems.kpi_daily` for tenant for today, render a 4-line summary AND set `evidence[0].ui_link = "/producer/zvity?date={today}"` so the operator can open the full report. Does NOT generate a PDF (out of scope; report screens already exist per `/zvity`).
- **Slots:** `grn_saved_uah`, `grn_earned_uah`, `imbalance_mwh`, `co2_avoided_tn`, `date_ua`
- **Citation:** `KPI зведення за {{ date_ua }} — повний звіт за посиланням.`

### Intent 13 (fallback only) — `unknown_intent`
- **Personas:** all
- **Pattern:** none — used when classifier finds no match OR persona-mismatch demotion
- **SQL:** none
- **Template:** lists `personas[persona].fallback_sample_questions` (5 items)
- **Returns:** confidence 0.0, evidence []

### 3.7 Coverage matrix (each persona ≥ 3 intents — services S1)

| Persona | Intents | Count |
|---|---|---|
| `dispatcher_analyst` | today_production, next_imbalance_window, curtailment_today, forecast_accuracy_today, asset_status_overview, generate_report_today | **6** |
| `market_analyst` | next_imbalance_window, arbitrage_window_today, top_revenue_yesterday, next_settlement_due, asset_status_overview, generate_report_today | **6** |
| `energy_advisor` | today_production, charge_battery_when, forecast_accuracy_today, flex_savings_potential, asset_status_overview, generate_report_today | **6** |
| `battery_coach` | arbitrage_window_today, charge_battery_when, deep_discharge_ok_today, asset_status_overview, generate_report_today | **5** |

All four ≥ 3 → S1 satisfied.

---

## 5. Template tree

One Jinja2 file per `(intent, persona)` cell where the persona is allowed for that intent (per §3.7 matrix above): **23 templates total** plus one shared `unknown_intent__shared.j2`. Template directives:

- **Voice differentiation per persona** is the entire point of separate template files. Persona `voice` field controls register: `formal` (vy-form, dispatcher_analyst, market_analyst), `coach` (encouraging second person, battery_coach, energy_advisor — `ти` allowed), `peer` reserved for future.
- **Citation phrase is mandatory** — every template must include at least one `{{ date_ua }}`, `{{ now_ua }}`, or explicit `{{ evidence[0].table }}` reference inside Ukrainian prose.
- **Numbers** are formatted via Jinja filter `uk_num` (provided by Backend; renders `1234.5` as `1 234,5`) — never inline format strings.
- **Empty result** path is mandatory in every template (every intent can return zero rows on some days — e.g., `curtailment_today` when no curtailment happened). Empty branch reads as a positive statement, not an error.

Example skeleton (`next_imbalance_window__market_analyst.j2`):

```jinja
{% if event %}
Найближче вікно небалансу очікується {{ event.date_ua }} о {{ event.hour_start }}:00.
Прогнозований небаланс ≈ {{ event.imbalance_mwh | uk_num }} МВт·год;
ціна дефіциту {{ event.price_short_uah_mwh | uk_num }} грн/МВт·год.
Рекомендація: переглянути позицію по {{ event.asset_name or "портфелю" }} на ВДР.
(За даними БР, період {{ event.date_ua }} / година {{ event.hour_start }}.)
{% else %}
На горизонті 24 годин значущих небалансів не прогнозується (за даними БР на {{ now_ua }}).
{% endif %}
```

---

## 6. The 30-question gold-set

Lives at `apps/api/tests/fixtures/agent_gold_set.yaml`. Format (one YAML doc, list of dicts):

```yaml
- id: g01
  question_uk: "що сьогодні з виробництвом?"
  persona: dispatcher_analyst
  expected_intent: today_production
  expected_min_confidence: 0.85
  expected_slots_present: [produced_mwh_today, date_ua]
  expected_evidence_table: dispatch.telemetry

- id: g02
  question_uk: "як справи з генерацією сьогодні"
  persona: dispatcher_analyst
  expected_intent: today_production
  expected_min_confidence: 0.70
  expected_slots_present: [produced_mwh_today, date_ua]
  expected_evidence_table: dispatch.telemetry

# ...30 total
```

Locked composition (covers each persona ≥ 7 questions, off-topic ≥ 2 per persona):

| Range | Persona | Coverage |
|---|---|---|
| g01–g08 | `dispatcher_analyst` | 2× today_production (paraphrase), 2× next_imbalance_window, 1× curtailment_today, 1× forecast_accuracy_today, 1× asset_status_overview, 1× off-topic ("яка погода в Києві?") |
| g09–g16 | `market_analyst` | 2× arbitrage_window_today, 2× next_imbalance_window, 1× top_revenue_yesterday, 1× next_settlement_due, 1× asset_status_overview, 1× off-topic ("розкажи анекдот") |
| g17–g23 | `energy_advisor` | 2× today_production, 1× charge_battery_when, 2× flex_savings_potential, 1× forecast_accuracy_today, 1× off-topic ("привіт, як справи?") |
| g24–g30 | `battery_coach` | 2× charge_battery_when, 1× deep_discharge_ok_today, 2× arbitrage_window_today, 1× asset_status_overview, 1× off-topic ("яка ціна нафти?") |

Off-topic items expect `expected_intent: unknown_intent` and `expected_min_confidence: 0.0`.

CI test contract (`test_agent_classifier_gold_set.py`):
1. Load the YAML.
2. For each row, call `service.handle_query(...)` with a frozen `now=2026-05-23T10:00:00+03:00` and a fixed test-tenant fixture (loaded from synth dataset).
3. Assert `result.intent == expected_intent`, `result.confidence >= expected_min_confidence`, every key in `expected_slots_present` appears in the rendered answer text OR the evidence rows, and `result.evidence[0].table == expected_evidence_table` when set.
4. Failure on **any** row blocks merge (per `ARCHITECTURE.md` §10.7 CI gate summary, F11 mitigation).

---

## 7. Caching, latency, audit

- **`agents.response_cache`** (ARCH §3.7.2) — keyed `SHA256(tenant_id || persona || normalised_text)`. TTL 300 s. Use it as a write-through cache in `service.handle_query`: check cache before SQL fetch; on miss, run SQL → render → store. Cache stores `response_text` + `evidence` JSONB. Cache hit short-circuits the SQL round-trip but still INSERTs a row in `agents.query_log` (with `duration_ms` reflecting cache-hit speed) so audit stays complete.
- **`agents.query_log`** insert is fire-and-forget within the request (await but don't surface errors — log to structlog `agent_audit_failed`). Schema per ARCH §3.7.1: `tenant_id, persona, user_text, classified_intent, confidence, response_text, evidence, duration_ms`.
- **Latency budget (services S3):** classification ≤ 5 ms, SQL fetch ≤ 60 ms p95 on synthetic data, template render ≤ 5 ms, log write ≤ 30 ms. Total p95 < 100 ms (own checklist target); 500 ms is the end-to-end HTTP budget that includes Caddy + Cloudflare round-trip.
- **Concurrency:** the handler is fully async; uses the existing RLS-scoped session injected by Backend middleware (`request.state.db`).

---

## 8. Pre-flight check (mandatory before writing code)

Before starting, the implementing agent confirms — in writing inside the first commit message OR in `difficulties_log.md` — that all four answers are "yes":

1. **Goal clear?** — Implementing 4 personas × shared classifier × 12 deterministic intents over the synthetic Postgres dataset; surfaced via `POST /api/v1/agents/{persona}/query`; backed by Jinja2 templates. *Yes / no?*
2. **Criteria measurable?** — S1–S8 in §1 are each binary checks runnable from CI (gold-set test, evidence-test, latency-test, grep gate). *Yes / no?*
3. **Tools available?** — Python 3.11, FastAPI router stub from Backend lead, synthetic dataset in Postgres (Phase 4.2 must be DONE), Jinja2, pytest, pymorphy3 optional. Verify `apps/api/pyproject.toml` includes Jinja2; verify `apps/synth/` has been run at least once locally (`docker compose run synth`). *Yes / no?*
4. **Plan complete?** — §3 module tree, §4 intent table, §5 templates, §6 gold-set, §7 audit/cache fully specified; no open architectural decisions remain. *Yes / no?*

If any answer is "no", STOP and either escalate to the orchestrator OR log to `difficulties_log.md` under heading `## YYYY-MM-DD — AI agents pre-flight blocker`.

---

## 9. Branching protocol (what to do when stuck)

Per `~/.claude/CLAUDE.md` global rules + project convention.

**Trigger:** any single sub-task exceeds 2× expected time, blocks on missing data, or requires a deviation from this spec.

**Steps:**
1. Open `difficulties_log.md` (project root). Append a new entry using the format already established in that file:
   ```
   ## 2026-05-XX HH:MM — short title
   **Stage:** Phase 4.8 — AI agents
   **Obstacle:** what is blocking
   **Branch taken:** alternative attempted
   **Returned to main path:** yes/no, when
   **Reusable lesson:** one line
   ```
2. Try **one** alternative path. Examples of allowed branches without re-escalating:
   - A regex pattern fails on an inflected form → add the form to the lexicon, do NOT add a new pattern row (keep the pattern table small).
   - A SQL template returns NULL where the template assumes non-NULL → handle the NULL in the template's `{% if %}` branch, NOT in Python.
   - Synthetic data is missing rows for an intent (e.g., zero curtailment events in the 30-day window) → log to difficulties_log AND adjust the template's empty-result branch to read as positive ("обмежень не зафіксовано"). Do NOT request a synth-data change unilaterally; flag it for DB lead.
3. If the alternative also fails, RETURN to the main path: skip the failing intent or persona-cell, mark it `TODO` in the relevant Python file with a link to the difficulties_log entry, and proceed with the next intent. **Never block the whole work-unit on one intent.**
4. Before declaring done, ensure ≤ 2 TODOs remain across all 12 intents AND no TODO sits inside a gold-set-covered combination.

---

## 10. Hand-off interface to Backend lead

Backend lead (per ARCH §14.2) writes `apps/api/app/agents/routers/text.py` with the FastAPI route. The route is **5 lines** and only does:

```python
@router.post("/api/v1/agents/{persona}/query")
async def query(persona: PersonaCode, body: QueryBody,
                session: AsyncSession = Depends(get_rls_session),
                tenant_id: UUID = Depends(get_current_tenant_id)) -> AgentResponse:
    return await service.handle_query(session, tenant_id=tenant_id, persona=persona,
                                      user_text=body.text, context=body.context)
```

What the Backend lead MUST guarantee for the agents lead (acceptance gate for this work-unit to start):
- `apps/synth/` has been run (Phase 4.2 done) — there is data in `dispatch.telemetry`, `market.rdn_prices`, `market.br_settlements`, `ems.kpi_daily`, `core.assets` for tenants `producer-1`, `ci-1`, `storage-1`.
- The RLS-scoped session dependency is wired and sets `app.tenant_id` on the connection.
- The route handler stub exists (returns 501 acceptable initially) so the agents lead can write tests against the contract.

---

## 11. Self-review checklist (the AI agents lead runs this before declaring done)

Tick every line. Anything unchecked must be in `difficulties_log.md` with a justification.

- [ ] All 12 intent files exist and export `INTENT_META`, `fetch_slots`, `render`.
- [ ] All 4 persona files exist and list ≥ 3 allowed_intents each.
- [ ] All 23 `(intent, persona)` templates exist + 1 `unknown_intent__shared.j2`.
- [ ] Lexicon in `normalise.py` has ≥ 8 inflection variants for each of: прогноз, небаланс, виробництво, батарея, активи, обмеження, доход, точність.
- [ ] Classifier pattern table is sorted by descending priority; ties broken deterministically.
- [ ] `service.handle_query` reads cache before SQL; writes cache + log on miss; writes log even on hit.
- [ ] Every template contains at least one citation phrase referencing a date / time / table.
- [ ] Grep gate `grep -nE '[0-9]{2,}' apps/api/app/agents/templates/` returns zero lines (or only whitelisted tokens).
- [ ] `apps/api/tests/fixtures/agent_gold_set.yaml` has exactly 30 entries; each persona covered ≥ 7 times; each persona has ≥ 2 off-topic items.
- [ ] `pytest apps/api/tests/test_agent_classifier_gold_set.py` exits 0.
- [ ] `pytest apps/api/tests/test_agent_evidence_required.py` exits 0 (every gold-set non-fallback response has `len(evidence) >= 1`).
- [ ] `pytest apps/api/tests/test_agent_response_latency.py` shows p95 < 100 ms on local Postgres.
- [ ] No dependency added to `pyproject.toml` beyond Jinja2 (already there) and optional `pymorphy3`+`pymorphy3-dicts-uk`.
- [ ] Import-linter contract `agents-no-llm` configured to forbid `openai`, `anthropic`, `litellm`, `sentence_transformers`, `transformers`, `torch`, `langchain` imports from `apps/api/app/agents/**`.
- [ ] `agents.query_log` rows appear after a manual `curl POST /api/v1/agents/dispatcher_analyst/query` against staging.
- [ ] PROGRESS.md updated with stage transition entry.

---

## 12. Done definition (binary)

This work-unit is **done** when, on a fresh checkout against a freshly seeded synthetic DB:

1. `pytest apps/api/tests/test_agent_*.py` exits 0.
2. `curl -X POST -H 'X-Tenant-Id: <producer-1-uuid>' -H 'Content-Type: application/json' -d '{"text":"коли наступний небаланс?"}' https://api.gecko.radai-1984.dev/api/v1/agents/dispatcher_analyst/query` returns a JSON envelope matching ARCH §4.8.
3. The same curl on the other 3 personas + 11 other intents returns valid envelopes.
4. `SELECT count(*) FROM agents.query_log WHERE tenant_id = '<producer-1-uuid>'` is > 0.
5. ARCH §14.4 checklist (8 boxes) all ticked in the work-unit's commit description.

---

## Appendix A — Pattern-vs-lexicon design note (justification, not contract)

The architect's choice (ARCH §7.1) was **pattern table + lexicon**, not embeddings. The reason this works for 12 intents over Ukrainian is:

- The 12 intent surfaces are operational questions a dispatcher / market analyst / battery operator already asks every day — they cluster around 30–60 high-frequency stems (`небаланс`, `арбітраж`, `прогноз`, `виробництво`, `розряд`, `заряд`, `доход`, `обмеж*`, `точн*`, `звіт`).
- Ukrainian inflection is regular enough that a lexicon with 8 variants per stem covers > 95% of realistic phrasing. The remaining 5% lands in `unknown_intent` and the safe-fallback message — which is exactly the spec.
- Embeddings would buy paraphrase robustness at the cost of: ~80 MB model weights, a torch dependency, GPU jitter on cold start, prompt-injection surface, and zero gain on the 30-question gold-set (already deterministic).
- Pymorphy3 sits between these two — adding it later is a one-flag flip if and when the gold-set scales past 100 questions.

This appendix is not a decision; it is the justification the implementing agent will reuse when defending the architecture in code review.
