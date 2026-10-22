# InsideMatch Product Requirements Document

Live football intelligence platform

Working draft for the hackathon team. This document defines the proposed product, its minimum viable version and the implementation plan. InsideMatch will process synthetic match events, calculate statistics and explain important moments in language suited to the viewer.

Scope note: Numerical match examples are illustrative synthetic scenarios. Technology choices are proposed and depend on access and integration testing. This document records the agreed product direction; it does not independently verify competition rules.

# 1 Product name

InsideMatch is the working name for a live AI football companion that turns match-event data into understandable, explainable and personalized football intelligence.

# 2 Problem

A scoreboard tells viewers what happened. Our product aims to explain why a moment matters, how the game is changing and which information is relevant to the viewer. Casual fans need simple explanations; tactical fans need more detail. Club and player followers need a focused view.

# 3 Core product idea

Structured match events enter the system over time. Code calculates statistics, detects meaningful patterns and supplies the evidence to the AI. The AI generates an explanation, which appears in the match interface.

Example sequence: 68:01 pass → 68:11 final-third entry → 68:17 shot → 68:41 recovery → 69:07 goal. An explanation can describe the preceding attacking pressure when the event evidence supports it.

# 4 Target users

## Casual fan

Wants clear explanations without specialist terms.

## Tactical fan

Wants evidence about possession, pressing and attacking patterns.

## Club fan

Chooses a club and receives priority for its events, players and relevant changes in control.

## Player focused fan

Selects a player and follows their recorded passes, shots and involvement. Chances created require explicit event links or a documented definition.

## Broadcaster or studio

Uses concise insights as commentary prompts, graphics or recap material.

# 5 Main user experience

- Match area showing a simulated match experience, score and clock. A production integration could display insights beside a licensed video feed.

- Timeline of goals, shots, cards and detected patterns.

- Live statistics with the time window clearly labeled.

- AI insight feed with supporting figures and event references.

- Casual and Tactical viewing modes in the MVP. Club and Player modes are extensions.

- Language selection when translation is implemented.

Illustrative insight: “Northbridge FC have had 71% of tracked possession and four shots in the last five minutes.” Any explanation of pressing or defensive positioning must also have supporting event evidence.

# 6 Core workflow

Synthetic event stream → ingestion → statistics and aggregation → pattern detection → backend → Foundry explanation → personalization → frontend. Statistics can update without waiting for AI generation.

# 7 Data source

For the hackathon build, replay synthetic football-realistic events gradually to simulate a live feed. The demo can accelerate match time. Production would require a suitable event-data provider and, if displayed, a licensed video source.

Example event: {"match_id":"demo_01", "event_id":"e103", "match_time_seconds":4097, "team":"Northbridge FC", "player":"Tomas Reyes", "event":"shot", "x":87, "y":35}.

Before coding, lock the schema and definitions: unique event IDs, timestamps, periods, teams, players, event type, outcome, possession changes, ball-in-play state and coordinates. Add pass endpoints and linked events where required. Fix pitch scale and attacking direction.

# 8 Statistics engine

Calculate match facts in code. The LLM receives these facts and must not invent missing measurements.

- Possession: track explicit team-control intervals. Exclude stoppages and unassigned intervals according to the documented denominator. Sparse passes alone do not establish exact possession time.

- Illustrative possession calculation: Northbridge FC 213 seconds and Riverside Athletic 87 seconds of assigned control. Total = 300 seconds. Northbridge FC = 213 ÷ 300 × 100 = 71%; Riverside Athletic = 29%.

- Shots: increment once per unique shot event. A goal linked to that shot must not count as a second shot.

- Pass accuracy = successful passes ÷ attempted passes × 100. Show unavailable when no passes were attempted.

- Final-third entries: count a defined crossing into the attacking third, using normalized direction and start/end locations; do not count every event already inside it.

- Player statistics: aggregate supported events by player. Do not equate event involvement with all touches.

# 9 Pattern detection

Start with two or three patterns. Thresholds are configuration choices to tune on the synthetic scenarios, rather than validated measures of football performance.

- Sustained pressure: a defined combination of recent shots, possession and final-third entries.

- Momentum shift: a meaningful change in recent attacking activity compared with the previous window.

- High recovery sequence: repeated recorded recoveries in a defined attacking zone. A pressing explanation requires additional pressure or sequence evidence.

- Player influence and attacking-flank patterns: extensions once event detail supports them.

# 10 AI layer using Microsoft Foundry

