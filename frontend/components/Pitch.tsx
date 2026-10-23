import { displayMinutes, teamById, toScreen } from "@/lib/format";
import type { MatchEvent, MatchInfo } from "@/lib/types";

const TRAIL = 8;
const SHOT_WINDOW_SECONDS = 600;

function Markings() {
  const line = { fill: "none", stroke: "rgba(255,255,255,0.55)", strokeWidth: 0.35 };
  return (
    <g>
      {Array.from({ length: 10 }, (_, i) => (
        <rect key={i} x={i * 10.5} y={0} width={10.5} height={68} fill={i % 2 ? "var(--pitch)" : "var(--pitch-2)"} />
      ))}
      <rect x={0} y={0} width={105} height={68} {...line} />
      <line x1={52.5} y1={0} x2={52.5} y2={68} {...line} />
      <circle cx={52.5} cy={34} r={9.15} {...line} />
      <circle cx={52.5} cy={34} r={0.4} fill="rgba(255,255,255,0.6)" />
      <rect x={0} y={13.84} width={16.5} height={40.32} {...line} />
      <rect x={88.5} y={13.84} width={16.5} height={40.32} {...line} />
      <rect x={0} y={24.84} width={5.5} height={18.32} {...line} />
      <rect x={99.5} y={24.84} width={5.5} height={18.32} {...line} />
      <circle cx={11} cy={34} r={0.35} fill="rgba(255,255,255,0.6)" />
      <circle cx={94} cy={34} r={0.35} fill="rgba(255,255,255,0.6)" />
      <rect x={-1.5} y={30.34} width={1.5} height={7.32} {...line} />
      <rect x={105} y={30.34} width={1.5} height={7.32} {...line} />
    </g>
  );
}

type Props = {
  info: MatchInfo;
  events: MatchEvent[];
  clockSecond: number;
  highlightId?: string | null;
};

export function Pitch({ info, events, clockSecond, highlightId }: Props) {
  const home = info.home_team_id;
  const color = (teamId: string) => teamById(info, teamId)?.secondary_color ?? "#fff";
  const fill = (teamId: string) => teamById(info, teamId)?.primary_color ?? "#fff";

  const located = events.filter((e) => e.x !== null && e.event_type !== "goal");
  const trail = located.slice(-TRAIL);
  const ball = trail.at(-1);
  const ballXY = ball ? toScreen(ball, home) : null;
  const shots = events.filter((e) => e.event_type === "shot" && clockSecond - e.match_second <= SHOT_WINDOW_SECONDS);
  const lastGoal = [...events].reverse().find((e) => e.event_type === "goal");
  const showPulse = lastGoal && clockSecond - lastGoal.match_second <= 20;
  const highlighted = highlightId ? events.find((e) => e.event_id === highlightId) : undefined;
  const highlightXY = highlighted ? toScreen(highlighted, home) : null;
  const h2 = info.periods.find((p) => p.period === 2)?.start_second ?? 2820;

  return (
    <figure className="panel overflow-hidden p-2">
      <svg viewBox="-2 -2 109 72" className="w-full" role="img" aria-label="Pitch view: last ball position, recent events and shots">
        <Markings />
        {trail.length > 1 && (
          <polyline
            points={trail.map((e) => toScreen(e, home)!.join(",")).join(" ")}
            fill="none"
            stroke="rgba(255,255,255,0.25)"
            strokeWidth={0.3}
            strokeDasharray="0.8 0.8"
          />
        )}
        {trail.map((e, i) => {
          const [x, y] = toScreen(e, home)!;
          return (
            <circle key={e.event_id} cx={x} cy={y} r={0.9} fill={fill(e.team_id)} stroke={color(e.team_id)} strokeWidth={0.25} opacity={(i + 1) / trail.length}>
              <title>{`${e.event_type} · ${Math.floor(displayMinutes(e.match_second, h2))}'`}</title>
            </circle>
          );
        })}
        {shots.map((s) => {
          const [x, y] = toScreen(s, home)!;
          const goal = s.outcome === "goal";
          return (
            <g key={`shot-${s.event_id}`}>
              <circle cx={x} cy={y} r={0.9 + (s.xg ?? 0) * 5} fill={fill(s.team_id)} fillOpacity={0.35} stroke={goal ? "#fff" : color(s.team_id)} strokeWidth={goal ? 0.6 : 0.3} />
              <title>{`Shot (${s.outcome}) · synthetic xG ${(s.xg ?? 0).toFixed(2)}`}</title>
            </g>
          );
        })}
        {showPulse && lastGoal && (
          <circle key={lastGoal.event_id} className="goal-pulse" cx={lastGoal.team_id === home ? 105 : 0} cy={34} r={1} fill="none" stroke="#fff" strokeWidth={0.6} />
        )}
        {highlightXY && <circle cx={highlightXY[0]} cy={highlightXY[1]} r={2.4} fill="none" stroke="var(--warn)" strokeWidth={0.5} />}
        {ballXY && (
          <g style={{ transform: `translate(${ballXY[0]}px, ${ballXY[1]}px)`, transition: "transform 450ms ease-out" }} data-testid="ball">
            <circle r={1.3} fill="#fff" stroke="#000" strokeWidth={0.25} />
          </g>
        )}
      </svg>
      <figcaption className="flex justify-between px-1 pt-1 text-[11px] text-muted">
        <span>← {teamById(info, info.away_team_id)?.short_name} attack</span>
        <span>Shot size = synthetic xG (last 10 min)</span>
        <span>{teamById(info, home)?.short_name} attack →</span>
      </figcaption>
    </figure>
  );
}
