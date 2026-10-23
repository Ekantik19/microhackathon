# CLAUDE.md: InsideMatch (team handoff file)

> **This file is the single source of truth for project status.** Several teammates (and their Claude Code sessions)
> work on this repo. Anyone, human or Claude, must be able to read ONLY this file and continue exactly where the last
> person stopped, with no questions. The full spec is `docs/MASTER_PROMPT.md` (authoritative; read only the sections
> you need, see the index in §9). Product context: `docs/PRD.md`. Plan, assumptions and blockers:
> `docs/IMPLEMENTATION_PLAN.md`.

---

## 0. Team protocol (MANDATORY for every Claude Code session and every teammate)

1. **Start of session:** `git pull --rebase`, then read this whole file, top to bottom. Read the newest entry of the
   **Handoff log (§12)** and the **Who is working on what (§6)** table before touching code.
2. **Claim before you build:** put your name and the step in §6, commit (`docs: claim step N`) and push straight
   away, so two people never build the same step. If a step is already claimed, pick another or talk to that person.
3. **Work in small steps.** `make test` must be green before every commit. Commit messages: `phase N: ...` or
   `step N: ...` or `docs: ...`. End commit messages with the Co-Authored-By line your tooling asks for.
4. **Update this file at the end of EVERY step and before ending ANY session, even mid-step.** Update: the status
   table (§5), §6, Current state (§7), Next step (§8, written as exact instructions), contracts/gotchas (§9),
   decisions (§10), problems (§11), and add a **Handoff log entry (§12)** saying: date, who, what was finished,
   what is half-done (files, branch, failing tests), and the exact next command to run. Then commit and push.
5. **Write for a reader with zero chat history.** Use repo-relative paths, name files and functions, record every
   decision with its reason, and never write "as discussed" or "see chat". If you learn something non-obvious
   (a gotcha, a contract, a workaround), add it to §9 or §11 at once.
6. **Never leave uncommitted work silently.** If you must stop with work in progress, commit it on a branch
   (`wip/<name>-<topic>`), push it, and say so in §12.
7. **Merge conflicts in this file:** merge both sides by hand. Never delete another person's handoff entries,
   gotchas or decisions; keep the status table consistent with the latest pushed code.
8. **🔐 Human checkpoints:** anything needing credentials, money, or cloud resources stops for a human. Claude never
   runs `azd up`, never creates cloud resources, never commits secrets (`.env` is git-ignored), and never asks for
   keys to be pasted into chat.
9. **Honesty:** mock vs real is always labeled (UI badge, logs `provider=mock|foundry|template`, README). Report test
   results faithfully. Never skip, weaken or delete a test to make it pass.

---

## 1. Non-negotiable product rules

1. **Deterministic analytics vs AI.** All statistics are computed by code from structured events. An LLM must never
   compute, estimate or "fill in" a number. The AI receives a `FactPack` (verified facts built by code) and only
   turns facts into words. Every AI output passes the deterministic grounding validator before display; on failure
   it regenerates once, then uses the template fallback. Every insight stores the event IDs it cites. The AI only
   ever sees data up to the current replay clock.
2. **Fictional data only.** Default match: Northbridge FC (`NBR`) vs Riverside Athletic (`RVA`). No real clubs,
   players, crests or Premier League marks in data, UI, screenshots or video. UI footer and README say "Synthetic
   match data. Clubs and players are fictional."
3. **Tests before commit**, **no secrets in git**, **no cloud spending by Claude** (see §0).

---

## 2. Project in one paragraph

InsideMatch is a live AI football companion for the Microsoft + Premier League "Inside the Game" hackathon.
**Deadline: submission closes Oct 27 2026, 11:59 pm PT; team target Oct 27, 6 pm PT; live demo must stay up until
Nov 10.** Pipeline **Ingest → Interpret → Explain → Render → Personalize**: seeded synthetic event generator →
simulated real-time replay → deterministic stats, rolling windows, 3 pattern detectors + key moments → FactPack →
Microsoft Foundry (mock fallback) + grounding validator → (DB) → SSE → Next.js broadcast-style UI with Casual/Tactical
modes, insight cards with evidence and a visible "Grounding check", and recaps. Judging: 5 equal criteria
(Technological Implementation, Agentic Design & Innovation, Real-World Impact, UX & Presentation, Category
Adherence); primary category **Best Use of Microsoft Foundry**. Our differentiator: trustworthy, evidence-linked AI.