Send the triggering event, calculated window statistics, detected pattern and source event IDs to the model. Request a short explanation in the selected mode. Distinguish observations from tentative interpretations and omit unsupported causal claims.

Example input: goal at 71 minutes; 71% tracked possession, four shots, eight final-third entries and three high recoveries in the preceding five minutes. Example grounded output: “The goal followed a spell of sustained attacking activity, with four shots and repeated entries into the final third.”

# 11 Personalization

Casual mode uses plain language. Tactical mode includes more detail about the recorded sequences and pitch zones. Both use the same underlying facts. Club mode prioritizes a selected team; Player mode filters to a selected player. Personalization must preserve factual meaning.

# 12 Narrative generation

- Live insight when an important pattern is detected.

- Key moment explanation for a goal or another major event.

- Half-time or full-time recap using only events received by that point.

# 13 Multilingual experience

Proposed extension: generate the insight in English and use Azure Translator for the selected language. Preserve player names, team names and numerical values. Text-to-speech commentary using Azure Speech is a later extension.

# 14 Technical architecture

The simulator publishes timestamped events. The ingestion layer accepts them, the analytics engine updates match state and the backend serves statistics to the frontend. Important moments trigger an AI request. The resulting explanation is associated with its evidence and delivered to the viewer.

The database stores events and generated outputs. Translation runs only for supported requested languages. The frontend displays available statistics while an explanation is pending. Video synchronization, where used, needs a shared match clock and delay handling.

# 15 Proposed Microsoft technologies

## GitHub

Repository and team collaboration.

## GitHub Copilot

Development assistance for understanding and implementing code.

## Microsoft Fabric

Proposed event ingestion and real-time aggregation layer, subject to available access and configuration.

## Microsoft Foundry

Model access for explanations, personalized wording and recaps.

## Azure AI Services

Optional translation and speech.

## Azure database service

Store matches, events, calculated outputs and preferences. Choose the specific service during implementation.

## Azure hosting

Run backend APIs and supporting components. Select the hosting service after validating the end-to-end flow.

# 16 MVP requirements

- One synthetic match dataset with a documented schema.

- Replay events as a stream with a consistent match clock.

- Calculate and display supported live statistics.

- Automatically detect two or three defined patterns.

- Generate grounded explanations through Foundry.

- Update the frontend as events arrive.

- Support Casual and Tactical modes.

- Generate a recap from the received match history.

# 17 Stretch features

Priority 1: Club mode, Player mode and multilingual explanations. Priority 2: spoken commentary and richer tactical visuals. Priority 3: multiple specialized agents, automatic highlight generation or video-based event recognition. Start extensions only after the complete MVP works.

# 18 Non goals for the MVP

- Recognizing every event directly from video or building a player-tracking system.

- Building a complete football streaming service.

- Using the LLM to guess statistics or missing events.

- Adding agents without a clear product responsibility.

- Implementing every possible feature before a reliable demonstration exists.

# 19 Demo scenario

Start an accelerated synthetic match. Show statistics changing as events arrive. Trigger a sustained-pressure insight, then switch from Casual to Tactical mode. Replay a goal and display its evidence-backed explanation. Jump to the end of the replay and generate the recap.

# 20 Product success criteria

- Events arrive incrementally and the displayed clock matches the replay.

- Statistics match independently checked expected results for the demo dataset.

- Duplicate events do not inflate counts and restarts reset match state correctly.

- Patterns trigger automatically under the documented conditions.

- Generated explanations use supplied facts and do not reveal future events.

- Viewer modes change the wording while preserving the underlying facts.

- Recaps agree with the received event history.

- The interface remains useful when AI generation is delayed or unavailable.

- The full demonstration runs reliably and is understandable without a technical walkthrough.

# 21 Main value proposition

InsideMatch helps viewers understand a match through explanations tied to recorded events. It combines calculated statistics with short narratives and adapts the level of detail to how the viewer wants to follow the game.

## Next implementation decision

Agree the synthetic dataset schema and metric definitions first. Confirm which fields actually exist, then limit the initial statistics and pattern detectors to what those fields support.

---

_Converted from `InsideMatch_PRD.docx`. Real club/player names in the original examples were replaced with fictional ones (fictional-data rule). Where this PRD differs from `CLAUDE_CODE_MASTER_PROMPT.md`, the master prompt wins (e.g. PostgreSQL instead of Cosmos DB, Next.js instead of Vite)._
