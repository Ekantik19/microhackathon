// Shapes returned by the InsideMatch API (mirrors backend/app/models).

export type Mode = "casual" | "tactical";
export type WindowName = "last_5" | "last_10" | "full";
export type SimStatus = "idle" | "running" | "paused" | "finished";
export const SPEEDS = [1, 5, 10, 30, 60] as const;
export type Speed = (typeof SPEEDS)[number];

export type TeamMeta = {
  team_id: string;
  name: string;
  short_name: string;
  primary_color: string;
  secondary_color: string;
  formation: string;
};

export type PlayerMeta = { player_id: string; name: string; shirt_number: number; position: string; starter: boolean };

export type MatchInfo = {
  match_id: string;
  competition: string;
  venue: string;
  kickoff: string;
  home_team_id: string;
  away_team_id: string;
  teams: TeamMeta[];
  squads: Record<string, PlayerMeta[]>;
  periods: { period: number; start_second: number; end_second: number }[];
};

export type MatchEvent = {
  match_id: string;
  event_id: string;
  seq: number;
  period: number;
  match_second: number;
  minute: number;
  second: number;
  team_id: string;
  player_id: string | null;
  event_type: string;
  outcome: string | null;
  x: number | null;
  y: number | null;
  end_x: number | null;
  end_y: number | null;
  possession_team_id: string | null;
  possession_id: number;
  recipient_id: string | null;
  xg: number | null;
  under_pressure: boolean;
  in_play: boolean;
  related_event_ids: string[];
};

export type SimState = {
  match_id: string;
  status: SimStatus;
  speed: number;
  clock_second: number;
  minute: number;
  second: number;
  period: number;
  score: Record<string, number>;
  events_emitted: number;
  events_total: number;
};

export const TEAM_METRICS = [
  "possession_pct",
  "shots",
  "shots_on_target",
  "pass_accuracy",
  "final_third_entries",
  "high_recoveries",
  "xg",
] as const;
export type TeamMetric = (typeof TEAM_METRICS)[number];
export type TeamValues = Partial<Record<TeamMetric | "possession_seconds" | "passes_attempted" | "passes_completed" | "recoveries", number | null>>;

export type StatsPayload = {
  clock_second: number;
  minute: number;
  second: number;
  period: number;
  score: Record<string, number>;
  windows: Record<WindowName, Record<string, TeamValues>>;
};

export type Metric = { value: number | null; event_ids: string[] };

export type PlayerStats = {
  player_id: string;
  team_id: string;
  involvement: Metric;
  passes_attempted: Metric;
  passes_completed: Metric;
  pass_accuracy: Metric;
  shots: Metric;
  xg: Metric;
  recoveries: Metric;
  final_third_entries: Metric;
};

export type WindowStats = {
  window: WindowName;
  start_second: number | null;
  end_second: number;
  teams: Record<string, Record<string, Metric | string>>;
  players: Record<string, PlayerStats[]>;
};

export type StatsResponse = { match_id: string; clock_second: number; score: Record<string, number>; stats: WindowStats };

export type TimelineItem = {
  kind: "event" | "detection";
  id: string;
  match_second: number;
  minute: number;
  second: number;
  period: number;
  type: string;
  team_id: string | null;
  player_id?: string | null;
  label: string;
  start_second?: number | null;
  rule_strength?: number | null;
};

export type Detection = {
  detection_id: string;
  match_id: string;
  pattern: string;
  kind: "pattern" | "key_moment";
  team_id: string | null;
  start_second: number;
  end_second: number;
  minute: number;
  second: number;
  period: number;
  rule_strength?: number | null;
  rule_strength_note?: string | null;
  evidence: Record<string, unknown>;
  event_ids: string[];
};

export type SupportingStat = { label: string; value: number | string; unit: string };
export type ValidatorResult = { passed: boolean; violations: string[] };
export type GenerationAttempt = { generated_by: string; passed: boolean; violations: string[] };

export type Insight = {
  insight_id: string;
  match_id: string;
  trigger_id: string;
  mode: Mode;
  type: "pattern" | "key_moment" | string;
  minute: number;
  match_second: number;
  headline: string;
  body: string;
  supporting_stats: SupportingStat[];
  cited_event_ids: string[];
  generated_by: "foundry" | "mock" | "template" | string;
  model?: string | null;
  latency_ms?: number | null;
  validator: ValidatorResult;
  attempts?: GenerationAttempt[];
  facts?: SupportingStat[];
  created_at: string;
};

export type PendingInsight = { trigger_id: string; mode: Mode; minute: number };

export type Recap = {
  recap_id: string;
  match_id: string;
  scope: "half_time" | "full_time" | "now" | string;
  mode: Mode;
  minute: number;
  match_second: number;
  body: string;
  key_moments: { minute: number; type: string; text: string }[];
  stats_summary: SupportingStat[];
  generated_by: string;
  validator: ValidatorResult;
  attempts?: GenerationAttempt[];
  cited_event_ids?: string[];
  created_at: string;
};

export type Health = { status: string; version: string; ai_provider: string; event_source: string; db: string };
