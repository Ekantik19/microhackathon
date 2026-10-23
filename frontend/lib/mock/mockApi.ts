// MOCK DATA LAYER (NEXT_PUBLIC_USE_MOCK_API=true). Replays a slice of a real simulator run recorded by
// scripts/record_mock_stream.py (63:30-70:30 of demo_01). Used for UI work and the Playwright smoke test.
// It is clearly labeled "Mock" in the UI and never used when the real API is configured.

import { ApiError, type MatchApi, type StreamHandlers } from "../api";
import type {
  Insight,
  MatchEvent,
  MatchInfo,
  Mode,
  Recap,
  SimState,
  SimStatus,
  Speed,
  StatsPayload,
  StatsResponse,
  TimelineItem,
  WindowName,
} from "../types";

type Message = { at: number; topic: string; data: unknown };
type Recording = {
  match: MatchInfo;
  start_second: number;
  end_second: number;
  snapshot: {
    state: SimState;
    stats: Record<WindowName, StatsResponse>;
    timeline: TimelineItem[];
    recent_events: MatchEvent[];
  };
  messages: Message[];
  end_stats: Record<WindowName, StatsResponse>;
  end_timeline: TimelineItem[];
};

const MODE_TOPICS = new Set(["insight", "insight_pending", "recap"]);
const TICK_MS = 100;

class MockMatch {
  status: SimStatus = "idle";
  speed = 10;
  clock = 0;
  private cursor = 0;
  private emittedEvents = 0;
  private timer: ReturnType<typeof setInterval> | null = null;
  private listeners = new Set<{ mode: Mode; handlers: StreamHandlers }>();
  events: MatchEvent[] = [];
  detections: TimelineItem[] = [];
  insights: Insight[] = [];
  recaps: Recap[] = [];
  lastStats: StatsPayload | null = null;

  constructor(private rec: Recording) {
    this.resetState();
  }

  private get secondHalfStart() {
    return this.rec.match.periods.find((p) => p.period === 2)?.start_second ?? 2820;
  }

  private resetState() {
    this.clock = this.rec.start_second;
    this.cursor = 0;
    this.emittedEvents = 0;
    this.events = [...this.rec.snapshot.recent_events];
    this.detections = [];
    this.insights = [];
    this.recaps = [];
    this.lastStats = null;
  }

  snapshot(): SimState {
    const t = Math.floor(this.clock);
    const period = t >= this.secondHalfStart ? 2 : 1;
    const shown = period === 1 ? t : 2700 + (t - this.secondHalfStart);
    return {
      match_id: this.rec.match.match_id,
      status: this.status,
      speed: this.speed,
      clock_second: t,
      minute: Math.floor(shown / 60),
      second: shown % 60,
      period,
      score: this.lastStats?.score ?? this.rec.snapshot.state.score,
      events_emitted: this.rec.snapshot.state.events_emitted + this.emittedEvents,
      events_total: this.rec.snapshot.state.events_total,
    };
  }

  private broadcast(topic: string, data: unknown) {
    for (const { mode, handlers } of this.listeners) {
      const msgMode = (data as { mode?: string } | null)?.mode;
      if (MODE_TOPICS.has(topic) && msgMode && msgMode !== mode) continue;
      handlers.onMessage(topic, data);
    }
  }