Stack: Python 3.12, FastAPI, Pydantic v2, `uv` (backend); Next.js **16.4** App Router, TypeScript, Tailwind v4,
`pnpm` (frontend); SSE via `sse-starlette`; SQLAlchemy/Alembic + Postgres (planned); Bicep + `azd` on Azure
Container Apps (planned).

---

## 3. Repo map

| Path | What it is (pipeline stage) |
|---|---|
| `backend/app/events/` | INGEST: `generator.py` (seeded match + storyline beats), `xg.py`, `sources.py` (EventSource), `catalog.py`, `simulator.py` (replay clock, controls, demo mode) |
| `backend/app/analytics/` | INTERPRET: pure stats functions + `state.py` (MatchState) |
| `backend/app/patterns/` | INTERPRET: detectors, `engine.py`, `hook.py` (wires into simulator), `report.py` CLI |
| `backend/app/ai/` | EXPLAIN + PERSONALIZE: `factpack.py`, `validator.py`, `providers.py` (Mock), `fallback.py`, `generate.py`, `modes.py`; `README.md` explains the grounded loop |
| `backend/app/services/` | `bus.py` (pub/sub), `store.py` (in-memory detections/insights/recaps + caches), `registry.py` (one simulator per match), `orchestrator.py` (detections → AI → store → bus), `payloads.py` |
| `backend/app/api/` | FastAPI routers: health, matches, simulation, stream (SSE), insights; `errors.py` (`{error:{code,message}}`) |
| `backend/app/models/` | Pydantic models: events, meta, stats, detections, insights, api |
| `backend/tests/` | `unit/`, `integration/`, `e2e/test_pipeline.py` (spec §14), `fixtures/` (`factory.ev()`, `FakeClock`, `demo.py`) |
| `frontend/` | RENDER: `app/match/[matchId]/page.tsx`, `components/*`, `lib/` (types, `realApi.ts`, `mock/mockApi.ts` + `recording.json`, `useMatch.ts`), `tests/mock/` + `tests/real/` Playwright, `scripts/screenshots.mjs` |
| `config/` | `patterns.yaml` (detector thresholds), `modes.yaml` (viewer modes) |
| `data/` | `matches/demo_01.{jsonl,meta.json,expected_stats.json,storyline.md}`, `schema/event.schema.json` |
| `scripts/` | `compute_expected_stats.py` (independent stats check), `record_mock_stream.py` (frontend mock fixture) |
| `docs/` | `MASTER_PROMPT.md` (spec), `PRD.md`, `IMPLEMENTATION_PLAN.md`, `metrics.md`, `setup-foundry.md` |

The original `CLAUDE_CODE_MASTER_PROMPT.md` and `InsideMatch_PRD.docx` live outside the repo on the original author's
machine; `docs/MASTER_PROMPT.md` and `docs/PRD.md` are the in-repo copies (real names in the PRD examples were
replaced with fictional ones).

---

## 4. Setup and commands

**First time on a new machine:**

```bash
git clone https://github.com/Ekantik19/microhackathon.git && cd microhackathon
# Prerequisites: Python 3.12, Node ≥ 20.9 (author uses 26, CI uses 24), uv, pnpm, GNU make  (macOS: brew install uv pnpm)
make install            # uv sync + pnpm install + Playwright Chromium
cp .env.example .env    # defaults = mock mode, no cloud needed. Add Foundry values only if you have them (never commit)
git config user.name "<you>"; git config user.email "<you>"   # your own identity
make dev                # API http://localhost:8000, web http://localhost:3000 (→ /match/demo_01)
make test               # everything; must be green before committing
```

| Command | Does |
|---|---|
| `make dev` / `make dev-api` / `make dev-web` | Run API (:8000, reload) and web (:3000) |
| `make test` | Backend ruff + format check + mypy + pytest (~25 s), frontend eslint + typecheck, mock Playwright (~10 s), real-backend Playwright (~45 s) |
| `make test-backend` / `make test-frontend` | Halves of the above |
| `make format` | ruff format + fixes |
| `make generate-data` | Regenerate demo_01 from the generator **and** `expected_stats.json` |
| `make record-mock` | Re-record `frontend/lib/mock/recording.json` from the real pipeline |
| `cd backend && uv run python -m app.patterns.report demo_01` | Print every detection for demo_01 |
| `cd frontend && node scripts/screenshots.mjs [baseUrl] [outDir]` | Demo-mode screenshots for a visual check |
| `make prewarm` | (Step 10) run every demo insight against Foundry |
| CI status without `gh` | `curl -s "https://api.github.com/repos/Ekantik19/microhackathon/actions/runs?per_page=3"` |

