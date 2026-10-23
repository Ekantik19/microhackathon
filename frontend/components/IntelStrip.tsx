import { PATTERN_LABELS, minuteLabel, secondHalfStart, teamById, uiColor } from "@/lib/format";
import type { Detection, MatchInfo } from "@/lib/types";

const ACTIVE_FOR_SECONDS = 600;

export function IntelStrip({ info, detections, clockSecond }: { info: MatchInfo; detections: Detection[]; clockSecond: number }) {
  const h2 = secondHalfStart(info);
  const active = [...detections]
    .reverse()
    .find((d) => d.kind === "pattern" && d.end_second <= clockSecond && clockSecond - d.end_second <= ACTIVE_FOR_SECONDS);
  const team = teamById(info, active?.team_id);

  return (
    <div className="panel flex min-h-14 items-center gap-3 px-4 py-3" aria-live="polite" data-testid="intel-strip">
      <span className="text-[11px] font-semibold uppercase tracking-widest text-accent">Live intelligence</span>
      {active ? (
        <div className="flex flex-1 flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium">
            <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: uiColor(team) }} />
            {team?.short_name} {PATTERN_LABELS[active.pattern] ?? active.pattern} since {minuteLabel(Math.max(0, active.start_second), h2)}
          </span>
          {active.rule_strength != null && (
            <span className="text-xs text-muted" title={active.rule_strength_note ?? undefined}>
              Signal strength (rule-based): <span className="tabular font-semibold text-foreground">{Math.round(active.rule_strength * 100)}%</span>
            </span>
          )}
        </div>
      ) : (
        <span className="text-sm text-muted">No pattern detected right now. Stats keep updating live.</span>
      )}
    </div>
  );
}
