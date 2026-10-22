# InsideMatch: Master Build Prompt for Claude Code

> Paste everything below this line into Claude Code, run from the root of the (empty or near-empty) `insidematch` repository.

---

You are the lead engineer building **InsideMatch**, our entry to the **Microsoft + Premier League "Inside the Game" Developer Hackathon**. Build a working, demo-ready, public-repo-ready application from scratch by following this specification. It is authoritative. Where it differs from `docs/PRD.md`, **this prompt wins**. Use the PRD for product context, metric definitions, and wording.

Hard deadline: submission closes **Oct 27, 2026, 11:59 pm PT**. The team's internal target is **Oct 27, 6:00 pm PT**. The live demo must stay reachable until **Nov 10, 2026** (end of judging). Optimize for a reliable, polished, honest MVP over breadth.

---

## 0. How you must work

Follow these rules for the whole build:

1. **Inspect before changing.** List the repo contents first. Read `docs/PRD.md` completely if it exists, and read any files in `data/`. If the PRD is missing, continue from this prompt, which is self-sufficient, and note the missing PRD in your plan.
2. **Write a short plan** in `docs/IMPLEMENTATION_PLAN.md`: phases, assumptions, and blockers, such as missing Azure credentials. Keep it to one page and update it as phases complete.
3. **Make reasonable assumptions** instead of stopping for minor questions. Record each one in the plan under "Assumptions". Stop and ask only for decisions that need credentials, cost money, or are irreversible.
4. **Build in the phases of section 14, in order.** The app must run locally (`make dev`) and tests must pass (`make test`) at the end of every phase. Commit at the end of each phase with a clear message such as `phase 3: deterministic stats engine + tests`.
5. **Run tests after every meaningful change.** Fix failures rather than documenting them. Never skip, weaken, or delete a test to make it pass.
6. **No placeholder functionality where a working implementation is feasible.** A mock is allowed only where a cloud service is involved, and it must be clearly labeled as a mock in code, UI, and README.
7. **Keep it explainable.** A hackathon team must be able to walk a judge through any file. Prefer plain functions and small modules over frameworks, metaclasses, DI containers, or deep inheritance. No enterprise ceremony.
8. **Separate mock/local from real cloud integrations** everywhere: config flags, logs (`provider=mock` vs `provider=foundry`), UI badges, and the README.
9. **Never commit secrets.** Use `.env` (git-ignored) and `.env.example`. Scan before every commit to a public repo.
10. **Finish with the summary** described in section 20.

---

## 1. Product objective

InsideMatch is a **live AI football companion**. It turns a stream of structured, synthetic, football-realistic match events into understandable, explainable, personalized match intelligence for fans, analysts, and broadcasters.

It must:

- **Ingest** synthetic football match events as a simulated real-time stream.
- **Interpret** them into deterministic statistics, rolling-window metrics, detected patterns, and key moments, all computed by code.
- **Explain** why a moment matters, using **Microsoft Foundry** models given only verified, structured facts.
- **Render** it in a polished live-match interface: clock, score, pitch view, live stats, timeline, insight cards, and recap.
- **Personalize** the explanation per viewer type (Casual and Tactical in the MVP), keeping the facts identical across modes.
- Generate **live insights**, **key-moment explanations**, and **half-time and full-time recaps**.
- Use Microsoft and Azure technologies **meaningfully**: Foundry for generation, Fabric as the real-time event layer (behind an interface), and Azure Container Apps and Azure Database for PostgreSQL for hosting and storage.

The hackathon's required flow is **Ingest → Interpret → Explain → Render → Personalize**. Name these five stages explicitly in the code layout, the architecture diagram, and the README.

**Honesty rule:** this is a *synthetic real-time football event simulation*. Never claim live Premier League data, video understanding, statistically validated tactical models, or proven production-scale throughput. The UI footer and README must say "Synthetic match data. Clubs and players are fictional."

**Fictional data rule:** use only fictional clubs and players. The default match is **Northbridge FC (`NBR`) vs Riverside Athletic (`RVA`)**. Never use real club names, crests, player names, or Premier League marks in data, UI, screenshots, or the video.

---

## 2. MVP scope (mandatory for the first working version)

Every item below must work end-to-end locally in mock mode, and with real Foundry when credentials exist.

| # | Capability | Notes |
|---|---|---|
| M1 | Synthetic event dataset | Seeded generator plus one committed demo match (`demo_01`) |
| M2 | Simulated real-time playback | Start, pause, resume, reset, speed (1x to 60x), deterministic |
| M3 | Live match clock and score | Derived from replayed events only |
| M4 | Event timeline | Goals, shots, cards, substitutions, detected moments |
| M5 | Live statistics | Possession, shots, shots on target, passes, pass accuracy, final-third entries, high recoveries, xG (synthetic) |
| M6 | Rolling windows | Last 5 min, last 10 min, full match |
| M7 | Player statistics | Per-player passes, pass accuracy, shots, xG, recoveries, final-third entries, involvement |
| M8 | Pattern detectors (3) | Sustained pressure, momentum shift, high-press recovery sequence |
| M9 | Key-moment detection | Goal, big chance (xG ≥ 0.30), card, half-time, full-time |
| M10 | Foundry explanations | Grounded live insights and key-moment explanations |
| M11 | Viewer modes | **Casual** and **Tactical**, driven by mode config rather than duplicated logic |
| M12 | Insight cards | Headline, body, type, minute, supporting stats, evidence event IDs |
| M13 | Recaps | Half-time and full-time, generated only from events received so far |
| M14 | Backend APIs + SSE | Section 9 |
| M15 | Persistence | SQLite locally, Azure Database for PostgreSQL in the cloud |
| M16 | Graceful fallback | Mock or template output when Foundry or Fabric is unavailable; the UI never breaks |
| M17 | Polished responsive frontend | Presentation-ready from 1280 px desktop down to 390 px mobile |
| M18 | Deterministic demo mode | One click that reliably walks through the storyline in under 90 seconds |

