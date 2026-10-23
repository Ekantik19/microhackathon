"use client";

import { useEffect, useMemo, useState } from "react";
import type { MatchApi } from "@/lib/api";
import { formatValue, playerNames, teamById, uiColor } from "@/lib/format";
import type { MatchInfo, PlayerStats, WindowName } from "@/lib/types";

type Col = { key: keyof PlayerStats; label: string; unit?: string };
const COLS: Col[] = [
  { key: "involvement", label: "Involvement" },
  { key: "passes_attempted", label: "Passes" },
  { key: "pass_accuracy", label: "Pass %", unit: "%" },
  { key: "shots", label: "Shots" },
  { key: "xg", label: "xG" },
  { key: "recoveries", label: "Recoveries" },
];
const REFRESH_SECONDS = 60; // refetch when the match clock has moved this far

export function PlayerTable({ info, api, matchId, windowName, clockSecond }: { info: MatchInfo; api: MatchApi | null; matchId: string; windowName: WindowName; clockSecond: number }) {
  const [rows, setRows] = useState<PlayerStats[] | null>(null);
  const [sort, setSort] = useState<{ key: keyof PlayerStats; desc: boolean }>({ key: "involvement", desc: true });
  const bucket = Math.floor(clockSecond / REFRESH_SECONDS);
  const names = useMemo(() => playerNames(info), [info]);

  useEffect(() => {
    if (!api) return;
    let cancelled = false;
    api
      .stats(matchId, windowName)
      .then((r) => !cancelled && setRows(Object.values(r.stats.players ?? {}).flat()))
      .catch(() => !cancelled && setRows([]));
    return () => {
      cancelled = true;
    };
  }, [api, matchId, windowName, bucket]);

  const value = (p: PlayerStats, key: keyof PlayerStats) => {
    const m = p[key];
    return typeof m === "object" ? (m.value ?? -1) : 0;
  };
  const sorted = [...(rows ?? [])].sort((a, b) => (sort.desc ? value(b, sort.key) - value(a, sort.key) : value(a, sort.key) - value(b, sort.key)));

  return (
    <div className="mt-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted">Players (involvement = recorded on-ball actions)</h3>
      <div className="max-h-72 overflow-auto rounded-lg border border-line">
        <table className="w-full min-w-[520px] text-left text-xs">
          <thead className="sticky top-0 bg-panel-2 text-muted">
            <tr>
              <th scope="col" className="px-2 py-2 font-medium">Player</th>
              {COLS.map((c) => (
                <th key={c.key} scope="col" className="px-2 py-2 text-right font-medium" aria-sort={sort.key === c.key ? (sort.desc ? "descending" : "ascending") : "none"}>
                  <button className="hover:text-foreground" onClick={() => setSort((s) => ({ key: c.key, desc: s.key === c.key ? !s.desc : true }))}>
                    {c.label}
                    {sort.key === c.key ? (sort.desc ? " ↓" : " ↑") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows === null && (
              <tr>
                <td colSpan={COLS.length + 1} className="px-2 py-3 text-muted">Loading players…</td>
              </tr>
            )}
            {rows?.length === 0 && (
              <tr>
                <td colSpan={COLS.length + 1} className="px-2 py-3 text-muted">No player actions in this window yet.</td>
              </tr>
            )}
            {sorted.map((p) => {
              const team = teamById(info, p.team_id);
              return (
                <tr key={p.player_id} className="border-t border-line">
                  <td className="px-2 py-1.5">
                    <span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: uiColor(team) }} />
                    {names[p.player_id] ?? p.player_id}
                  </td>
                  {COLS.map((c) => {
                    const m = p[c.key];
                    return (
                      <td key={c.key} className="tabular px-2 py-1.5 text-right">
                        {typeof m === "object" ? formatValue(m.value, c.unit) : ""}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
