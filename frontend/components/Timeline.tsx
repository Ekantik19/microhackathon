import { displayMinutes, secondHalfStart, teamById, uiColor } from "@/lib/format";
import type { MatchInfo, TimelineItem } from "@/lib/types";

const SPAN = 95; // display minutes shown (90 + stoppage)

function Marker({ item, color }: { item: TimelineItem; color: string }) {
  switch (item.type) {
    case "goal":
      return <circle r={5} fill={color} stroke="#fff" strokeWidth={2} />;
    case "shot":
      return <circle r={3} fill="none" stroke={color} strokeWidth={1.5} />;
    case "card":
      return <rect x={-2.5} y={-4} width={5} height={8} rx={1} fill="var(--warn)" />;
    case "substitution":
      return <path d="M-4 -2 H3 L1 -4 M4 2 H-3 L-1 4" stroke={color} strokeWidth={1.4} fill="none" />;
    case "period_end":
      return <rect x={-1} y={-7} width={2} height={14} fill="rgba(255,255,255,0.6)" />;
    default:
      return <rect x={-3.5} y={-3.5} width={7} height={7} transform="rotate(45)" fill="var(--accent)" />;
  }
}

export function Timeline({
  info,
  items,
  clockSecond,
  highlightId,
  onSeek,
}: {
  info: MatchInfo;
  items: TimelineItem[];
  clockSecond: number;
  highlightId?: string | null;
  onSeek: (matchSecond: number) => void;
}) {
  const h2 = secondHalfStart(info);
  const pos = (s: number) => `${(Math.min(displayMinutes(s, h2), SPAN) / SPAN) * 100}%`;
  const ticks = [0, 15, 30, 45, 60, 75, 90];

  return (
    <section className="panel px-4 pb-3 pt-4" aria-label="Match timeline">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">Timeline</h2>
        <span className="text-[11px] text-muted">Click a marker to replay from there</span>
      </div>
      <div className="relative h-14" data-testid="timeline">
        <div className="absolute left-0 right-0 top-6 h-1 rounded bg-white/10" />
        <div className="absolute left-0 top-6 h-1 rounded bg-accent/60 transition-all" style={{ width: pos(clockSecond) }} />
        {ticks.map((m) => (
          <span key={m} className="tabular absolute top-10 -translate-x-1/2 text-[10px] text-muted" style={{ left: `${(m / SPAN) * 100}%` }}>
            {m}&apos;
          </span>
        ))}
        {items.map((item) => {
          const team = teamById(info, item.team_id);
          const color = team ? uiColor(team) : "#fff";
          const active = highlightId === item.id;
          return (
            <button
              key={`${item.kind}-${item.id}`}
              className={`group absolute top-[26px] -translate-x-1/2 -translate-y-1/2 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${active ? "scale-150" : ""}`}
              style={{ left: pos(item.match_second) }}
              onClick={() => onSeek(item.match_second)}
              aria-label={`${item.minute}' ${item.label}. Replay from here.`}
            >
              <svg width={14} height={16} viewBox="-7 -8 14 16" aria-hidden>
                <Marker item={item} color={color} />
              </svg>
              <span className="pointer-events-none absolute bottom-6 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-black/90 px-2 py-1 text-[11px] group-hover:block group-focus-visible:block">
                {item.minute}&apos; {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
