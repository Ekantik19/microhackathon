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
| 4 | Phase 4: EventSource, simulator, event bus | ⏳ next |
| 5 | Phase 5: REST API + SSE | todo |
| 6 | Phase 6: frontend on mock data + Playwright smoke | todo |
| 7 | Phase 7: connect frontend to real API/SSE | todo |
| 8 | Phase 8: pattern detectors + key moments | todo |
| 9 | Phase 9: FactPack, mock AI, validator, modes, orchestrator, E2E test | todo |
| 🔐 B | Create Microsoft Foundry project + model deployment; put endpoint/key in `.env` | waiting on human |
| 10 | Phase 10: FoundryAIProvider, prompts, prewarm | todo |
| 🔐 C | (optional) Fabric workspace + Eventstream custom endpoint connection strings | waiting on human |
| 11 | Phase 11: Fabric source/publisher | todo |
| 12 | Phase 12: persistence (SQLAlchemy, Alembic) | todo |
| 13 | Phase 13: UX polish, accessibility, demo mode | todo |
| 🔐 D | Install az/azd/Docker, `az login`, `azd up` | waiting on human |
| 14 | Phase 14: Dockerfiles, Bicep, azd, README, docs, smoke test | todo |
| 15 | Stretch goals | todo |

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

## Next steps

- Step 4 (Phase 4, spec §7): `app/events/sources.py` (`EventSource` Protocol + `LocalSyntheticEventSource`
  reading `data/matches/{id}.jsonl`; Fabric source comes in Step 11), `app/services/bus.py` (in-process async
  pub/sub, topics event/stats/detection/insight_pending/insight/recap/sim_status), `app/events/simulator.py`
  (buffers match, emits each event when the simulated clock reaches its match_second; start/pause/resume/
  reset/set_speed(1|5|10|30|60)/seek; seek+reset rebuild MatchState; compress stoppages; deterministic;
  stats computed synchronously per event and published; demo-mode sequence). Make the clock injectable
  (fake clock / manual tick) so tests are fast and deterministic. Tests: ordered emission, speed scaling,
  pause/resume, reset rebuilds state, deterministic replay, no duplicates, seek.
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
