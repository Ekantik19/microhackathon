import { Crest } from "./Crest";
import { clockText, teamById } from "@/lib/format";
import type { Health, Insight, MatchInfo, SimState } from "@/lib/types";

const STATUS: Record<string, { label: string; tone: string }> = {
  idle: { label: "Ready", tone: "bg-white/10 text-white/80" },
  running: { label: "Live replay", tone: "bg-red-500/20 text-red-200" },
  paused: { label: "Paused", tone: "bg-amber-400/15 text-amber-200" },
  finished: { label: "Full time", tone: "bg-sky-400/15 text-sky-200" },
};

function aiBadge(health: Health | undefined, insights: Insight[], mock: boolean) {
  if (mock || health?.ai_provider === "mock") return { label: "AI: Mock", tone: "bg-white/10 text-white/80" };
  if (insights.at(-1)?.generated_by === "template") return { label: "AI: Fallback", tone: "bg-amber-400/15 text-amber-200" };
  return { label: "AI: Foundry", tone: "bg-accent/15 text-accent" };
}

export function TopBar({
  info,
  sim,
  health,
  insights,
  mock,
}: {
  info: MatchInfo;
  sim?: SimState;
  health?: Health;
  insights: Insight[];
  mock: boolean;
}) {
  const home = teamById(info, info.home_team_id)!;
  const away = teamById(info, info.away_team_id)!;
  const status = mock && sim?.status === "finished" ? { label: "Recording ended", tone: STATUS.finished.tone } : STATUS[sim?.status ?? "idle"];
  const ai = aiBadge(health, insights, mock);
  const period = sim?.status === "finished" && !mock ? "FT" : sim?.period === 2 ? "2nd half" : "1st half";

  return (
    <header className="panel flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between">
      <div className="flex items-center justify-center gap-3 md:justify-start" aria-live="polite">
        <div className="flex items-center gap-2">
          <Crest team={home} size={34} />
          <span className="hidden text-right text-base font-semibold sm:block">{home.name}</span>
        </div>
        <div className="flex flex-col items-center">
          <div className="tabular rounded-lg bg-black/40 px-3 py-1 text-2xl font-bold tracking-tight" data-testid="score">
            {sim?.score[home.team_id] ?? 0}
            <span className="px-1 text-white/40">–</span>
            {sim?.score[away.team_id] ?? 0}
          </div>
          <div className="tabular text-xs text-muted" data-testid="clock">
            {clockText(sim?.minute ?? 0, sim?.second ?? 0)} · {period}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-base font-semibold sm:block">{away.name}</span>
          <Crest team={away} size={34} />
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-medium">
        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 ${status.tone}`} data-testid="status-pill">
          {sim?.status === "running" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />}
          {status.label}
        </span>
        <span className={`rounded-full px-3 py-1 ${ai.tone}`} data-testid="ai-badge">
          {ai.label}
        </span>
        <span className="rounded-full bg-warn/15 px-3 py-1 text-warn">Synthetic data</span>
      </div>
    </header>
  );
}