  private apply(message: Message, live: boolean) {
    const { topic, data } = message;
    if (topic === "event") {
      this.events = [...this.events, data as MatchEvent].slice(-60);
      this.emittedEvents += 1;
    }
    if (topic === "stats") this.lastStats = data as StatsPayload;
    if (topic === "insight") {
      const insight = data as Insight;
      this.insights = [...this.insights.filter((i) => !(i.trigger_id === insight.trigger_id && i.mode === insight.mode)), insight];
    }
    if (topic === "recap") this.recaps = [...this.recaps, data as Recap];
    if (topic === "detection") {
      const d = data as { detection_id: string; pattern: string; kind: string; team_id: string; end_second: number; minute: number; second: number; period: number };
      if (d.kind === "pattern") {
        this.detections.push({
          kind: "detection",
          id: d.detection_id,
          match_second: d.end_second,
          minute: d.minute,
          second: d.second,
          period: d.period,
          type: d.pattern,
          team_id: d.team_id,
          label: d.pattern.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()),
        });
      }
    }
    if (live) this.broadcast(topic, data);
  }

  private tick = () => {
    if (this.status !== "running") return;
    this.clock = Math.min(this.clock + (TICK_MS / 1000) * this.speed, this.rec.end_second);
    const messages = this.rec.messages;
    while (this.cursor < messages.length && messages[this.cursor].at <= this.clock) {
      this.apply(messages[this.cursor], true);
      this.cursor += 1;
    }
    if (this.cursor >= messages.length || this.clock >= this.rec.end_second) {
      this.status = "finished";
      this.stopTimer();
      this.broadcast("sim_status", this.snapshot());
    }
  };

  private startTimer() {
    if (!this.timer) this.timer = setInterval(this.tick, TICK_MS);
  }

  private stopTimer() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  control(action: string, speed?: Speed): SimState {
    if (speed) this.speed = speed;
    if (action === "reset" || action === "demo" || (action === "start" && this.status === "finished")) {
      this.stopTimer();
      this.status = "idle";
      this.resetState();
    }
    if (action === "demo") this.speed = 60;
    if (action === "start" || action === "demo" || (action === "resume" && this.status === "paused")) {
      this.status = "running";
      this.startTimer();
    }
    if (action === "pause" && this.status === "running") {
      this.status = "paused";
      this.stopTimer();
    }
    const state = this.snapshot();
    this.broadcast("sim_status", state);
    return state;
  }

  setSpeed(speed: Speed): SimState {
    this.speed = speed;
    const state = this.snapshot();
    this.broadcast("sim_status", state);
    return state;
  }

  seek(target: number): SimState {
    const t = Math.max(this.rec.start_second, Math.min(target, this.rec.end_second));
    const wasRunning = this.status === "running";
    this.resetState();
    while (this.cursor < this.rec.messages.length && this.rec.messages[this.cursor].at <= t) {
      this.apply(this.rec.messages[this.cursor], false);
      this.cursor += 1;
    }
    this.clock = t;
    this.status = this.cursor >= this.rec.messages.length ? "finished" : wasRunning ? "running" : "paused";
    if (this.status === "running") this.startTimer();
    if (this.lastStats) this.broadcast("stats", this.lastStats);
    const state = this.snapshot();
    this.broadcast("sim_status", state);
    return state;
  }

  stats(window: WindowName): StatsResponse {
    const midpoint = (this.rec.start_second + this.rec.end_second) / 2;
    const base = this.clock >= midpoint ? this.rec.end_stats[window] : this.rec.snapshot.stats[window];
    if (!this.lastStats) return base;
    const teams = Object.fromEntries(
      Object.entries(this.lastStats.windows[window]).map(([team, values]) => [
        team,
        { team_id: team, ...Object.fromEntries(Object.entries(values).map(([k, v]) => [k, { value: v, event_ids: [] }])) },
      ]),
    );
    return {
      match_id: base.match_id,
      clock_second: this.lastStats.clock_second,
      score: this.lastStats.score,
      stats: { ...base.stats, end_second: this.lastStats.clock_second, teams },
    };
  }

  timeline(): TimelineItem[] {
    const items = this.rec.end_timeline.filter((i) => i.match_second <= this.clock);
    return [...items, ...this.detections].sort((a, b) => a.match_second - b.match_second);
  }

  generateRecap(mode: Mode): Recap {
    const recorded = this.rec.messages.find((m) => m.topic === "recap" && (m.data as Recap).mode === mode);
    if (!recorded) throw new ApiError("recap_unavailable", "No recap in the mock recording.");
    const recap = { ...(recorded.data as Recap), recap_id: `mock_now_${mode}_${Date.now()}` };
    this.recaps = [...this.recaps, recap];
    this.broadcast("recap", recap);
    return recap;
  }

  subscribe(mode: Mode, handlers: StreamHandlers): () => void {
    const entry = { mode, handlers };
    this.listeners.add(entry);
    setTimeout(() => {
      handlers.onOpen();
      handlers.onMessage("sim_status", this.snapshot());
    }, 0);
    return () => this.listeners.delete(entry);
  }
}

let matchPromise: Promise<MockMatch> | null = null;

function load(): Promise<MockMatch> {
  matchPromise ??= import("./recording.json").then((m) => new MockMatch(m.default as unknown as Recording));
  return matchPromise;
}

async function withMatch<T>(id: string, fn: (m: MockMatch, rec: Recording) => T): Promise<T> {
  const match = await load();
  const rec = (await import("./recording.json")).default as unknown as Recording;
  if (id !== rec.match.match_id) throw new ApiError("match_not_found", `No match with id '${id}'`, 404);
  return fn(match, rec);
}

export const mockApi: MatchApi = {
  kind: "mock",
  health: async () => ({ status: "ok", version: "mock", ai_provider: "mock", event_source: "mock-recording", db: "n/a" }),
  match: (id) => withMatch(id, (_, rec) => rec.match),
  state: (id) => withMatch(id, (m) => m.snapshot()),
  stats: (id, window) => withMatch(id, (m) => m.stats(window)),
  timeline: (id) => withMatch(id, (m) => m.timeline()),
  events: (id, sinceSeq, limit) => withMatch(id, (m) => m.events.filter((e) => e.seq > sinceSeq).slice(0, limit)),
  insights: (id, mode) => withMatch(id, (m) => m.insights.filter((i) => i.mode === mode)),
  recaps: (id) => withMatch(id, (m) => m.recaps),
  control: (id, action, speed) => withMatch(id, (m) => m.control(action, speed)),
  setSpeed: (id, speed) => withMatch(id, (m) => m.setSpeed(speed)),
  seek: (id, t) => withMatch(id, (m) => m.seek(t)),
  generateRecap: (id, mode) => withMatch(id, (m) => m.generateRecap(mode)),
  subscribe(id, mode, handlers) {
    let unsubscribe: (() => void) | null = null;
    let cancelled = false;
    void withMatch(id, (m) => {
      if (!cancelled) unsubscribe = m.subscribe(mode, handlers);
    });
    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  },
};
