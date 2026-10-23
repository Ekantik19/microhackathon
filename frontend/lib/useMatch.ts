"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, type Control, type MatchApi } from "./api";
import { getApi } from "./client";
import { eventLabel, isTimelineEvent, playerNames } from "./format";
import type {
  Detection,
  Health,
  Insight,
  MatchEvent,
  MatchInfo,
  Mode,
  PendingInsight,
  Recap,
  SimState,
  Speed,
  StatsPayload,
  StatsResponse,
  TeamValues,
  TimelineItem,
  WindowName,
} from "./types";

type State = {
  info?: MatchInfo;
  health?: Health;
  sim?: SimState;
  stats?: StatsPayload;
  events: MatchEvent[];
  timeline: TimelineItem[];
  detections: Detection[];
  insights: Insight[];
  pending: PendingInsight[];
  recaps: Recap[];
  connection: "connecting" | "open" | "error";
  error?: string;
};

type Action =
  | { type: "loaded"; info: MatchInfo; health: Health }
  | { type: "resynced"; sim: SimState; stats: StatsPayload; timeline: TimelineItem[]; events: MatchEvent[]; insights: Insight[]; recaps: Recap[] }
  | { type: "insights"; insights: Insight[]; recaps: Recap[] }
  | { type: "message"; topic: string; data: unknown; mode: Mode }
  | { type: "connection"; value: State["connection"] }
  | { type: "error"; message?: string };

const initial: State = { events: [], timeline: [], detections: [], insights: [], pending: [], recaps: [], connection: "connecting" };
const MAX_EVENTS = 60;

function upsert<T>(list: T[], item: T, same: (a: T) => boolean): T[] {
  return [...list.filter((x) => !same(x)), item];
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "loaded":
      return { ...state, info: action.info, health: action.health, error: undefined };
    case "resynced":
      return {
        ...state,
        sim: action.sim,
        stats: action.stats,
        timeline: action.timeline,
        events: action.events,
        insights: action.insights,
        recaps: action.recaps,
        pending: [],
        detections: state.detections.filter((d) => d.end_second <= action.sim.clock_second),
        error: undefined,
      };
    case "insights":
      return { ...state, insights: action.insights, recaps: action.recaps, pending: [] };
    case "connection":
      return { ...state, connection: action.value };
    case "error":
      return { ...state, error: action.message };
    case "message":
      return applyMessage(state, action.topic, action.data, action.mode);
  }
}

function applyMessage(state: State, topic: string, data: unknown, mode: Mode): State {
  switch (topic) {
    case "event": {
      const e = data as MatchEvent;
      const timeline = isTimelineEvent(e)
        ? [
            ...state.timeline,
            {
              kind: "event" as const,
              id: e.event_id,
              match_second: e.match_second,
              minute: e.minute,
              second: e.second,
              period: e.period,
              type: e.event_type,
              team_id: e.event_type === "period_end" ? null : e.team_id,
              player_id: e.player_id,
              label: eventLabel(e, playerNames(state.info)),
            },
          ]
        : state.timeline;
      return { ...state, events: [...state.events, e].slice(-MAX_EVENTS), timeline };
    }
    case "stats": {
      const stats = data as StatsPayload;
      const sim = state.sim
        ? { ...state.sim, clock_second: stats.clock_second, minute: stats.minute, second: stats.second, period: stats.period, score: stats.score }
        : state.sim;
      return { ...state, stats, sim };
    }
    case "sim_status":
      return { ...state, sim: data as SimState };
    case "detection": {
      const d = data as Detection;
      const timeline =
        d.kind === "pattern"
          ? [
              ...state.timeline,
              {
                kind: "detection" as const,
                id: d.detection_id,
                match_second: d.end_second,
                minute: d.minute,
                second: d.second,
                period: d.period,
                type: d.pattern,
                team_id: d.team_id,
                label: d.pattern.replace(/_/g, " "),
              },
            ]
          : state.timeline;
      return { ...state, detections: upsert(state.detections, d, (x) => x.detection_id === d.detection_id), timeline };
    }
    case "insight_pending": {
      const p = data as PendingInsight;
      if (p.mode !== mode) return state;
      return { ...state, pending: upsert(state.pending, p, (x) => x.trigger_id === p.trigger_id) };
    }
    case "insight": {
      const i = data as Insight;
      if (i.mode !== mode) return state;
      return {
        ...state,
        insights: upsert(state.insights, i, (x) => x.trigger_id === i.trigger_id),
        pending: state.pending.filter((p) => p.trigger_id !== i.trigger_id),
      };
    }
    case "recap": {
      const r = data as Recap;
      return { ...state, recaps: upsert(state.recaps, r, (x) => x.recap_id === r.recap_id) };
    }
    default:
      return state;
  }
}

