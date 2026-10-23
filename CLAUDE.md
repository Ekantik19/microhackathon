# CLAUDE.md: InsideMatch

> **Read this file first at the start of every step.** It holds the scope, progress, next steps and gotchas,
> so you do not need to re-read the chat. Update it at the end of every step.
> The full spec is `docs/MASTER_PROMPT.md` (authoritative). Read only the sections you need for the current step.

## Non-negotiable rules

1. **Deterministic analytics vs AI.** All statistics are computed by code from structured events. An LLM must
   never compute, estimate or "fill in" a number. The AI receives a `FactPack` (verified facts built by code) and
   only turns facts into words. Every AI output passes the deterministic grounding validator before display;
   on failure, regenerate once, then use the template fallback. Every insight stores the event IDs it cites.
   The AI only ever sees data up to the current replay clock.
2. **Fictional data only.** Default match: Northbridge FC (`NBR`) vs Riverside Athletic (`RVA`). No real
   clubs, players, crests or Premier League marks in data, UI, screenshots or video. UI footer and README say
   "Synthetic match data. Clubs and players are fictional."
3. **Tests before commit.** `make test` must be green before every commit. Never skip, weaken or delete a test.
4. **Never commit secrets.** `.env` is git-ignored; only `.env.example` is committed.
5. **Do not spend money or create cloud resources.** Prepare commands; the human runs `azd up` etc.
6. Mock vs real is always labeled (`provider=mock` vs `provider=foundry`) in config, logs, UI and README.

## Project scope (one paragraph)

InsideMatch is a live AI football companion for the Microsoft "Inside the Game" hackathon (submit by
**Oct 27 2026, 6 pm PT** internal target; demo live until Nov 10). Pipeline: **Ingest → Interpret → Explain →
Render → Personalize**. Synthetic seeded event generator → simulated real-time replay → deterministic stats,
rolling windows and 3 pattern detectors → FactPack → Microsoft Foundry (mock fallback) + grounding validator →
SQLite/Postgres → SSE → Next.js broadcast-style UI with Casual/Tactical modes, insight cards and recaps.

Stack: Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy/Alembic (backend, `uv`), Next.js 14+ App Router +
TypeScript + Tailwind (frontend, `pnpm`), SSE via `sse-starlette`, Bicep + `azd` for Azure Container Apps.

## Layout

- Repo root: `/Users/ekantik/Desktop/microhackathon/microhackathon` (git remote `github.com/Ekantik19/microhackathon`)
- Parent folder holds the original `CLAUDE_CODE_MASTER_PROMPT.md` and `InsideMatch_PRD.docx`.
- `backend/app/{events=INGEST, analytics+patterns=INTERPRET, ai=EXPLAIN+PERSONALIZE, api, services, db}`
- `frontend/` = RENDER. `config/` = patterns.yaml, modes.yaml. `data/matches/` = demo_01 files.

## Step plan and progress

Each step is a small chunk ending with green tests, an updated CLAUDE.md, and a local commit.
🔐 = manual checkpoint where the human must authenticate or act.

| Step | Phase | Status |
|---|---|---|
| 0 | Inspect, PRD → `docs/PRD.md`, plan, CLAUDE.md | ✅ done |
| 1 | Phase 1: repo scaffold, Makefile, `.env.example`, CI, FastAPI `/health`, Next.js shell | ✅ done (commit `phase 1`) |
| 🔐 A | Push to GitHub (`git push -u origin main`) so CI runs. Needs your GitHub auth | ✅ done: pushed, CI green on `286e040` |
| 2 | Phase 2: event schema, seeded generator, demo_01 files, storyline | ✅ done (commit `phase 2`) |
| 3 | Phase 3: analytics engine + expected-stats script + tests | ✅ done (commit `phase 3`) |
| 4 | Phase 4: EventSource, simulator, event bus | ✅ done (commit `phase 4`) |
| 5 | Phase 5: REST API + SSE | ✅ done (commit `phase 5`) |
| 6 | Phase 6: frontend on mock data + Playwright smoke | ✅ done (commit `phase 6`) |
| 7 | Phase 7: connect frontend to real API/SSE | ✅ done (commit `phase 7`) |
| 8 | Phase 8: pattern detectors + key moments | ✅ done (commit `phase 8`) |
| 9 | Phase 9: FactPack, mock AI, validator, modes, orchestrator, E2E test **+ visible "Grounding check" on cards** | ✅ done (commit `phase 9`) |
| 🔐 B | Create Microsoft Foundry project + model deployment; put endpoint/key in `.env` | ⏳ next: waiting on human |
| 10 | Phase 10: FoundryAIProvider, prompts, structured output, fallback, cache, prewarm | todo |
| 11 | **NEW (judging lever): MCP server with read-only match tools + "Ask the match" agent** (Foundry tool calling over the same tools, answers checked by the same validator) + chat panel in the UI | todo |
| 12 | **NEW: Club-focused and Player-focused modes** (modes are data; small UI picker) | todo |
| 13 | Phase 12: persistence (SQLAlchemy, Alembic, Postgres) | todo |
| 14 | Phase 13: UX polish, accessibility, demo mode < 90 s, Lighthouse ≥ 90 | todo |
| 🔐 D | Install az/azd/Docker, `az login`, `azd up` | waiting on human |
| 15 | Phase 14: Dockerfiles, Bicep, azd, README, docs, demo script, smoke test | todo |
| 🔐 C | (optional) Fabric workspace + Eventstream custom endpoint connection strings | waiting on human |
| 16 | Phase 11: Fabric source/publisher. **Deprioritised: only if time remains** | todo |
| 17 | Remaining stretch: Broadcaster/Fantasy modes, multilingual, Agent Framework multi-agent | todo |

