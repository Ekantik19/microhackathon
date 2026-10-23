"use client";

import { useState } from "react";
import { formatValue, teamById, uiColor } from "@/lib/format";
import type { MatchInfo, StatsPayload, TeamMetric, WindowName } from "@/lib/types";
import { PlayerTable } from "./PlayerTable";
import type { MatchApi } from "@/lib/api";

const WINDOWS: { id: WindowName; label: string }[] = [
  { id: "last_5", label: "Last 5 min" },
  { id: "last_10", label: "Last 10 min" },
  { id: "full", label: "Full match" },
];

const ROWS: { key: TeamMetric; label: string; unit?: string; percent?: boolean }[] = [
  { key: "possession_pct", label: "Possession", unit: "%", percent: true },
  { key: "shots", label: "Shots" },
  { key: "shots_on_target", label: "Shots on target" },
  { key: "pass_accuracy", label: "Pass accuracy", unit: "%", percent: true },
  { key: "final_third_entries", label: "Final-third entries" },
  { key: "high_recoveries", label: "High recoveries" },
  { key: "xg", label: "Synthetic xG" },
];

function PairedBar({ home, away, homeColor, awayColor, percent }: { home: number | null; away: number | null; homeColor: string; awayColor: string; percent?: boolean }) {
  const h = home ?? 0;
  const a = away ?? 0;
  const homeShare = percent ? h / Math.max(h + a, 1) : h + a === 0 ? 0.5 : h / (h + a);
  return (
    <div className="flex h-2 overflow-hidden rounded-full bg-white/5" aria-hidden>
      <div className="h-full transition-all duration-500" style={{ width: `${homeShare * 100}%`, background: homeColor }} />
      <div className="h-full flex-1 transition-all duration-500" style={{ background: awayColor, opacity: h + a === 0 ? 0.2 : 1 }} />
    </div>
  );
}

export function StatsPanel({ info, stats, api, matchId, clockSecond }: { info: MatchInfo; stats?: StatsPayload; api: MatchApi | null; matchId: string; clockSecond: number }) {
  const [windowName, setWindowName] = useState<WindowName>("last_5");
  const home = teamById(info, info.home_team_id)!;
  const away = teamById(info, info.away_team_id)!;
  const values = stats?.windows[windowName];
  const label = WINDOWS.find((w) => w.id === windowName)!.label;

  return (
    <section className="panel p-4" aria-label="Live statistics">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">
          Live stats · <span className="text-foreground" data-testid="window-label">{label}</span>
        </h2>
        <div role="tablist" aria-label="Stats window" className="flex rounded-lg bg-black/40 p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.id}
              role="tab"
              aria-selected={windowName === w.id}
              className={`rounded-md px-3 py-1 text-xs font-medium ${windowName === w.id ? "bg-white/15" : "text-white/60 hover:text-white"}`}
              onClick={() => setWindowName(w.id)}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>
      {!values ? (
        <p className="text-sm text-muted">Loading stats…</p>
      ) : (
        <dl className="flex flex-col gap-3" data-testid="stats-rows">
          {ROWS.map((row) => {
            const h = values[home.team_id]?.[row.key] ?? null;
            const a = values[away.team_id]?.[row.key] ?? null;
            return (
              <div key={row.key}>
                <div className="mb-1 flex items-baseline justify-between text-sm">
                  <dd className="tabular w-14 font-semibold">{formatValue(h, row.unit)}</dd>
                  <dt className="text-xs text-muted">{row.label}</dt>
                  <dd className="tabular w-14 text-right font-semibold">{formatValue(a, row.unit)}</dd>
                </div>
                <PairedBar home={h} away={a} homeColor={uiColor(home)} awayColor={uiColor(away)} percent={row.percent} />
              </div>
            );
          })}
        </dl>
      )}
      <PlayerTable info={info} api={api} matchId={matchId} windowName={windowName} clockSecond={clockSecond} />
    </section>
  );
}