---

## 5. Step plan and status

Each step ends with green tests, an updated CLAUDE.md, and a commit (pushed by a human). 🔐 = a human must act.

| Step | What | Status |
|---|---|---|
| 0 | Inspect, PRD → `docs/PRD.md`, plan, CLAUDE.md | ✅ done |
| 1 | Repo scaffold, Makefile, `.env.example`, CI, FastAPI `/health`, Next.js shell | ✅ done |
| 🔐 A | Push to GitHub so CI runs | ✅ done (CI green) |
| 2 | Event schema, seeded generator, demo_01 files, storyline | ✅ done |
| 3 | Deterministic analytics + independent expected-stats check | ✅ done |
| 4 | EventSource, simulator, event bus, demo mode | ✅ done |
| 5 | REST API + SSE | ✅ done |
| 6 | Frontend on a recorded mock data layer + Playwright smoke | ✅ done |
| 7 | Frontend on the real API/SSE, resync, real-backend Playwright | ✅ done |
| 8 | Pattern detectors + key moments | ✅ done |
| 9 | FactPack, validator, mock AI, template fallback, modes, orchestrator, recaps, E2E test, visible Grounding check | ✅ done |
| 🔐 B | Create Microsoft Foundry project + model deployment; put endpoint/key in `.env` (see `docs/setup-foundry.md`) | ⏳ **next: waiting on a human** |
| 10 | FoundryAIProvider, prompts, structured output, timeout/retry/fallback, cache, prewarm | todo (can start with a fake client before 🔐 B) |
| 11 | **Judging lever:** MCP server with read-only match tools + "Ask the match" agent (Foundry tool calling over the same tools, answers checked by the same validator) + chat panel | todo |
| 12 | Club-focused and Player-focused modes (modes are data; small UI picker) | todo |
| 13 | Persistence: SQLAlchemy, Alembic, SQLite local / Postgres in Azure; cache insights in DB | todo |
| 14 | UX polish, accessibility (Lighthouse ≥ 90), demo mode < 90 s, mobile pass | todo |
| 🔐 D | Install az/azd/Docker, `az login`, `azd up` (a human runs it) | waiting on a human |
| 15 | Dockerfiles, Bicep, azd, deploy workflow, README, all docs, demo-video shot list, smoke test | todo |
| 🔐 C | (optional) Fabric workspace + Eventstream custom endpoint connection strings | waiting on a human |
| 16 | Fabric source/publisher. **Deprioritised: only if time remains** | todo |
| 17 | Remaining stretch: Broadcaster/Fantasy modes, multilingual, Agent Framework multi-agent | todo |

**Plan change (2026-10-23, agreed with the project owner):** to raise "Agentic Design & Innovation" and "Best Use of
Foundry", the visible grounding check (Step 9), the "Ask the match" agent + MCP (Step 11) and Club/Player modes
(Step 12) come before persistence and deployment; Fabric moved to the end as optional. **If time runs short, cut from
the bottom: 17, then 16, then 12. Never cut Steps 10, 11, 13, 14, 15.** Parallelisable now: Step 10 (needs 🔐 B for
the live test), Step 12, Step 13, and the infra half of Step 15 are largely independent; coordinate via §6.

---

## 6. Who is working on what

| Person | Step / branch | Since | Notes |
|---|---|---|---|
| Ekantik19 (+ Claude) | Steps 0–9 done; waiting on 🔐 B | 2026-10-23 | Next for this person: Step 10 once `.env` has Foundry values |
| _(add yourself)_ | | | |

---

## 7. Current state (as of the last handoff)

**Works end to end, locally, in mock-AI mode (`make dev`, no cloud):**
- Seeded synthetic match `demo_01` (1959 events, 1–1) with a scripted storyline; replay at 1/5/10/30/60x with start,
  pause, resume, reset, seek, and Demo mode (~36 s wall time).