**Plan change (2026-10-23, agreed with the human):** the order was changed to raise the "Agentic Design &
Innovation" and "Best Use of Foundry" scores: grounding made visible (Step 9), "Ask the match" agent + MCP (Step 11)
and Club/Player modes (Step 12) come before persistence/deploy; Fabric moves to the end as optional. Deadline
Oct 27, 6 pm PT: if time runs short, cut from the bottom of the table (17, then 16, then 12), never Steps 9–11, 13–15.

## Current progress

- Step 0 done: PRD converted (real names replaced), master prompt copied to `docs/MASTER_PROMPT.md`,
  `docs/IMPLEMENTATION_PLAN.md` written. `uv` and `pnpm` installed via Homebrew.
- Step 1 done: backend (`app/main.py`, `config.py`, `api/health.py`, `api/errors.py` with `{error:{code,message}}`
  shape), 2 tests; frontend Next.js 16.4 shell at `/match/[matchId]` (`/` redirects to `/match/demo_01`) with
  green health badge + fictional-data footer; Makefile (`dev`, `test`, `lint`, `format`, `generate-data`,
  `prewarm`, `docker-build`); `.github/workflows/ci.yml`; MIT LICENSE. `make dev` + `make test` verified.
- Step 2 done: `app/models/events.py` (Event, EventType, `display_clock`), `app/models/meta.py` (MatchMeta),
  `app/events/xg.py` (synthetic xG formula), `app/events/generator.py` (MatchBuilder: seeded background
  possessions steered by `SEGMENTS` + scripted storyline `beats()`), committed `data/matches/demo_01.jsonl`
  (1959 events, 1–1), `demo_01.meta.json`, `demo_01.storyline.md`, `data/schema/event.schema.json`.
  `tests/unit/test_generator.py` (13 tests: determinism, committed file == generator output, ordering, clock,
  goal→shot links, storyline beats, xG formula, squads, schema current). 15 backend tests green.
- Step 3 done: `app/models/stats.py` (Metric{value,event_ids}, TeamStats, PlayerStats, WindowStats),
  `app/analytics/` (definitions, possession, shots, passing, territory, players, score, windows, context, state).
  `MatchState(match_id, teams)`: `ingest()` (False on duplicate/other match, handles out-of-order seq),
  `reset()`, `advance_clock()`, `score()`, `window(name, with_players)`, `windows()`. `docs/metrics.md`.
  `scripts/compute_expected_stats.py` (no app imports; per-second possession walk) →
  `data/matches/demo_01.expected_stats.json`. Tests: `test_analytics.py` (hand fixtures incl. 71/29),
  `test_expected_stats.py` (engine == script exactly; mutation-checked). 39 backend tests green.
- Step 4 done: `app/events/sources.py` (`EventSource` Protocol, `LocalSyntheticEventSource`, `InMemoryEventSource`),
  `app/events/catalog.py` (`list_match_ids`, `load_meta`), `app/services/bus.py` (`EventBus.publish/subscribe`,
  bounded per-subscriber queues, drop-oldest), `app/services/payloads.py` (`stats_payload` = compact values, no
  event IDs; `clock_fields`), `app/events/simulator.py` (`Simulator(meta, source, bus, hooks, tick, now, sleep)`:
  `load`, `start(speed)`, `pause`, `resume`, `set_speed`, `reset`, `seek`, `advance(match_seconds)`,
  `play_until`, `run_demo`, `snapshot`, `received`, `at(min, sec)`). Tests: `tests/unit/test_simulator.py`
  (12) with `tests/fixtures/fake_clock.py`. 51 backend tests green (~8 s).