/** REST stats (with event IDs) → the compact shape the SSE stream pushes. */
function toPayload(responses: Record<WindowName, StatsResponse>): StatsPayload {
  const full = responses.full;
  const windows = Object.fromEntries(
    Object.entries(responses).map(([name, r]) => [
      name,
      Object.fromEntries(
        Object.entries(r.stats.teams).map(([team, metrics]) => [
          team,
          Object.fromEntries(
            Object.entries(metrics)
              .filter(([k]) => k !== "team_id")
              .map(([k, m]) => [k, typeof m === "string" ? null : m.value]),
          ) as TeamValues,
        ]),
      ),
    ]),
  ) as StatsPayload["windows"];
  return { clock_second: full.clock_second, minute: 0, second: 0, period: 1, score: full.score, windows };
}

export function useMatch(matchId: string, mode: Mode) {
  const [state, dispatch] = useReducer(reducer, initial);
  const [api, setApi] = useState<MatchApi | null>(null);
  const [attempt, setAttempt] = useState(0);
  const lastStatus = useRef<{ status?: string; emitted?: number }>({});

  useEffect(() => {
    void getApi().then(setApi);
  }, []);

  const resync = useCallback(async () => {
    if (!api) return;
    try {
      const [sim, last5, last10, full, timeline, insights, recaps] = await Promise.all([
        api.state(matchId),
        api.stats(matchId, "last_5"),
        api.stats(matchId, "last_10"),
        api.stats(matchId, "full"),
        api.timeline(matchId),
        api.insights(matchId, mode),
        api.recaps(matchId),
      ]);
      const events = await api.events(matchId, Math.max(0, sim.events_emitted - MAX_EVENTS), MAX_EVENTS);
      const stats = { ...toPayload({ last_5: last5, last_10: last10, full }), minute: sim.minute, second: sim.second, period: sim.period };
      lastStatus.current = { status: sim.status, emitted: sim.events_emitted };
      dispatch({ type: "resynced", sim, stats, timeline, events, insights, recaps });
    } catch (e) {
      dispatch({ type: "error", message: e instanceof ApiError ? e.message : "Something went wrong loading the match." });
    }
  }, [api, matchId, mode]);

  // Static data.
  useEffect(() => {
    if (!api) return;
    let cancelled = false;
    Promise.all([api.match(matchId), api.health()])
      .then(([info, health]) => {
        if (cancelled) return;
        dispatch({ type: "loaded", info, health });
        void resync(); // show the current state over REST even if the live stream is down
      })
      .catch((e) => !cancelled && dispatch({ type: "error", message: e instanceof ApiError ? e.message : String(e) }));
    return () => {
      cancelled = true;
    };
  }, [api, matchId, attempt, resync]);

  // The live stream. Resync on every (re)connect, and after seek/reset (events_emitted jumps).
  useEffect(() => {
    if (!api) return;
    dispatch({ type: "connection", value: "connecting" });
    const unsubscribe = api.subscribe(matchId, mode, {
      onOpen: () => {
        dispatch({ type: "connection", value: "open" });
        void resync();
      },
      onError: () => dispatch({ type: "connection", value: "error" }),
      onMessage: (topic, data) => {
        if (topic === "sim_status") {
          const s = data as SimState;
          const prev = lastStatus.current;
          const jumped = prev.emitted !== undefined && Math.abs(s.events_emitted - prev.emitted) > 1;
          lastStatus.current = { status: s.status, emitted: s.events_emitted };
          if (jumped) {
            void resync();
            return;
          }
        }
        if (topic === "event") lastStatus.current.emitted = (data as MatchEvent).seq;
        dispatch({ type: "message", topic, data, mode });
      },
    });
    return unsubscribe;
  }, [api, matchId, mode, resync, attempt]);

  const run = useCallback(
    async (fn: (api: MatchApi) => Promise<unknown>) => {
      if (!api) return;
      try {
        await fn(api);
      } catch (e) {
        dispatch({ type: "error", message: e instanceof ApiError ? e.message : String(e) });
      }
    },
    [api],
  );

  const actions = {
    control: (action: Control, speed?: Speed) => run((a) => a.control(matchId, action, speed)),
    setSpeed: (speed: Speed) => run((a) => a.setSpeed(matchId, speed)),
    seek: (second: number) => run((a) => a.seek(matchId, second)),
    generateRecap: () => run((a) => a.generateRecap(matchId, mode, "now")),
    retry: () => setAttempt((n) => n + 1),
    clearError: () => dispatch({ type: "error", message: undefined }),
  };

  return { ...state, api, actions };
}