- Deterministic stats (possession, shots, on target, pass accuracy, final-third entries, high recoveries, synthetic
  xG, player table) over last 5 / last 10 / full, each with contributing event IDs; independently verified.
- Detectors: sustained pressure, momentum shift, high-press sequence + key moments (goal, big chance, card, half-time,
  full-time). demo_01 yields exactly 12 detections (pinned by tests, listed in `data/matches/demo_01.storyline.md`).
- AI layer: FactPack → MockAIProvider → grounding validator → regenerate once → TemplateFallback; Casual and Tactical
  insights for every trigger; half-time/full-time recaps; on-demand recap; every attempt recorded and shown as the
  "Grounding check".
- REST + SSE API; Next.js UI: top bar, pitch, live intelligence strip, timeline (click to seek), insight feed with
  Evidence, stats tabs, player table, recap panel, mode toggle (persisted), reconnect banner.
- Tests: 111 backend (unit, integration, E2E pipeline), 4 mock Playwright, 4 real-backend Playwright. CI runs all.

**Mocked / not real yet:** AI text comes from `MockAIProvider` (badge "AI: Mock") until Step 10. Storage is in
memory (lost on API restart) until Step 13. Fabric not implemented (Step 16, optional). Nothing deployed.

**Not started:** Steps 10–17 (see §5).

---

## 8. Next step: exact instructions

### 🔐 Checkpoint B (a human)
Follow `docs/setup-foundry.md` (verified against Microsoft Learn on 2026-10-23): create a Foundry project at
ai.azure.com (New Foundry toggle on), deploy `gpt-4.1-mini` (Deploy → Default settings), copy the endpoint + API key
from the project Home page into the repo-root `.env`:
`AI_PROVIDER=foundry`, `FOUNDRY_ENDPOINT=https://<resource>.openai.azure.com`, `FOUNDRY_API_KEY=...`,
`FOUNDRY_MODEL_DEPLOYMENT=gpt-4.1-mini`. Keys are shared between teammates out of band (password manager), never in
git or chat.

### Step 10: FoundryAIProvider (spec §8.3)
- **Verified API facts (Microsoft Learn, 2026-10-23):** use the plain `openai` client with the v1 API:
  `OpenAI(base_url="https://<host>/openai/v1/", api_key=<key or token provider>)`, no `api_version`. Hosts
  `<r>.openai.azure.com` and `<r>.services.ai.azure.com` both work, so normalise `FOUNDRY_ENDPOINT` to scheme + host
  (the portal may show a project URL with `/api/projects/...`) and append `/openai/v1/`. Managed identity:
  `api_key=get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")` when
  `FOUNDRY_USE_MANAGED_IDENTITY=true`; role "Cognitive Services OpenAI User". Structured outputs:
  `client.beta.chat.completions.parse(model=deployment, messages=..., response_format=PydanticModel)` or
  `response_format={"type": "json_schema", "json_schema": {"name": ..., "strict": True, "schema": ...}}`. Strict
  schemas: every field in `required`, `additionalProperties: false`, no min/max/pattern/format keywords.
  `gpt-4.1-mini` 2025-04-14 supports this.
- Build `backend/app/ai/foundry.py` `FoundryAIProvider` (same protocol as `MockAIProvider`: `generate_live_insight`,
  `generate_event_explanation`, `generate_match_recap`, each taking `violations` for the retry). Use the async client
  (`AsyncOpenAI`).
- System prompt in `backend/app/ai/prompts/system.md`. Requirements (spec §8.3): use only the supplied facts; never
  invent stats, events, player actions, injuries, quotes or causes; hedge interpretation ("suggests", "came after");
  explain why the moment matters; follow the mode; live insights ≤ 2 sentences and ≤ the mode's `max_words`;
  headline ≤ 8 words; return the JSON schema. Add: copy fact labels exactly into `supporting_stats`; cite only event
  IDs listed in the FactPack; use names only from `allowed_names`. On a retry, list the validator violations.
- User message = FactPack JSON + mode config JSON. Temperature 0.3, `max_tokens` ~300 (insight) / ~600 (recap).
  Timeout `AI_TIMEOUT_SECONDS` (8 s) is already applied in `app/ai/generate.py`; add 1 SDK retry on transient errors.