- Step 5 done: models `app/models/{api,detections,insights}.py` (Detection, Insight, Recap, SupportingStat,
  ValidatorResult defined now so the API shape is stable). `app/services/store.py` (MatchStore: detections,
  insights keyed (trigger_id, mode), recaps, `insight_cache` survives `clear_live`), `app/services/registry.py`
  (MatchRegistry: lazy Simulator per match, `hook_factories` for later phases, demo task start/cancel),
  `app/api/{deps,matches,simulation,insights,stream}.py`, `main.py` (state on `app.state`: settings, bus,
  store, registry; lifespan shuts down sims). `/matches/{id}` omits `final_score` and `seed` (no spoilers).
  `generate-recap` returns 503 `recap_unavailable` until `app.state.recap_generator` is set (Step 9). SSE sends a
  `sim_status` snapshot on connect, filters insight/insight_pending/recap by `data["mode"]`, ping 15 s.
  Tests: `tests/integration/test_api.py` (11), `test_sse.py` (real uvicorn on port 0). 62 backend tests green.
- Step 6 done: frontend. `lib/types.ts` (mirrors backend models), `lib/api.ts` (`MatchApi` interface), `lib/realApi.ts`
  (fetch + EventSource with exp. backoff 1→15 s), `lib/mock/mockApi.ts` + `lib/mock/recording.json` (408 KB, recorded
  63:30–70:30 by `scripts/record_mock_stream.py` / `make record-mock`; sample insights/recap written from real stats,
  `generated_by: mock`), `lib/client.ts` (`getApi()` picks mock iff `NEXT_PUBLIC_USE_MOCK_API=true`, lazy import),
  `lib/useMatch.ts` (reducer over SSE topics; resync on open and when `sim_status.events_emitted` jumps),
  `lib/useStoredMode.ts` (useSyncExternalStore over localStorage), `lib/format.ts` (`uiColor`, `toScreen`, clock,
  labels). Components: TopBar, Crest, Controls, Pitch, IntelStrip, Timeline, InsightFeed, StatsPanel, PlayerTable,
  RecapPanel, ApiBanner, MatchScreen. Playwright (`playwright.config.ts`, `tests/smoke.spec.ts`, desktop 1280 +
  Pixel 7, port 3100, mock mode) is in `make test` and CI. Screenshots reviewed at desktop and mobile.
- Step 7 done: verified against the real backend (Start at 60x → live clock/score/stats; pause; reset; demo; timeline
  click-to-seek; API killed → "Live connection lost" banner → API restarted → auto-recovery, no page errors).
  `useMatch` now also resyncs over REST on mount (UI shows state even if SSE is down). `next.config.ts`
  `distDir: NEXT_DIST_DIR || ".next"` so test servers (`.next-e2e-mock`, `.next-e2e-real`) run beside `make dev`.
  Tests: `tests/mock/smoke.spec.ts` (`pnpm test:e2e`), `tests/real/live.spec.ts` + `playwright.real.config.ts`
  (`pnpm test:e2e:real`: starts uvicorn :8100 + next dev :3200; live stream, seek/timeline/reset, stream retry +
  resync via `page.route` abort). Both are in `make test`; CI has a new `e2e-real-api` job.
- Step 8 done: `config/patterns.yaml`; `app/patterns/{config,base,sustained_pressure,momentum_shift,high_press,
  key_moments,engine,hook,report}.py`. `Context(state, event)` caches the last and previous 5-min windows
  (`analytics.windows.window_stats_between`). `PatternEngine.process(state, event)` → Detections with IDs
  `d_0001…` (reset with the sim). `detect_all(events, teams, cfg)` for offline runs; CLI
  `python -m app.patterns.report demo_01`. `Simulator.on_reset` callbacks (reset + start of every seek).
  `detection_hooks(store, bus, cfg)` registered in `main.py`: store.add_detection always, bus `detection` only when
  not replaying. `TimelineItem` gained `start_second`, `rule_strength`; frontend rebuilds `detections` from the
  timeline on resync. demo_01 → 12 detections exactly as storyline.md (pinned). Seek with detectors ≤ 0.6 s.
  Tests: `test_patterns.py` (12 fixtures), `test_storyline_detections.py`, `test_detections_live.py`; real e2e checks
  the intel strip. 86 backend tests green (~18 s).
