import type {
  Health,
  Insight,
  MatchEvent,
  MatchInfo,
  Mode,
  Recap,
  SimState,
  Speed,
  StatsResponse,
  TimelineItem,
  WindowName,
} from "./types";

export type Control = "start" | "pause" | "resume" | "reset" | "demo";

export type StreamHandlers = {
  onMessage: (topic: string, data: unknown) => void;
  onOpen: () => void;
  onError: () => void;
};

/** Everything the UI needs from the backend. Implemented by the real HTTP client and by the mock replay. */
export interface MatchApi {
  kind: "real" | "mock";
  health(): Promise<Health>;
  match(id: string): Promise<MatchInfo>;
  state(id: string): Promise<SimState>;
  stats(id: string, window: WindowName): Promise<StatsResponse>;
  timeline(id: string): Promise<TimelineItem[]>;
  events(id: string, sinceSeq: number, limit: number): Promise<MatchEvent[]>;
  insights(id: string, mode: Mode): Promise<Insight[]>;
  recaps(id: string): Promise<Recap[]>;
  control(id: string, action: Control, speed?: Speed): Promise<SimState>;
  setSpeed(id: string, speed: Speed): Promise<SimState>;
  seek(id: string, matchSecond: number): Promise<SimState>;
  generateRecap(id: string, mode: Mode, scope: "half_time" | "full_time" | "now"): Promise<Recap>;
  subscribe(id: string, mode: Mode, handlers: StreamHandlers): () => void;
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 0,
  ) {
    super(message);
  }
}

export const STREAM_TOPICS = ["event", "stats", "detection", "insight_pending", "insight", "recap", "sim_status"] as const;