- Log provider, deployment, latency, token usage and validator result. Never log keys.
- `get_provider(settings)` in `app/ai/providers.py` currently raises `NotImplementedError` for foundry: return the
  Foundry provider when `AI_PROVIDER=foundry` and an endpoint is set; otherwise mock with ONE clear warning log.
  `/health` already reports `app.state.ai_provider.name`; the UI badge shows Foundry, or "Fallback" when the latest
  insight is `template`.
- **Open decision (record it in §10):** the insight cache is in memory until Step 13. For prewarm to survive an API
  restart, either (a) add a small git-ignored JSON file cache (e.g. `data/cache/insights.json`) loaded at startup, or
  (b) make `scripts/prewarm_insights.py` call the running API (seek through the match) so the API's own cache fills.
  Recommendation: (b), because it needs no new storage code and Step 13 replaces it anyway.
- `scripts/prewarm_insights.py` + `make prewarm`: generate every demo_01 trigger in both modes plus recaps against
  Foundry and print a table of validator results. If drafts fail, **fix the prompt, never loosen the validator**. Real
  prose may hit `COMMON_WORDS` gaps in `validator.py`: add only genuine ordinary English words, never names.
- Tests: a fake OpenAI client (no network). Structured output parsed into `InsightDraft`; timeout leads to template;
  a transient error is retried once; a validator failure regenerates with violations. A live test marked
  `@pytest.mark.cloud`, skipped unless `FOUNDRY_ENDPOINT` is set. Then run the real-backend Playwright suite with
  Foundry on and check the badge.
- When done: update this file (all sections in §0.4) and `docs/setup-foundry.md`, commit `phase 10: ...`.

---

## 9. Contracts and gotchas by area

**Spec index (`docs/MASTER_PROMPT.md`):** §4 AI rule, §5 schema + generator, §6 analytics, §7 simulator, §8 detectors,
FactPack, validator, modes, narratives, §9 API, §10 DB, §11 frontend, §13 env vars, §14 phases + required E2E test,
§15 Azure, §17 reliability, §18 judging, §19 done criteria + README contents, §20 final report format.

**Data / generator**
- 1st half 0–2820 s, 2nd half 2820–5760 s (`H2_START`, `FULL_TIME` in `generator.py`). Display minute in the 2nd half
  = 45 + (t − 2820) // 60, so 69' ≈ t 4260. `Simulator.at(minute, second)` converts.
- Coordinates: the acting team always attacks toward x = 105. `possession_team_id` is `None` after an incomplete pass
  or clearance. Possession changes only on the winning team's event. Goals link to their shot via
  `related_event_ids`; press recoveries/tackles link to their `pressure` event. Substitution: `player_id` goes off,
  `recipient_id` comes on.
- **Any change to `generator.py` changes demo_01:** run `make generate-data` (tests fail until you do), then check
  `python -m app.patterns.report demo_01` still matches `storyline.md` and `tests/unit/test_storyline_detections.py`.

**Analytics**
- Windows are (t0, t1]: exclusive start, inclusive end. Percentages are whole numbers rounded half up, `None` ("n/a")
  when the denominator is 0. Possession excludes the transition interval that ends in a change of possession.
- Functions take events in seq order and only those received (≤ clock). `window_stats(..., with_players=False)` is
  the cheap per-event path (~1.7 ms). Metrics carry event-ID lists (large for full-match possession): strip them for
  per-event SSE (`services/payloads.py` does).

**Simulator**
- Per emitted event: `state.ingest` → bus `event` → bus `stats` → `await hook(sim, event, replaying)`. Hooks run while
  the simulator lock is held: a hook must NOT call simulator controls (deadlock). Spawn background tasks instead.
- `seek` rebuilds state from scratch, calls `sim.on_reset` callbacks, replays hooks with `replaying=True`, and
  publishes one `stats` + `sim_status` (clients refetch). Status: idle → running ⇄ paused → finished; `start()` when
  finished resets first. Dead-ball gaps > 2 match-seconds are skipped.
- Demo mode at 30x: 0'→3', seek 60'→70:30, seek 76'→80', seek 85:30→FT (spec said 89'; moved so the 86' big chance
  streams live). Seek with detectors + AI ≤ 0.6 s.