- Step 9 done: `app/ai/{README.md (§4 rule), models.py, factpack.py, modes.py, validator.py, providers.py (AIProvider,
  MockAIProvider, template_recap, get_provider), fallback.py (TemplateFallback), generate.py (draft → validate →
  regenerate once with violations → template; records GenerationAttempt list)}`, `config/modes.yaml` (casual,
  tactical visible; broadcaster/club_focus/player_focus/fantasy hidden), `app/services/orchestrator.py`
  (`Orchestrator.attach` = hook factory for on_reset, `on_detection` listener from `detection_hooks(...,
  listeners=[...])`, eager generation for visible modes, `insight_pending` → `insight`, recaps at HT/FT, epoch guard,
  semaphore 4, caches `store.insight_cache` / `store.recap_cache`, `recap_now` for POST /generate-recap → 409
  `recap_not_available` if scope not reached). Insight gained `attempts`, `facts` (labels "· Team"); Recap gained
  `attempts`, `cited_event_ids`. Frontend: `components/GroundingCheck.tsx` in Evidence + recaps, verified facts list.
  Mock fixture re-recorded from the real pipeline (`scripts/record_mock_stream.py` now drives `create_app`).
  Tests: `test_validator.py`, `test_ai_generation.py`, `tests/e2e/test_pipeline.py` (spec §14 five checks), API
  insights/recap test, real Playwright "Demo → insight + Grounding check → full-time recap < 90 s" (demo ≈ 36 s).
  111 backend tests + 4 mock e2e + 4 real e2e green.

## Next steps

- **🔐 Checkpoint B (human):** create a Microsoft Foundry project + chat model deployment (e.g. gpt-4.1-mini), put
  `AI_PROVIDER=foundry`, `FOUNDRY_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_MODEL_DEPLOYMENT` in repo-root `.env`
  (never in chat). Docs were checked 2026-10-23 and the verified steps are in `docs/setup-foundry.md`: use
  `OpenAI(base_url="https://<host>/openai/v1/", api_key=key or get_bearer_token_provider(DefaultAzureCredential(),
  "https://ai.azure.com/.default"))`, no api-version; hosts `<r>.openai.azure.com` or `<r>.services.ai.azure.com`
  (normalize FOUNDRY_ENDPOINT to scheme+host, then append /openai/v1/); structured outputs via
  `client.beta.chat.completions.parse(..., response_format=PydanticModel)` or `response_format={"type":"json_schema",
  "json_schema":{"name","strict":True,"schema"}}` (all fields required, additionalProperties false, no min/max/
  pattern); MI role "Cognitive Services OpenAI User".
- Step 10 (Phase 10, spec §8.3): `app/ai/foundry.py` `FoundryAIProvider` (openai SDK against the Foundry endpoint,
  structured output JSON schema for InsightDraft/RecapDraft, system prompt `app/ai/prompts/system.md` with the §8.3
  rules + "copy fact labels exactly; only cite event IDs from the FactPack", user message = FactPack JSON + mode,
  temperature 0.3, max tokens, timeout `AI_TIMEOUT_SECONDS`, 1 retry on transient errors, `previous violations` in
  the retry message, API key locally / `DefaultAzureCredential` when `FOUNDRY_USE_MANAGED_IDENTITY=true`, logs
  provider/deployment/latency/tokens/validator, never keys). `get_provider` returns it when configured, else mock
  with one clear warning. `/health` and the UI badge then show `foundry`; badge "Fallback" when the latest insight is
  `template`. `scripts/prewarm_insights.py` runs every demo_01 trigger (both modes + recaps) against Foundry and
  reports validator results (fix prompts, never loosen the validator). **Cache persistence decision needed:** the
  cache is in memory until Step 13 (DB); either add a small JSON-file cache now (e.g. `data/cache/insights.json`,
  git-ignored) that the API loads on startup, or run prewarm through the API. Tests with a fake OpenAI client:
  structured output parsed, timeout → template, transient error retried once, validator failure → regenerate.
  Cloud integration test marked `@pytest.mark.cloud`, skipped without env vars. Watch for validator false positives
  from real prose (COMMON_WORDS gaps): extend the common-word list only with genuine ordinary words, never names.
- After each step's commit, the human pushes; CI status can be checked without `gh` via
  `curl -s https://api.github.com/repos/Ekantik19/microhackathon/actions/runs?per_page=3` (public repo).