**Stretch goals (not MVP; build only after section 19's MVP completion criteria pass, in this order):**

1. Additional viewer modes: **Broadcaster** (talking points plus an on-screen stat), **Club-focused**, **Player-focused**, **Fantasy-focused**.
2. **MCP server** exposing read-only match tools (`get_match_state`, `get_window_stats`, `get_events`, `get_player_stats`, `list_detections`) so GitHub Copilot Agent Mode or any MCP client can query a live match.
3. **Multi-agent workflow** with Microsoft Agent Framework: Analyst (gathers facts via tools), Narrator, and Personalizer, keeping the same grounding validator.
4. Multilingual output via Azure AI Translator, preserving names and numbers.
5. Fabric Real-Time Dashboard over the Eventhouse.

**Explicit non-goals:** computer vision, video recognition, player tracking, real or live Premier League data, speech or TTS, real broadcast integrations, user accounts, payments, and ML models trained for tactics.

---

## 3. Technology stack (use exactly this unless a blocker forces a change)

| Concern | Choice | Why |
|---|---|---|
| Frontend | **Next.js 14+ (App Router), TypeScript, Tailwind CSS** | Fast to build, polished UI, easy container deploy |
| Charts and pitch | Hand-written SVG components and small Tailwind bars; Recharts only if needed | No heavy viz dependency |
| Backend | **Python 3.12, FastAPI, Pydantic v2, Uvicorn** | Typed models, async, quick APIs |
| Real-time transport | **Server-Sent Events** (`sse-starlette`) | One-way server→client is all we need. Simpler than WebSockets, auto-reconnects in browsers, and proxy-friendly on Container Apps. Explain this choice in the README. |
| Analytics | Plain Python modules with pure, deterministic functions | Testable and explainable |
| AI | **Microsoft Foundry** model deployment (e.g. `gpt-4.1-mini` or `gpt-4o-mini`; deployment name from env), called via the official `openai` Python SDK against the Foundry project's Azure OpenAI-compatible endpoint, with structured JSON output | Grounded generation. Check the current Foundry docs for the exact endpoint/base URL format and API version before coding; do not guess. |
| Event layer | `EventSource` interface: `LocalSyntheticEventSource` (default) and `FabricEventSource` (Fabric Eventstream custom endpoint, Event Hubs-compatible, `azure-eventhub` SDK) | Fabric as the real-time data layer without making local dev fragile |
| Database | **SQLAlchemy 2.x** with **SQLite** locally and **Azure Database for PostgreSQL – Flexible Server** in Azure (`DATABASE_URL` switch), plus **Alembic** migrations | One ORM, two targets, simple |
| Package management | `uv` for Python, `pnpm` (or npm) for frontend | Reproducible |
| Quality | `ruff`, `mypy` (lenient), `pytest`, `pytest-asyncio`, `httpx`; ESLint, `tsc --noEmit`, Playwright smoke test | Required by the judging criteria |
| Hosting | **Azure Container Apps** (two apps: `api`, `web`), **Azure Container Registry**, **Log Analytics**, **Azure Database for PostgreSQL Flexible Server (Burstable B1ms)**, user-assigned **managed identity**; IaC in **Bicep** with **Azure Developer CLI (`azd`)** | Cloud native, minimal service count |
| Secrets | Container Apps secrets (Key Vault only if trivial to add) | Simplicity |
| CI | GitHub Actions: lint + tests for backend and frontend on every push; optional `azd deploy` workflow | Quality signal for judges |

Do **not** add AKS, Functions, Logic Apps, Cosmos DB, Redis, Service Bus, or Event Grid. They solve no requirement here.

The PRD mentions Cosmos DB and Vite. This prompt supersedes both with PostgreSQL and Next.js.

---

## 4. Non-negotiable rule: deterministic analytics vs AI

- **All statistics are computed by code** from structured events: possession, shots, shots on target, passes, pass accuracy, final-third entries, recoveries, high recoveries, xG sums, and player actions. **An LLM must never compute, estimate, or "fill in" a number.**
- The AI layer receives a **`FactPack`**: verified structured context built by code. It only turns facts into words.
- Every AI output passes a **deterministic grounding validator** (section 8.4) before it is shown. Every number and every team or player name in the text must exist in the FactPack or the match metadata. On failure, regenerate once with the violations listed. If it fails again, use the template fallback.
- Every insight stores the **event IDs** it cites, and the UI can show them ("Evidence").
- The AI only ever sees data up to the current replay clock, never future events.

Put this rule at the top of `CLAUDE.md` and of `backend/app/ai/README.md`.

---

## 5. Data: event schema and synthetic generator

### 5.1 Inspect first

Check `data/` and the repo for any official hackathon dataset. As of Oct 22, 2026 the official hackathon repo (`microsoft/insidethegamehackathon`) ships rules and resource playlists but **no dataset**. If an official dataset appears, write an adapter in `backend/app/events/adapters/` that maps its fields to our schema. **Do not invent fields it does not contain**; mark unsupported metrics as unavailable rather than fabricating them. Our own synthetic generator is the default source.

### 5.2 Event schema (`backend/app/models/events.py`, Pydantic v2; export JSON Schema to `data/schema/event.schema.json`)

| Field | Type | Notes |
|---|---|---|
| `match_id` | str | e.g. `demo_01` |
| `event_id` | str | Unique per match, e.g. `e00103` |
| `seq` | int | Strictly increasing |
| `period` | int | 1 or 2 |
| `match_second` | int | Seconds since kickoff, continuous across halves (2nd half starts at 2700 + 1st-half stoppage) |
| `minute`, `second` | int | Display clock, e.g. 68:41; derived but stored for convenience |
| `team_id` | str | `NBR` or `RVA` |
| `player_id` | str or null | e.g. `NBR_07`; null for team or match events |
| `event_type` | enum | `period_start`, `period_end`, `kickoff`, `pass`, `carry`, `shot`, `goal`, `tackle`, `interception`, `recovery`, `pressure`, `clearance`, `foul`, `card`, `out_of_play`, `substitution` |
| `outcome` | str or null | Pass: `complete`/`incomplete`; shot: `goal`/`saved`/`off_target`/`blocked`; tackle: `won`/`lost`; card: `yellow`/`red` |
| `x`, `y` | float or null | Pitch metres, x 0–105, y 0–68, **normalized so the acting team always attacks toward x = 105** |
| `end_x`, `end_y` | float or null | Pass and carry endpoints |
| `possession_team_id` | str or null | Team in control after this event |
| `possession_id` | int | Increments on every change of control |
| `recipient_id` | str or null | Pass receiver if complete |
| `shot_outcome` | str or null | Duplicate of outcome for shots, kept for schema clarity |
| `xg` | float or null | Shots only. **Synthetic xG** from a simple documented distance/angle formula, labeled "synthetic xG" everywhere |
| `under_pressure` | bool | Actor was pressured (a `pressure` event within 3 s and 10 m) |
| `in_play` | bool | False during stoppages |
| `related_event_ids` | list[str] | A goal links to its shot; a recovery links to the pressure that caused it |

**Match metadata** (`data/matches/demo_01.meta.json`): match id, competition label "Synthetic League", venue name (fictional), kickoff (ISO), seed, teams (id, name, short name, primary/secondary colour hex, formation), squads (player id, name, shirt number, position, starter flag), and the final score.

### 5.3 Synthetic generator (`backend/app/events/generator.py`, CLI: `python -m app.events.generator --seed 42 --match-id demo_01`)

- **Deterministic:** the same seed produces byte-identical JSONL.
- **Realistic flow:** possession chains of passes and carries with plausible coordinates and pass lengths. Turnovers come through tackles, interceptions, recoveries, and clearances. Pressure events precede some turnovers. Shots come from realistic zones, with xG from the formula. The generator also produces out-of-play gaps, both halves with stoppage time, 3 substitutions per team, and at least one yellow card.
- **Volume:** about 1,600 to 2,000 events.
- **Scripted storyline** so detectors and the demo are reliable (document it in `data/matches/demo_01.storyline.md`):
  - 23': RVA goal (1–0).
  - 40'–44': RVA high-press recovery sequence (≥ 3 high recoveries in 180 s).
  - 62'–70': NBR sustained pressure (in a 5-minute window: possession ≥ 65%, ≥ 3 shots, ≥ 6 final-third entries).
  - 69': NBR goal (1–1), linked to its shot.
  - ~78': momentum shift to RVA.
  - 86': RVA big chance (xG ≥ 0.30) saved.
  - Final score 1–1 (record it in meta).
- Outputs: `data/matches/demo_01.jsonl`, `demo_01.meta.json`, and `demo_01.expected_stats.json` (section 6.3).

### 5.4 Data-driven design

Nothing outside `generator.py` and `adapters/` may assume where events come from. Everything downstream consumes `Event` objects from an `EventSource` (section 7).

---

## 6. Statistics engine (`backend/app/analytics/`)

Pure functions. No I/O, no globals, no LLM. Each metric function returns the **value and the contributing event IDs**.

### 6.1 Modules and functions

```
analytics/
  definitions.py     # constants: pitch size, FINAL_THIRD_X = 70.0, HIGH_REGION_X = 70.0, windows
  possession.py      # possession_seconds(events, t0, t1) -> {team_id: seconds}; possession_pct(...)
  shots.py           # shots(events, team), shots_on_target(...), xg_total(...)
  passing.py         # passes_attempted, passes_completed, pass_accuracy (None if 0 attempts)
  territory.py       # final_third_entries(...), high_recoveries(...)
  players.py         # player_stats(events, player_id) and player_table(events, team)
  score.py           # score_at(events, t) -> {team_id: goals}
  windows.py         # window_stats(events, end_second, window_seconds) -> WindowStats for 300, 600 and full
  context.py         # recent_events(events, t, n), match_context(...) -> data for FactPack
  state.py           # MatchState: incremental ingestion, idempotent on duplicate event_id, reset()
```

### 6.2 Metric definitions (document in `docs/metrics.md`; tests enforce them)

- **Possession %:** the team's seconds of in-play control divided by total assigned in-play seconds in the window, times 100. Control spans from an event to the next event within the same `possession_id`. Out-of-play and unassigned time is excluded. Show "n/a" if the denominator is 0. *Worked example (put it in the tests): NBR 213 s and RVA 87 s gives NBR 71%, RVA 29%.*
- **Shots:** unique `shot` events. A `goal` linked to a shot is **not** a second shot.
- **Shots on target:** shots with `saved` or `goal`.
- **Pass accuracy:** completed ÷ attempted × 100, or `None` (displayed "n/a") when attempted = 0.
- **Final-third entry:** a `pass` (complete) or `carry` with `x < 70` and `end_x ≥ 70`. Events already inside the final third do not count.
- **High recovery:** `recovery`, `interception`, or a won `tackle` with `x ≥ 70`.
- **xG total:** sum of synthetic `xg` over shots.
- **Player involvement:** count of a player's recorded on-ball events. Never call it "touches".
- **Windows:** `last_5` = 300 s, `last_10` = 600 s, `full`. Windows end at the current replay clock.

### 6.3 Verification

- Hand-built fixtures (10–40 events each) with expected values computed by hand in the test docstring.
- `scripts/compute_expected_stats.py` is a deliberately simple, slow, independent implementation written from the definitions. It writes `demo_01.expected_stats.json` at 15', 45', 69', and 90'. A test asserts the fast engine equals it exactly.
- Tests also cover: duplicate events do not change totals; reset clears state; goals do not double-count; pass accuracy is None with no passes; the windows' boundaries are inclusive and exclusive as documented.

---

## 7. Event sources and the real-time simulator (`backend/app/events/`)

```python
class EventSource(Protocol):
    async def events(self, match_id: str) -> AsyncIterator[Event]: ...
```

- **`LocalSyntheticEventSource`** (default) reads `data/matches/{match_id}.jsonl`.
- **`FabricEventSource`** (enabled with `EVENT_SOURCE=fabric`) consumes from a **Microsoft Fabric Eventstream custom endpoint** (Event Hubs-compatible) using `azure-eventhub`. A companion **`FabricPublisher`** (`scripts/publish_to_fabric.py` and an optional hook in the simulator) pushes replayed events into the Eventstream. In Fabric, the Eventstream routes to (a) an **Eventhouse/KQL database** for real-time analytics and (b) a custom-endpoint destination that `FabricEventSource` reads. Document every Fabric click and setting in `docs/setup-fabric.md`. If Fabric env vars are absent, log one clear warning and fall back to local.

**Simulator** (`backend/app/events/simulator.py`), one per match:

- Pulls events from the configured `EventSource`, buffers the full match, and **emits each event when the simulated clock reaches its `match_second`**.
- Controls: `start`, `pause`, `resume`, `reset`, `set_speed(1|5|10|30|60)`, `seek(match_second)`. Seek and reset rebuild `MatchState` from scratch.
- Clock advances with `asyncio`. Stoppages are compressed so the demo does not stall.
- **Deterministic:** the same source and the same control sequence produce the same emitted sequence and the same detections.
- Publishes onto an in-process async **event bus** (`backend/app/services/bus.py`) with topics: `event`, `stats`, `detection`, `insight_pending`, `insight`, `recap`, `sim_status`.
- **Stats never wait for AI.** Stats are computed and pushed synchronously per event. AI work runs in background tasks.
- **Demo mode** (`POST /matches/{id}/simulation/demo`): reset, run at 30x from 0', jump to 60', play through 62'–70' (sustained pressure plus goal), jump to 77' (momentum shift), jump to 89', and finish with the full-time recap. This takes under 90 s of wall time.

---

## 8. Interpretation and explanation

### 8.1 Pattern detectors (`backend/app/patterns/`)

Thresholds, windows, and cooldowns live in `config/patterns.yaml`. Each detector is a small class with `evaluate(state, event) -> Detection | None`, and its docstring states the rule in plain English.

| Detector | Rule (defaults) | Cooldown |
|---|---|---|
| `sustained_pressure` | In the last 5 min: team possession ≥ 65% **and** shots ≥ 3 **and** final-third entries ≥ 6 | 5 min per team |
| `momentum_shift` | Attacking index = 3×shots + 1×final-third entries + 2×high recoveries + 5×xG. The team leading the index in the last 5 min differs from the leader in the previous 5 min, and the new leader's index is ≥ 2× its previous value and ≥ 8 | 8 min |
| `high_press_sequence` | ≥ 3 high recoveries by one team within 180 s | 5 min per team |

Key-moment detectors (`backend/app/patterns/key_moments.py`): `goal`, `big_chance` (shot with xG ≥ 0.30 that is not a goal), `card`, `half_time`, `full_time`.

**`Detection` output** (Pydantic):

```json
{
  "detection_id": "d_0007",
  "pattern": "sustained_pressure",
  "team_id": "NBR",
  "start_second": 3720,
  "end_second": 4020,
  "rule_strength": 0.82,
  "rule_strength_note": "Rule-derived: average of each metric's ratio to its threshold, capped at 1. Not a calibrated probability.",
  "evidence": {
    "possession_pct_last_5": 71,
    "shots_last_5": 4,
    "final_third_entries_last_5": 8
  },
  "event_ids": ["e01412", "e01419", "..."]
}
```

Never call `rule_strength` "confidence" or a probability in the UI. The UI label is "Signal strength (rule-based)".

Stretch detectors, only after the MVP: `player_influence` (top player by involvement and xG in the window) and `flank_concentration` (share of final-third entries by y-band: left < 22.7, centre, right > 45.3).

### 8.2 FactPack (`backend/app/ai/factpack.py`)

Built by code for each trigger. It contains only verified values:

```json
{
  "trigger": {"type": "goal", "minute": 69, "event_id": "e01431", "team": "Northbridge FC", "player": "Tomas Reyes"},
  "score_before": {"Northbridge FC": 0, "Riverside Athletic": 1},
  "score_after":  {"Northbridge FC": 1, "Riverside Athletic": 1},
  "window": "last_5",
  "facts": [
    {"key": "possession_pct", "team": "Northbridge FC", "value": 71, "unit": "%", "event_ids": ["..."]},
    {"key": "shots", "team": "Northbridge FC", "value": 4, "unit": "", "event_ids": ["..."]},
    {"key": "final_third_entries", "team": "Northbridge FC", "value": 8, "unit": "", "event_ids": ["..."]}
  ],
  "detections": [{"pattern": "sustained_pressure", "team": "Northbridge FC", "since_minute": 64}],
  "recent_events": [{"minute": 68, "type": "shot", "player": "Tomas Reyes", "outcome": "saved"}],
  "allowed_names": ["Northbridge FC", "Riverside Athletic", "Tomas Reyes", "..."],
  "clock_second": 4141
}
```

### 8.3 AI provider abstraction (`backend/app/ai/`)

```python
class AIProvider(Protocol):
    name: str  # "foundry" | "mock"
    async def generate_live_insight(self, facts: FactPack, mode: ModeConfig) -> InsightDraft: ...
    async def generate_event_explanation(self, facts: FactPack, mode: ModeConfig) -> InsightDraft: ...
    async def generate_match_recap(self, facts: RecapFactPack, mode: ModeConfig) -> RecapDraft: ...
```

- **`MockAIProvider`**: deterministic, template-based, uses only FactPack values, and is instant. It is the default when `AI_PROVIDER=mock` or Foundry env vars are missing. Its outputs are tagged `generated_by: "mock"`.
- **`FoundryAIProvider`** calls the Foundry deployment with:
  - A **system prompt** (`backend/app/ai/prompts/system.md`) that requires the model to:
    - Use only the supplied facts.
    - Never invent statistics, events, player actions, injuries, quotes, or causes.
    - Separate observation from interpretation, using hedged language ("suggests", "came after") rather than unsupported causal claims.
    - Explain *why the moment matters* in the match context.
    - Follow the mode's style.
    - Keep live insights to at most 2 sentences and at most 45 words.
    - Return JSON that matches the schema.
  - A **user message** containing the FactPack JSON and the mode config.
  - **Structured output** (JSON schema / response_format): `{headline (≤ 8 words), body, supporting_stats: [{label, value, unit}], cited_event_ids: [...]}`.
  - A timeout of 8 s, 1 retry on transient errors, temperature 0.3, and token limits set.
  - Auth: an API key from env locally; **managed identity** (`DefaultAzureCredential`) on Azure when `FOUNDRY_USE_MANAGED_IDENTITY=true`.
  - Logs: provider, deployment, latency, tokens, validator result. Never log keys.
- **`TemplateFallback`**: if Foundry times out or errors, or the validator fails twice, build the insight from the FactPack with templates. It is tagged `generated_by: "template"`.
- **Caching:** results are cached by `(match_id, trigger_id, mode)` in the DB. `scripts/prewarm_insights.py` runs every trigger of `demo_01` against real Foundry ahead of the demo and video recording.

### 8.4 Grounding validator (`backend/app/ai/validator.py`)

Deterministic checks:

- Extract every number from headline, body, and supporting_stats (digits, percentages, minutes, and number words one through twenty). Each must equal a FactPack value (percentages rounded to whole numbers), a score, or a minute present in the FactPack.
- Extract capitalized name candidates. Each must be in `allowed_names`. Common words are allow-listed.
- Every `cited_event_id` must exist in the FactPack and have `match_second ≤ clock_second`. This blocks **future leakage**.
- `supporting_stats` values must match facts exactly.

The result is `{passed: bool, violations: [...]}`. Store it with the insight.

### 8.5 Personalization (`config/modes.yaml` plus `backend/app/ai/modes.py`)

There is one generation path. Modes are **data**, not code branches:

```yaml
casual:
  label: Casual
  audience: "A fan new to football tactics"
  style: "Plain, friendly, no jargon. Explain any football term in a few words."
  max_words: 35
  include_stats: 1
  terminology: basic
tactical:
  label: Tactical
  audience: "An analyst who wants evidence"
  style: "Precise. Name zones, sequences and windows. Reference detected patterns by name."
  max_words: 45
  include_stats: 3
  terminology: advanced
# Stretch modes, defined but hidden until implemented:
broadcaster: {...}
club_focus: {...}     # requires club_id param
player_focus: {...}   # requires player_id param
fantasy: {...}
```

The mode only changes wording and how many stats are shown, never the facts. A test asserts that Casual and Tactical outputs for the same trigger cite numbers from the same FactPack and pass the validator.

### 8.6 Narrative outputs

- **Live insight:** triggered by each detection.
- **Key-moment explanation:** triggered by goal, big chance, or card. It describes the build-up from the last 5 minutes of verified facts.
- **Recaps:** created automatically at `half_time` and `full_time` and on demand via `POST /generate-recap`. The recap has 4 to 6 sentences, a "Key moments" list (minute, type, one line), and a final stats summary. It is built from `RecapFactPack` (all events so far plus detections) and validated the same way.

---

## 9. Backend API (`backend/app/api/`)

All responses are Pydantic models, and all errors return `{error: {code, message}}`. CORS is restricted to the configured web origin.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{status, version, ai_provider, event_source, db}` |
| GET | `/matches` | List available matches (from `data/matches/*.meta.json` and DB) |
| GET | `/matches/{match_id}` | Metadata: teams, squads, colours |
| GET | `/matches/{match_id}/state` | Clock, period, score, sim status, speed |
| GET | `/matches/{match_id}/stats?window=last_5\|last_10\|full` | Team and player stats with contributing event IDs |
| GET | `/matches/{match_id}/timeline` | Key events and detections so far |
| GET | `/matches/{match_id}/events?since_seq=&limit=` | Raw events so far (never future) |
| GET | `/matches/{match_id}/insights?mode=casual\|tactical` | Insights so far for a mode |
| GET | `/matches/{match_id}/recaps` | Recaps generated so far |
| GET | `/matches/{match_id}/stream?mode=` | **SSE**: `event`, `stats`, `detection`, `insight_pending`, `insight`, `recap`, `sim_status`, plus a heartbeat every 15 s |
| POST | `/matches/{match_id}/simulation/start` | Body `{speed?}` |
| POST | `/matches/{match_id}/simulation/pause` | |
| POST | `/matches/{match_id}/simulation/resume` | |
| POST | `/matches/{match_id}/simulation/reset` | Clears state, detections and live insights; cached AI text is kept |
| POST | `/matches/{match_id}/simulation/speed` | Body `{speed: 1\|5\|10\|30\|60}` |
| POST | `/matches/{match_id}/simulation/seek` | Body `{match_second}` |
| POST | `/matches/{match_id}/simulation/demo` | Scripted demo run |
| POST | `/matches/{match_id}/generate-recap` | Body `{mode, scope: "half_time"\|"full_time"\|"now"}` |

Insights for other modes are generated lazily when a client switches mode, and then cached. SSE messages carry the mode's text. On a mode switch, the client refetches `/insights?mode=`.

---

## 10. Persistence (`backend/app/db/`)

SQLAlchemy 2 models and Alembic migrations. `DATABASE_URL` defaults to `sqlite:///./insidematch.db`.

- `matches` (id, meta JSON, created_at)
- `events` (match_id, event_id PK pair, seq, match_second, payload JSON)
- `detections` (id, match_id, pattern, team_id, start/end_second, rule_strength, evidence JSON, event_ids JSON)
- `insights` (id, match_id, trigger_id, mode, type, minute, headline, body, supporting_stats JSON, cited_event_ids JSON, generated_by, model, latency_ms, validator JSON, created_at; unique on match_id + trigger_id + mode)
- `recaps` (id, match_id, scope, mode, body, key_moments JSON, generated_by, validator JSON)

Stats are always **recomputed from events**, never trusted from storage. A DB outage must not stop the live demo: log the error and continue in memory.

---

## 11. Frontend (`frontend/`, Next.js App Router)

**Look:** a dark, broadcast-studio style that is high contrast, uses team colours from metadata, and has smooth but restrained motion. It must not look like an admin panel. Value should be obvious within 5 seconds of opening: the clock is running, stats are moving, and an insight card is appearing.

**Main screen (`/match/[matchId]`, with `/` redirecting to `/match/demo_01`):**

- **Top bar:** generated SVG crest shields (fictional, built from team colours), team names, score, match clock (mm:ss plus period), a playback status pill (Live replay / Paused / Full time), an AI status badge (`Foundry` / `Mock` / `Fallback`), and a "Synthetic data" badge.
- **Main area (about 60% width on desktop):**
  - An **SVG pitch** (105×68) showing the ball's last position, animated between events, with a fading trail of the last 8 events in team colours, shot markers sized by synthetic xG, and a goal pulse animation.
  - A **live intelligence strip** under the pitch showing the current active detection (e.g. "NBR sustained pressure since 64'") with its signal strength (rule-based).
- **Insight feed (about 40%, right side):** cards, newest first. Each card shows the minute, a type badge (Pattern / Key moment / Recap), the headline, a body of at most 2 sentences, and 1–3 supporting stat chips. An **"Evidence"** expander lists facts and event IDs; clicking an event ID highlights it on the pitch and timeline. A skeleton "Analysing…" card shows while an insight is pending. Generated-by tags read "AI · Foundry", "Mock", or "Template".
- **Stats section:** a tab switch for **Last 5 / Last 10 / Full match**, with the window label always visible. Paired bars show possession, shots, shots on target, pass accuracy, final-third entries, high recoveries, and synthetic xG. A **player table** (sortable) lists involvement, passes, pass accuracy, shots, xG, and recoveries.
- **Timeline:** a horizontal 0'–90' strip with icons for goals, shots, cards, substitutions, and detections. Hover or tap shows details; click seeks the replay there.
- **Controls:** Start / Pause / Resume / Reset, a speed segmented control (1x, 5x, 10x, 30x, 60x), a **Demo mode** button, and the **viewer mode toggle (Casual | Tactical)**, which persists in localStorage. The mode toggle is prominent, because switching it live is the key demo moment.
- **Recap panel:** a large card with the half-time and full-time recaps, plus a "Generate recap now" button.
- **Footer:** "Synthetic match data. Clubs and players are fictional. Not affiliated with the Premier League." plus a link to the repo.

**Behaviour:**

- One `EventSource` connection, with auto-reconnect and backoff. On (re)connect, fetch `/state`, `/stats`, `/timeline`, and `/insights` to resync.
- Loading, empty, and error states for every panel. If the API is down, show a friendly banner with retry.
- Responsive: the 3-column desktop layout stacks on tablet and mobile. Keyboard accessible, with ARIA labels on controls and colour contrast of at least 4.5:1.
- `NEXT_PUBLIC_API_BASE_URL` is used for the API.
- Develop the UI first against a **mock data layer** (`frontend/lib/mock/`) that replays a recorded SSE log, then switch to the real API (Phase 7). Keep the mock behind `NEXT_PUBLIC_USE_MOCK_API=true` for UI work.

---

## 12. Repository structure

```
/README.md
/CLAUDE.md
/LICENSE                      (MIT)
/Makefile                     (dev, test, lint, generate-data, prewarm, docker-build)
/.env.example
/.github/workflows/ci.yml     (+ deploy.yml, optional)
/azure.yaml                   (azd)
/docs/
  PRD.md
  IMPLEMENTATION_PLAN.md
  architecture.md             (Mermaid diagrams)
  metrics.md
  setup-foundry.md
  setup-fabric.md
  setup-azure.md
  judging.md                  (criteria → evidence)
  demo-script.md
/data/
  schema/event.schema.json
  matches/demo_01.jsonl
  matches/demo_01.meta.json
  matches/demo_01.expected_stats.json
  matches/demo_01.storyline.md
/config/
  patterns.yaml
  modes.yaml
/backend/
  pyproject.toml
  Dockerfile
  alembic/
  app/
    main.py                   (FastAPI app, routers, lifespan)
    config.py                 (pydantic-settings)
    api/                      (routes: health, matches, simulation, stream, insights, recaps)
    models/                   (Pydantic: events, meta, stats, detections, insights)
    events/                   (EventSource, LocalSynthetic, Fabric, generator, simulator, adapters/)   ← INGEST
    analytics/                (stats engine)                                                         ← INTERPRET
    patterns/                 (detectors, key moments)                                               ← INTERPRET
    ai/                       (factpack, providers, prompts/, validator, modes, recap)               ← EXPLAIN + PERSONALIZE
    services/                 (bus, orchestrator wiring detections → AI → storage → SSE)
    db/                       (SQLAlchemy models, repository)
  tests/
    unit/  integration/  e2e/  fixtures/
/frontend/                    (Next.js app: app/, components/, lib/, tests/)                         ← RENDER
/scripts/
  compute_expected_stats.py
  prewarm_insights.py
  publish_to_fabric.py
  smoke_test_deployed.sh
/infrastructure/
  main.bicep, modules/*.bicep, main.parameters.json
```

You may refine this layout, but keep the five pipeline stages visibly separated.

---

## 13. Environment configuration (`.env.example`)

```
# --- Core ---
APP_ENV=local                         # local | azure
LOG_LEVEL=INFO
WEB_ORIGIN=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_API=false

# --- Events ---
EVENT_SOURCE=local                    # local | fabric
DEFAULT_MATCH_ID=demo_01

# --- AI (Microsoft Foundry) ---
AI_PROVIDER=mock                      # mock | foundry
FOUNDRY_ENDPOINT=                     # Foundry project / Azure OpenAI-compatible endpoint
FOUNDRY_API_KEY=                      # local only; use managed identity in Azure
FOUNDRY_MODEL_DEPLOYMENT=gpt-4.1-mini
FOUNDRY_API_VERSION=                  # if the chosen SDK path requires it
FOUNDRY_USE_MANAGED_IDENTITY=false
AI_TIMEOUT_SECONDS=8

# --- Fabric (optional) ---
FABRIC_EVENTSTREAM_SOURCE_CONNECTION_STRING=      # custom endpoint source (publish)
FABRIC_EVENTSTREAM_DEST_CONNECTION_STRING=        # custom endpoint destination (consume)
FABRIC_EVENTSTREAM_DEST_CONSUMER_GROUP=$Default
FABRIC_PUBLISH_ON_REPLAY=false

# --- Database ---
DATABASE_URL=sqlite:///./insidematch.db           # Azure: postgresql+psycopg://...

# --- Stretch ---
TRANSLATOR_ENDPOINT=
TRANSLATOR_KEY=
TRANSLATOR_REGION=
```

With no cloud variables set, `make dev` must give a fully working app in mock mode.

---

## 14. Build phases

Each phase ends with: app runnable, `make test` green, `docs/IMPLEMENTATION_PLAN.md` updated, and a commit.

| Phase | Deliverable | Done when |
|---|---|---|
| 1. Repo and local env | Structure from §12, Makefile, `.env.example`, `CLAUDE.md` (with the §4 rule, the fictional-data rule, and "tests before commit"), CI workflow, FastAPI `/health`, Next.js shell calling it | `make dev` shows the web shell with a green health badge; CI passes |
| 2. Dataset | Schema models plus JSON Schema, seeded generator, committed `demo_01` files, storyline doc | Same seed gives identical output; all events validate; unique IDs; goals link to shots |
| 3. Deterministic analytics | §6 modules, `MatchState`, expected-stats script | All §6.3 tests pass, including the 71/29 worked example and exact match with expected stats at 15', 45', 69', 90' |
| 4. Simulator | `EventSource`, `LocalSyntheticEventSource`, simulator with all controls, event bus | Tests: ordered emission, speed scaling, pause/resume, reset rebuilds state, deterministic replay, no duplicates |
| 5. APIs and real-time | §9 endpoints and SSE | httpx tests for every endpoint; SSE test receives ordered `event` and `stats` messages at 60x |
| 6. Frontend on mock data | All §11 panels against `lib/mock` | Visually complete; Playwright smoke test passes in mock mode |
| 7. Connect frontend | Real API and SSE, resync on reconnect | Pressing Start shows a live clock, score and stats from the backend |
| 8. Pattern detection | §8.1 detectors and key moments, `config/patterns.yaml`, detection CLI (`python -m app.patterns.report demo_01`) | Fixture tests fire and stay silent correctly; the storyline is detected within ±2 minutes of the scripted minutes; cooldowns are respected |
| 9. Mock AI provider | FactPack, `AIProvider`, `MockAIProvider`, `TemplateFallback`, validator, modes config, orchestrator, insight and recap storage, SSE delivery | E2E test (below) passes in mock mode; validator unit tests catch an invented number, an unknown name, and a future event ID |
| 10. Microsoft Foundry | `FoundryAIProvider`, prompts, structured output, timeout/retry/fallback, caching, prewarm script, `docs/setup-foundry.md` | With real credentials: `scripts/prewarm_insights.py` generates every demo insight with the validator passing (fix prompts, never loosen the validator). Without credentials: everything still works in mock mode. Tests for timeout fallback use a fake HTTP client |
| 11. Microsoft Fabric | `FabricEventSource`, `FabricPublisher`, `docs/setup-fabric.md` (Eventstream → Eventhouse plus custom endpoint, a sample KQL query for possession over time) | With env vars, a replay publishes to Fabric and the app can consume back from Fabric. Without them, a clear log line and local fallback. Unit tests use a fake Event Hubs client |
| 12. Persistence | §10 DB layer, Alembic, repository, caching insights in the DB | Restarting the API keeps cached insights; tests run on SQLite; DB failure does not stop replay |
| 13. UX polish and personalization | Motion, empty/error states, Evidence expander, mode switch regenerating or fetching cached text, recap panel, Demo mode button, mobile layout, accessibility pass | Demo mode runs the full storyline in under 90 s with no console errors; Lighthouse accessibility ≥ 90 |
| 14. Deployment and docs | Dockerfiles, Bicep plus `azd`, deploy workflow, README, all docs, `smoke_test_deployed.sh` | `azd up` (run by the human with their subscription) deploys both apps; the smoke test passes against the live URL; README complete |
| 15. Stretch (optional) | §2 stretch list in order | Each stretch item ships behind a flag and never breaks Demo mode |

**Required end-to-end test** (`backend/tests/e2e/test_pipeline.py`, mock AI): start replay of `demo_01` at 60x, then assert:

1. `stats` messages update the score and possession.
2. A `detection` for `sustained_pressure` (NBR) arrives.
3. An `insight_pending` and then an `insight` for that detection arrive, passing the validator.
4. The 69' goal produces a key-moment insight citing only events at or before 69'.
5. Full time produces a recap.

Add a Playwright test that loads the page, clicks Demo mode, and sees an insight card and the recap.

---

## 15. Azure deployment (Phase 14)

- `infrastructure/main.bicep` provisions: a Log Analytics workspace, a Container Apps environment, Azure Container Registry, a user-assigned managed identity (AcrPull, plus the **Azure AI User / Cognitive Services OpenAI User** role on the Foundry resource, passed in as a parameter because the human creates the Foundry project manually), Azure Database for PostgreSQL Flexible Server (Burstable B1ms, a database named `insidematch`, firewall allowing Azure services), and two Container Apps:
  - `api`: FastAPI on port 8000 with ingress external, **min replicas 1** (keeps the demo warm through Nov 10), and env from secrets.
  - `web`: Next.js standalone output on port 3000, external ingress, min replicas 1.
- `azure.yaml` defines the two services for `azd`.
- `.github/workflows/deploy.yml`: azd deploy with OIDC federated credentials. Document `azd pipeline config`.
- `docs/setup-azure.md` gives exact commands, expected cost (approximate, with a note to set a budget alert), and teardown (`azd down`) **after Nov 10**.
- **Do not run `azd up`, create cloud resources, or spend money yourself.** Prepare everything, then tell the human the exact commands to run.

---

## 16. Testing requirements (summary)

The tests must cover: possession, rolling windows, pass accuracy, shot counts (including the goal not double-counting), final-third entries, player stats, each detector (positive and negative), replay controls and determinism, every API endpoint, SSE delivery, the FactPack builder, the validator, mock provider output, Foundry provider fallback on timeout or error, mode consistency, recap time safety, the DB repository, and the Fabric source/publisher with fakes. Also include the E2E pipeline test and the Playwright smoke test. CI runs all non-cloud tests on every push. Cloud integration tests are skipped unless their env vars are set.

---

## 17. Reliability requirements

- Structured logging (JSON in Azure, pretty locally) with request IDs. Log provider, latency, and validator result for every AI call.
- Pydantic validation on all inputs, with 4xx errors in the documented shape.
- If Foundry fails, the template fallback is used, the UI badge shows "Fallback", and nothing crashes.
- If Fabric fails, the local source is used with a log warning.
- If the DB fails, the app continues in memory with a log error.
- Loading and error states in every UI panel. SSE auto-reconnects and resyncs.
- `/health` reports each dependency's status.
- Deterministic demo mode plus prewarmed cache, so the recorded video and the judges' demo never wait on a model.

---

## 18. Hackathon judging alignment

The five criteria are equally weighted (20% each). Optimize for them, and record the evidence in `docs/judging.md`:

- **Technological Implementation:** clean, separated pipeline stages; typed models; a tested deterministic engine; CI; a documented, seeded synthetic data generator (the rules value "optimized synthetic data creation"); IaC.
- **Agentic Design & Innovation:** the MVP has a grounded generation loop. Code assembles the FactPack, Foundry generates structured output, and a deterministic validator checks it and asks for a correction or falls back. Document this loop clearly as the agentic core. Do **not** add agents with no product responsibility. The stretch items (MCP server, then the Agent Framework multi-agent workflow) are the main levers to raise this score if time allows.
- **Real-World Impact:** the `EventSource` interface and adapters show how a real broadcaster or event-data feed would plug in. Evidence-linked insights suit studio use. Caching and fallback show production thinking.
- **User Experience & Presentation:** polished broadcast-style UI, value obvious in 5 seconds, Demo mode, and the live Casual/Tactical switch. Write `docs/demo-script.md` as a shot list for a video **under 2 minutes**.
- **Category Adherence:** primary target **Best Use of Microsoft Foundry**. Make Foundry central and visible (badge, README, architecture). Secondary: **Best Azure Cloud Native Integration** via Container Apps, managed identity, Postgres, and Bicep/azd.

Do not add Microsoft products just to raise the count.

---

## 19. Submission readiness and completion criteria

**README.md must contain:**

- A one-line pitch and a 3-sentence description.
- A screenshot or GIF placeholder path.
- Live demo URL and video URL placeholders.
- A **"How it works: Ingest → Interpret → Explain → Render → Personalize"** section mapping each stage to its folder.
- An **architecture diagram in Mermaid**: synthetic generator / Fabric Eventstream → EventSource → simulator → analytics and patterns → FactPack → Foundry (validator loop) → DB → SSE → Next.js.
- The grounding approach (the §4 rule, the validator, evidence IDs).
- Why SSE.
- Local setup in 3 commands, in mock mode.
- Foundry, Fabric, and Azure setup (linking `docs/`).
- Environment variables, how to run tests, and the synthetic data notes and storyline.
- **Known limitations** (honest list).
- A **"Hackathon Technology Mapping"** table:
  - Microsoft Foundry → grounded live insights, key-moment explanations, recaps
  - Microsoft Fabric → real-time event ingestion (Eventstream) and analytics (Eventhouse/KQL)
  - Azure Container Apps + ACR + managed identity → hosting
  - Azure Database for PostgreSQL → events, detections, insights, recaps
  - GitHub (public repo, Actions CI) and GitHub Copilot → development and collaboration (state honestly how they were used)
- Testing instructions for judges: no login, open the URL, click **Demo mode**.
- License (MIT) and a disclaimer: synthetic data, fictional clubs and players, not affiliated with the Premier League.

**The MVP is complete only when all of these are true:**

- [ ] `make dev` runs the full app locally in mock mode with no cloud credentials.
- [ ] `make test` passes: unit, integration, E2E pipeline test, and the Playwright smoke test.
- [ ] Stats for `demo_01` exactly match `expected_stats.json` at the checkpoints.
- [ ] All three detectors and all key moments fire at the scripted times during replay.
- [ ] Casual and Tactical insights render, differ in wording, and cite the same facts.
- [ ] Half-time and full-time recaps generate and contain no future events.
- [ ] With Foundry credentials, prewarm completes with every insight passing the validator.
- [ ] Killing the Foundry connection mid-replay produces fallback insights with no UI errors.
- [ ] Demo mode completes in under 90 s.
- [ ] No secrets in git history, and no real club or player names anywhere.
- [ ] Docker images build; Bicep compiles (`az bicep build`); the deploy instructions are complete.

---

## 20. Final report (print this when you stop)

End your work with a concise report in this exact structure:

1. **Works end-to-end:** features verified, and how (which tests or manual checks).
2. **Mocked or local only:** each item, and what is needed to make it real.
3. **Connected to Microsoft services:** Foundry, Fabric, Azure, each marked *verified live*, *implemented but untested without credentials*, or *not implemented*.
4. **Remaining work and risks:** prioritized, with the stretch items not started.
5. **Commands for the human:** exactly what to run next (Foundry setup, prewarm, `azd up`, smoke test, video recording).

Begin now with step 0: inspect the repository, read `docs/PRD.md`, and write `docs/IMPLEMENTATION_PLAN.md`.
