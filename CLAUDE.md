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
| 🔐 A | Push to GitHub (`git push -u origin main`) so CI runs. Needs your GitHub auth | waiting on human |
| 2 | Phase 2: event schema, seeded generator, demo_01 files, storyline | ⏳ next |
| 3 | Phase 3: analytics engine + expected-stats script + tests | todo |
| 4 | Phase 4: EventSource, simulator, event bus | todo |
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

## Next steps

- Step 2 (Phase 2, spec §5): `backend/app/models/events.py` + `meta.py` (Pydantic), export JSON Schema to
  `data/schema/event.schema.json`, seeded `backend/app/events/generator.py` (CLI `python -m app.events.generator
  --seed 42 --match-id demo_01`), outputs `data/matches/demo_01.{jsonl,meta.json}` and `demo_01.storyline.md`.
  Tests: same seed → identical bytes; all events validate; unique IDs; goals link to shots; storyline present.
  (`demo_01.expected_stats.json` is produced in Step 3 by `scripts/compute_expected_stats.py`.)
- 🔐 A can happen any time: `cd microhackathon && git push -u origin main`.

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

## Problems faced and solutions

| Problem | Solution |
|---|---|
| PRD is a .docx and pandoc is missing | Extracted text with Python `zipfile` + regex into `docs/PRD.md` |
| PRD examples use real club/player names (fictional-data rule) | Replaced with Northbridge FC / Riverside Athletic / Tomas Reyes |
| `uv`, `pnpm` not installed | `brew install uv pnpm` |
| `tsc` failed: `Cannot find name 'PageProps'` | Run `next typegen` first (`pnpm typecheck` does both) |
| `git commit` had no identity configured | Set repo-local `user.name`/`user.email` |
