"use client";

import { useState } from "react";
import { useMatch } from "@/lib/useMatch";
import { useStoredMode } from "@/lib/useStoredMode";
import { ApiBanner } from "./ApiBanner";
import { Controls } from "./Controls";
import { InsightFeed } from "./InsightFeed";
import { IntelStrip } from "./IntelStrip";
import { Pitch } from "./Pitch";
import { RecapPanel } from "./RecapPanel";
import { StatsPanel } from "./StatsPanel";
import { Timeline } from "./Timeline";
import { TopBar } from "./TopBar";

export function MatchScreen({ matchId }: { matchId: string }) {
  const [mode, changeMode] = useStoredMode();
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [recapBusy, setRecapBusy] = useState(false);
  const match = useMatch(matchId, mode);

  const clock = match.sim?.clock_second ?? 0;
  const mock = match.api?.kind === "mock";

  if (!match.info) {
    return (
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-4 py-6">
        {match.error ? (
          <ApiBanner message={`${match.error} Is the backend running on the configured URL?`} onRetry={match.actions.retry} onDismiss={match.actions.clearError} />
        ) : (
          <div className="panel animate-pulse p-6 text-sm text-muted">Loading match…</div>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-4 py-4">
      <TopBar info={match.info} sim={match.sim} health={match.health} insights={match.insights} mock={mock} />
      {mock && (
        <p className="rounded-lg bg-white/5 px-3 py-2 text-center text-xs text-muted">
          Mock data layer: replaying a recorded slice (63:30–70:30) of the real simulator. Not connected to the API.
        </p>
      )}
      {match.error && <ApiBanner message={match.error} onRetry={match.actions.retry} onDismiss={match.actions.clearError} />}
      {match.connection === "error" && !match.error && (
        <div role="status" className="rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-200">Live connection lost. Reconnecting…</div>
      )}
      <Controls sim={match.sim} mode={mode} onMode={changeMode} onControl={match.actions.control} onSpeed={match.actions.setSpeed} />
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="flex flex-col gap-4 lg:col-span-3">
          <Pitch info={match.info} events={match.events} clockSecond={clock} highlightId={highlightId} />
          <IntelStrip info={match.info} detections={match.detections} clockSecond={clock} />
          <Timeline info={match.info} items={match.timeline} clockSecond={clock} highlightId={highlightId} onSeek={match.actions.seek} />
        </div>
        <div className="lg:col-span-2">
          <InsightFeed insights={match.insights} pending={match.pending} onHighlight={setHighlightId} />
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <StatsPanel info={match.info} stats={match.stats} api={match.api} matchId={matchId} clockSecond={clock} />
        </div>
        <div className="lg:col-span-2">
          <RecapPanel
            recaps={match.recaps}
            mode={mode}
            busy={recapBusy}
            onGenerate={async () => {
              setRecapBusy(true);
              await match.actions.generateRecap();
              setRecapBusy(false);
            }}
          />
        </div>
      </div>
    </main>
  );
}
