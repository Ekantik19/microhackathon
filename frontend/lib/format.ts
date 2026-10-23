import type { MatchEvent, MatchInfo, TeamMeta } from "./types";

export const pad2 = (n: number) => String(n).padStart(2, "0");
export const clockText = (minute: number, second: number) => `${pad2(minute)}:${pad2(second)}`;

export function secondHalfStart(info: MatchInfo | undefined): number {
  return info?.periods.find((p) => p.period === 2)?.start_second ?? 2820;
}

/** Display minute (as a float) for a match_second. The 2nd-half clock restarts at 45:00. */
export function displayMinutes(matchSecond: number, h2: number): number {
  return matchSecond < h2 ? matchSecond / 60 : 45 + (matchSecond - h2) / 60;
}

export function minuteLabel(matchSecond: number, h2: number): string {
  return `${Math.floor(displayMinutes(matchSecond, h2))}'`;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** A team colour that stays readable on the dark UI: the primary colour, or the secondary if the primary is too dark. */
export function uiColor(team: TeamMeta | undefined): string {
  if (!team) return "#ffffff";
  return luminance(team.primary_color) < 0.1 ? team.secondary_color : team.primary_color;
}

export function teamById(info: MatchInfo | undefined, id: string | null | undefined): TeamMeta | undefined {
  return info?.teams.find((t) => t.team_id === id);
}

export function playerNames(info: MatchInfo | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  for (const squad of Object.values(info?.squads ?? {})) for (const p of squad) out[p.player_id] = p.name;
  return out;
}

/** Events are normalized so the acting team attacks toward x = 105. On screen the home team attacks right. */
export function toScreen(e: { team_id: string; x: number | null; y: number | null }, homeId: string): [number, number] | null {
  if (e.x === null || e.y === null) return null;
  return e.team_id === homeId ? [e.x, e.y] : [105 - e.x, 68 - e.y];
}

export function formatValue(value: number | null | undefined, unit = ""): string {
  if (value === null || value === undefined) return "n/a";
  const shown = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return `${shown}${unit}`;
}

const TIMELINE_TYPES = new Set(["goal", "shot", "card", "substitution", "period_end"]);

export function isTimelineEvent(e: MatchEvent): boolean {
  return TIMELINE_TYPES.has(e.event_type);
}

export function eventLabel(e: MatchEvent, names: Record<string, string>): string {
  const who = names[e.player_id ?? ""] ?? "";
  switch (e.event_type) {
    case "goal":
      return `Goal: ${who}`;
    case "shot":
      return `Shot (${(e.outcome ?? "").replace(/_/g, " ")}): ${who}, synthetic xG ${(e.xg ?? 0).toFixed(2)}`;
    case "card":
      return `${(e.outcome ?? "").replace(/^\w/, (c) => c.toUpperCase())} card: ${who}`;
    case "substitution":
      return `Substitution: ${names[e.recipient_id ?? ""] ?? ""} on, ${who} off`;
    case "period_end":
      return e.period === 1 ? "Half-time" : "Full-time";
    default:
      return e.event_type;
  }
}

export const PATTERN_LABELS: Record<string, string> = {
  sustained_pressure: "sustained pressure",
  momentum_shift: "momentum shift",
  high_press_sequence: "high-press sequence",
};