- The bus drops a subscriber's oldest message when its queue (default 2000) is full. Tests that drain only at the
  end need `EventBus(max_queue=100_000)`.

**API (frontend contract)**
- SSE topics: `event` (Event JSON), `stats` (clock_second, minute, second, period, score, windows{last_5, last_10,
  full}{team}{metric: value}), `sim_status` (SimState), `detection`, `insight_pending` {trigger_id, mode, minute,
  type}, `insight`, `recap` (the last three filtered by `?mode=`). A `sim_status` snapshot is sent on connect; ping
  every 15 s.
- REST: `/matches`, `/matches/{id}` (no `final_score`/`seed`, no spoilers), `/state`, `/stats?window=` (full metrics
  with event IDs + players), `/timeline` (items include detections with `start_second`, `rule_strength`),
  `/events?since_seq&limit`, `/insights?mode=`, `/recaps`, POST `simulation/{start,pause,resume,reset,speed,seek,demo}`,
  POST `/generate-recap` {mode, scope} → 409 `recap_not_available` if the scope isn't reached. Errors are always
  `{error:{code,message}}`. Manual controls cancel a running demo.
- httpx `ASGITransport` buffers whole responses: SSE tests need a real uvicorn server (see `tests/integration/test_sse.py`).

**Detectors**
- Thresholds in `config/patterns.yaml`. Momentum needs t ≥ 600 and a previous leader (a tie = no leader); high press
  evaluates only on a new high recovery; key moments fire on their defining event. Detection IDs `d_0001…` are
  deterministic from kickoff, so caches survive seek/reset. Detections cite only events ≤ `end_second` (tested).

**AI layer**
- The FactPack is built synchronously in `Orchestrator.on_detection` (time safety). It lists only detections from the
  last 10 minutes (older minutes were letting invented numbers through). Allowed numbers = fact values + scores +
  minutes in the pack; supporting stats must match a fact with the same label (a team suffix is allowed).
- Insights are generated eagerly for the visible modes (casual, tactical). IDs `{match}:{detection_id}:{mode}`.
  Caches: `store.insight_cache`, `store.recap_cache` (survive reset; live lists are cleared). Epoch guard: results from
  before a reset/seek fill the cache but never reach the live feed. Concurrency: semaphore of 4.
- Tests: `tests/fixtures/demo.py` replays demo_01 and builds every FactPack; background work is awaited with
  `await app.state.orchestrator.idle()`; the E2E test injects a `FakeClock` via `sim._now` / `sim._sleep`.

**Frontend**
- **Next.js is v16.4**, newer than most model training data: read `frontend/node_modules/next/dist/docs/` before using
  an API (`frontend/AGENTS.md` says the same; keep it committed). `params` is a Promise; `cacheComponents: true` means
  runtime data sits inside `<Suspense>`; `PageProps`/`LayoutProps` are generated globals (`pnpm typecheck` runs
  `next typegen`); Tailwind v4 (`@import "tailwindcss"`, no tailwind.config).
- `NEXT_PUBLIC_*` values are inlined at **build** time: the web Docker image must be built with the real API URL.
  `make dev-web` exports `NEXT_PUBLIC_*` from the root `.env`; the backend reads the root `.env` itself.
- ESLint forbids `setState` directly in an effect: use `useSyncExternalStore` or callbacks (see `lib/useStoredMode.ts`).
- If styles look stale or Tailwind classes are missing: `pkill -f "next dev"; rm -rf frontend/.next`.
- Home team always attacks right on screen. Use `uiColor(team)` for team colours on the dark UI (NBR navy is too
  dark). The mock replay ends at 70:30 and shows "Recording ended", not "Full time".
- Ports: `make dev` = API 8000 + web 3000. Mock e2e = web 3100 (`.next-e2e-mock`). Real e2e = API 8100 + web 3200
  (`.next-e2e-real`). Only one `next dev` may run per build folder; `next dev` adds tsconfig includes per folder
  (committed). Chromium `setOffline` doesn't cut an open localhost EventSource: tests use `page.route(..., abort)`.

**Tooling / git**
- GNU make 3.81 on macOS: keep recipes simple. Ruff ignores E501 (the formatter owns line length). A shell heredoc
  followed by a newline does not stop later commands on failure: chain with `&&`.
