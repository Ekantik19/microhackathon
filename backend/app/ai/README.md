# app/ai: EXPLAIN + PERSONALIZE

> **Non-negotiable rule.** All statistics are computed by code from structured events. A language model must never
> compute, estimate or "fill in" a number. The AI layer receives a `FactPack` (verified facts built by code) and
> only turns facts into words. Every output passes the deterministic grounding validator (`validator.py`) before it
> is shown: on failure it is regenerated once with the violations listed, and if it fails again the template
> fallback is used. Every insight stores the event IDs it cites. The AI only ever sees data up to the replay clock.

## The grounded generation loop (the agentic core)

```
detection ──► factpack.py builds a FactPack from MatchState (only events ≤ clock)
          ──► provider drafts {headline, body, supporting_stats, cited_event_ids}   (mock or Microsoft Foundry)
          ──► validator.py checks every number, name and cited event against the FactPack
                 passed? ──► store + stream the insight (attempts recorded: "Grounding check")
                 failed? ──► regenerate once with the violations listed ──► validate again
                 failed again / timeout / error? ──► fallback.py writes it from templates (tagged "template")
```

| File | Role |
|---|---|
| `models.py` | FactPack, RecapFactPack, InsightDraft, RecapDraft |
| `factpack.py` | Builds fact packs from code-computed stats, detections and recent events |
| `modes.py` | Loads `config/modes.yaml`. Modes change wording and how many stats are shown, never the facts |
| `providers.py` | `AIProvider` protocol and `MockAIProvider` (deterministic templates, tagged `mock`) |
| `fallback.py` | `TemplateFallback` (tagged `template`) |
| `validator.py` | The deterministic grounding validator |
| `generate.py` | The loop above: draft → validate → regenerate once → fallback |
