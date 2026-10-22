# Implementation plan

One-page plan. Status tracking lives in `CLAUDE.md`; this page records phases, assumptions and blockers.

## Phases

Phases follow `docs/MASTER_PROMPT.md` §14, in order. Each ends with `make dev` runnable, `make test` green and a
commit: 1 repo/env → 2 dataset → 3 analytics → 4 simulator → 5 API+SSE → 6 frontend (mock) → 7 connect →
8 patterns → 9 mock AI + validator → 10 Foundry → 11 Fabric → 12 persistence → 13 UX polish → 14 deploy + docs →
15 stretch.

## Assumptions

- `docs/PRD.md` was missing; it was converted from `InsideMatch_PRD.docx`. Real club/player names in its examples
  were replaced with fictional ones to honour the fictional-data rule.
- No official hackathon dataset exists in the repo; the seeded synthetic generator is the only source.
- `pnpm` is used for the frontend and `uv` for the backend (both installed via Homebrew).
- Commits are made locally at the end of each phase; pushing to GitHub is left to the human.
- Python 3.12 from the system install is used by `uv` (no separate download).

## Blockers (need the human)

| Blocker | Needed for | Status |
|---|---|---|
| GitHub push auth | CI running on GitHub (Phase 1 "CI passes") | open |
| Microsoft Foundry project, model deployment, endpoint and key | Phase 10 live verification | open |
| Microsoft Fabric workspace + Eventstream custom endpoint | Phase 11 live verification | open (optional) |
| Azure subscription, `az`/`azd`/Docker installed, `az login` | Phase 14 deploy | open |
