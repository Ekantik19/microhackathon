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
- Possession credits no team for the transition interval that ends in a change of possession (contested time).
- Expected-stats checkpoints use the display clock: 45' = 2700 s (before 1st-half stoppage), 69' = 69:00.
- Demo mode's last segment starts at 85:30 instead of 89' so the scripted 86' big chance is shown live.
- Stoppages longer than 2 match-seconds are skipped during replay (the clock jumps forward).
- The match metadata endpoint hides the final score and seed so the UI cannot show the future.
- The mock data layer replays a recorded 63:30–70:30 slice of the real simulator (not the whole match) to keep the
  fixture small; its sample insights are written from the recorded stats and labeled Mock.
- The UI also loads state over REST on mount, so it is useful even if the live stream is down.
- Status: phases 1–7 complete.

## Blockers (need the human)

| Blocker | Needed for | Status |
|---|---|---|
| GitHub push auth | CI running on GitHub (Phase 1 "CI passes") | resolved (pushed, CI green) |
| Microsoft Foundry project, model deployment, endpoint and key | Phase 10 live verification | open |
| Microsoft Fabric workspace + Eventstream custom endpoint | Phase 11 live verification | open (optional) |
| Azure subscription, `az`/`azd`/Docker installed, `az login` | Phase 14 deploy | open |