## Important things to keep in mind

- Toolchain on this Mac: python 3.12.9, node 26, uv 0.13, pnpm 12, GNU make 3.81 (old: no `.ONESHELL`
  surprises, keep recipes simple). **Missing:** az, azd, docker (only needed at Step 14 / 🔐 D).
- Spec section index (docs/MASTER_PROMPT.md): §4 AI rule, §5 schema+generator, §6 analytics, §7 simulator,
  §8 detectors/FactPack/validator/modes, §9 API, §10 DB, §11 frontend, §13 env, §14 phases, §19 done criteria,
  §20 final report format.
- Commits are local only. Pushing is the human's call (🔐 A). Repo-local git identity was set to
  `Ekantik19 <ekantikt@gmail.com>`; the human may switch to a GitHub noreply email before pushing.
- **Next.js is v16.4** (newer than training data). Read `frontend/node_modules/next/dist/docs/` before using an
  API. Known: `params` is a Promise; `cacheComponents: true` means runtime/async data must sit inside
  `<Suspense>`; `PageProps`/`LayoutProps` are global generated types (`next typegen`, already in
  `pnpm typecheck`); Tailwind v4 (`@import "tailwindcss"`, no tailwind.config). `next dev` re-adds a block to
  `frontend/AGENTS.md`; keep it committed.
- `NEXT_PUBLIC_*` vars are inlined at **build** time: the web Docker image must be built with the real API URL
  (Step 14). `make dev-web` exports `NEXT_PUBLIC_*` from root `.env`; backend reads root `.env` via pydantic-settings.
- `make test` = backend ruff + format check + mypy + pytest, then frontend eslint + typecheck. Playwright is added
  in Step 6.
- **Generator facts other steps rely on:** 1st half 0–2820 s, 2nd half 2820–5760 s (`H2_START`, `FULL_TIME`);
  display minute in 2nd half = 45 + (t − 2820)//60, so 69' ≈ t 4260. `possession_team_id` is `None` after an
  incomplete pass or clearance (loose ball = unassigned time). Possession changes only on the winning team's
  event. Goal events link to their shot via `related_event_ids`; recoveries/tackles from a press link to the
  `pressure` event. Substitution: `player_id` goes off, `recipient_id` comes on. Ruff ignores E501 (formatter
  owns line length).
- **Any change to generator.py changes demo_01.** Regenerate with `make generate-data`; the test
  `test_committed_file_matches_generator_output` fails until you do. Re-run expected stats (Step 3) after too.
- Approximate detector check from Step 2 (spec defaults): high press RVA ~42:42, sustained pressure NBR ~66:40,
  momentum → RVA ~77:50; **emergent** momentum → RVA at ~12:38 and ~44:29 (documented in storyline.md). Re-verify
  with the real detectors in Step 8; retune `SEGMENTS` only if needed.
- Shell gotcha: a `python3 - <<EOF` heredoc followed by a newline does NOT gate later commands; chain with `&&`.
- **Analytics contracts:** windows are (t0, t1] (exclusive start, inclusive end); percentages are whole numbers
  rounded half up, `None` when the denominator is 0; possession excludes the transition interval that ends in a
  change of possession. Functions take events in seq order, only those received (≤ clock). `window_stats(...,
  with_players=False)` is the cheap per-event path (avg 1.7 ms, worst 3.2 ms on demo_01; with players ~8 ms).
  Metrics carry event_id lists, which are large for full-match possession: strip them for per-event SSE pushes.
- `make generate-data` regenerates demo_01 **and** expected_stats.json. `test_committed_expected_stats_are_current`
  catches drift.
- **Simulator contracts:** per emitted event: `state.ingest` → bus `event` (event JSON) → bus `stats`
  (`stats_payload`) → `await hook(sim, event, replaying)`. Hooks run while the simulator lock is held: a hook must
  NOT call simulator controls (deadlock); spawn background tasks instead. `seek` rebuilds state from scratch,
  runs hooks with `replaying=True`, publishes only one `stats` + `sim_status` (clients should refetch on
  sim_status). Status: idle → running ⇄ paused → finished; `start()` when finished resets first. Dead-ball gaps
  > 2 match-seconds are skipped. `sim_status` payload = `snapshot()`.
- Demo mode (`run_demo`) at 30x: 0'→3', seek 60'→70:30, seek 76'→80', seek **85:30**→FT (spec said 89'; moved
  earlier so the 86' big chance streams live). ~40 s of wall time. Seeks will get slower once detectors run as
  hooks in Step 8 (re-measure; keep demo < 90 s).