- az, azd and Docker are not installed on the original author's machine (needed only at 🔐 D / Step 15).
- Repo-local git identity is per person (`git config user.name/user.email`); don't commit someone else's.

---

## 10. Decisions and deviations from the spec (with reasons)

| Decision | Why |
|---|---|
| PRD examples' real club/player names replaced with fictional ones | Fictional-data rule |
| Signal strength = average of min(1, value / (1.5 × threshold)) | The spec's "ratio to its threshold, capped at 1" is always 1.0 when a rule fires, so it carries no information |
| Demo mode's last segment starts at 85:30, not 89' | So the scripted 86' big chance streams live |
| Two emergent momentum shifts (12:45, 44:29) kept | They are real outputs of the rule on the seeded data; documented in `storyline.md` |
| Possession credits no team for the transition interval ending in a change of possession | Contested time; matches the spec's "same possession_id" definition |
| Expected-stats checkpoints use the display clock; 69' = 69:00 (before the 69:07 goal) | Unambiguous; documented in `docs/metrics.md` |
| `/matches/{id}` hides `final_score` and `seed` | The UI must not see the future |
| Insights generated eagerly for Casual + Tactical; hidden modes later lazily | Instant live mode switch, the key demo moment |
| Mock data layer replays a recorded 63:30–70:30 slice of the real pipeline | Keeps the fixture small (≈ 420 KB) |
| Plan reordered: Ask-the-match agent + MCP and Club/Player modes before persistence/deploy; Fabric optional | Targets the weakest judging criteria (agentic, Foundry) |
| Grounding check shows only what really happened; any staged validator demo must be clearly labelled | Honesty rule |

---

## 11. Problems faced and solutions

| Problem | Solution |
|---|---|
| PRD is a .docx and pandoc is missing | Extracted text with Python `zipfile` + regex into `docs/PRD.md` |
| `uv`, `pnpm` not installed | `brew install uv pnpm` |
| `tsc`: `Cannot find name 'PageProps'` | Run `next typegen` first (`pnpm typecheck` does both) |
| `git commit` had no identity | Set repo-local `user.name`/`user.email` |
| Generator: a beat started before the current clock | Margins sized to the worst-case action (14 s); dead-ball gaps capped at the beat time; no `out_of_play` while the ball is already dead |
| Sustained pressure did not fire (too few final-third entries) | Smaller margins so background play runs between beats; a dominant team recycles the ball out of the box and re-enters |
| Many spurious momentum shifts from background noise | Lower background attack/shot tendencies; segments shaped so the "leader" flips only where the storyline wants |
| Next.js served stale CSS (missing new Tailwind classes) | `rm -rf frontend/.next` and restart |
| A second `next dev` refused to start ("Another next dev server is already running") | `distDir: NEXT_DIST_DIR` so test servers use their own build folders |
| Playwright offline mode didn't drop the SSE stream | Abort the stream with `page.route` instead |
| Mock replay blanked the pitch at the end | Mock `events_emitted` counted messages, not events; fixed |
| NBR navy unreadable on the dark UI | `uiColor()` uses the secondary colour when the primary is too dark |
| Validator let invented numbers through (minutes of old detections were "allowed") | FactPack lists only the last 10 minutes of detections |
| Validator accepted a supporting stat whose value matched any fact | Stats must match a fact with the same label |
| A test passed for the wrong reason (fixture short on entries) | Rewrote it to isolate the condition, with a positive control |

---

## 12. Handoff log (newest first)

### 2026-10-23: Ekantik19 + Claude Code (Opus 5.5)
- **Finished:** Steps 0–9, all committed. Pushed to GitHub up to Phase 8 at the time of writing; the owner pushes
  the rest (`git log origin/main..main` shows anything unpushed).
  `make test` fully green: 111 backend, 4 mock e2e, 4 real e2e. Verified Foundry setup steps written to
  `docs/setup-foundry.md`. This file was restructured as the team handoff document.
- **Half-done:** nothing. No open branches.
- **Waiting on:** 🔐 B, a Foundry project + `gpt-4.1-mini` deployment, with values in the repo-root `.env`.
- **Next command:** after `.env` is set, start Step 10 as described in §8. Without Foundry access, Step 10 can still be
  built and tested against a fake client, and Steps 12, 13 and the infra part of 15 can be claimed in parallel.