- The bus drops the oldest message when a subscriber queue (default 2000) is full. Test subscribers that drain
  only at the end need `EventBus(max_queue=100_000)`.
- **API contracts for the frontend:** SSE topics `event` (Event JSON), `stats` (`stats_payload`: clock_second,
  minute, second, period, score, windows{last_5,last_10,full}{team}{metric: value}), `sim_status` (SimState),
  later `detection`, `insight_pending`, `insight`, `recap` (have `mode`). REST: `/state` SimState, `/stats?window=`
  full metrics with event_ids + players, `/timeline` items {kind,id,match_second,minute,second,period,type,
  team_id,player_id,label}, `/events?since_seq&limit`, `/insights?mode=`, `/recaps`. Manual controls cancel a
  running demo; `/demo` clears live store items and returns immediately.
- httpx `ASGITransport` buffers whole responses: SSE tests must use a real uvicorn server (see test_sse.py).
- **Frontend gotchas:** a stale `frontend/.next` cache served OLD CSS (missing new Tailwind classes) → if styles look
  wrong, `pkill -f "next dev"; rm -rf frontend/.next`. ESLint's react-hooks rule forbids setState directly in an
  effect (use useSyncExternalStore / callbacks). `devIndicators: false` in next.config. On screen the home team
  always attacks right (no end switch at half-time). The mock's "finished" means "Recording ended" (70:30), not FT.
  Team navy primary is too dark on the UI → always use `uiColor(team)` for bars/dots. Screenshot helper:
  `scratchpad/shots.mjs` (copy into frontend/ to run with node, since it imports @playwright/test).
- Ports: `make dev` = API 8000 + web 3000. Mock e2e = web 3100 (`.next-e2e-mock`). Real e2e = API 8100 + web 3200
  (`.next-e2e-real`, CORS via `WEB_ORIGIN`). Only ONE `next dev` may run per distDir ("Another next dev server is
  already running"). `next dev` rewrites tsconfig.json includes for each distDir; those entries are committed.
- Chromium `context.setOffline` does not cut an open localhost EventSource; use `page.route(..., abort)` instead.
- **Signal strength deviation from spec:** spec says "ratio to its threshold, capped at 1", which is always 1.0 when a
  rule fires. We use ratio to `strength_scale` (1.5) × threshold; the note text says so. Documented in patterns.yaml
  and IMPLEMENTATION_PLAN.
- Detector contracts: momentum needs t ≥ 600 and a previous leader (ties = no leader); high press only evaluates on a
  new high recovery; key moments fire on the defining event (goal, shot xG ≥ 0.30 not goal, card, period_end).
  Detections cite only events ≤ end_second (tested). Fixture factory `ev()` sets period 2 for t ≥ 2820.
- **AI contracts:** FactPack is built synchronously in `on_detection` (time safety); it lists only detections from the
  last 10 min (older minutes were letting invented numbers through). Allowed numbers = fact values + scores +
  minutes in the pack; supporting stats must match a fact with the same label (team suffix allowed). Insight IDs
  `{match}:{detection_id}:{mode}`; detection IDs are deterministic from kickoff, so caches survive seek/reset.
  `tests/fixtures/demo.py` replays demo_01 and builds every FactPack (cached). Background tasks: tests call
  `await app.state.orchestrator.idle()`. E2E uses a FakeClock by setting `sim._now/_sleep`.

## Problems faced and solutions

| Problem | Solution |
|---|---|
| PRD is a .docx and pandoc is missing | Extracted text with Python `zipfile` + regex into `docs/PRD.md` |
| PRD examples use real club/player names (fictional-data rule) | Replaced with Northbridge FC / Riverside Athletic / Tomas Reyes |
| `uv`, `pnpm` not installed | `brew install uv pnpm` |
| `tsc` failed: `Cannot find name 'PageProps'` | Run `next typegen` first (`pnpm typecheck` does both) |
| `git commit` had no identity configured | Set repo-local `user.name`/`user.email` |
| Generator: beat started before current clock (background overran) | Margins sized to the worst-case action (14 s); dead-ball gaps capped at the beat time; no `out_of_play` while the ball is already dead |
| Sustained pressure did not fire (too few final-third entries) | Smaller margins so background plays between beats; dominant team recycles the ball out of the box and re-enters |
| Many spurious momentum shifts from background noise | Lowered background attack/shot tendencies; shaped segments so the "leader" only flips where the storyline wants |
