import { SPEEDS, type Mode, type SimState, type Speed } from "@/lib/types";
import type { Control } from "@/lib/api";

type Props = {
  sim?: SimState;
  mode: Mode;
  onMode: (m: Mode) => void;
  onControl: (c: Control, speed?: Speed) => void;
  onSpeed: (s: Speed) => void;
};

const btn = "rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent";

export function Controls({ sim, mode, onMode, onControl, onSpeed }: Props) {
  const status = sim?.status ?? "idle";
  const primary =
    status === "running"
      ? { label: "Pause", action: "pause" as const }
      : status === "paused"
        ? { label: "Resume", action: "resume" as const }
        : { label: status === "finished" ? "Replay" : "Start", action: "start" as const };

  return (
    <section aria-label="Replay controls" className="panel flex flex-col gap-3 p-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <button className={`${btn} bg-accent text-black hover:brightness-110`} onClick={() => onControl(primary.action)} data-testid="primary-control">
          {primary.label}
        </button>
        <button className={`${btn} bg-white/10 hover:bg-white/15`} onClick={() => onControl("reset")}>
          Reset
        </button>
        <div role="group" aria-label="Replay speed" className="flex overflow-hidden rounded-lg border border-line">
          {SPEEDS.map((s) => (
            <button
              key={s}
              className={`tabular px-2.5 py-2 text-sm ${sim?.speed === s ? "bg-white/20 font-semibold" : "hover:bg-white/10"}`}
              aria-pressed={sim?.speed === s}
              aria-label={`Speed ${s}x`}
              onClick={() => onSpeed(s)}
            >
              {s}x
            </button>
          ))}
        </div>
        <button className={`${btn} bg-indigo-500/80 hover:bg-indigo-500`} onClick={() => onControl("demo")} data-testid="demo-button">
          ▶ Demo mode
        </button>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-muted">Viewer mode</span>
        <div role="radiogroup" aria-label="Viewer mode" className="flex rounded-xl bg-black/40 p-1">
          {(["casual", "tactical"] as const).map((m) => (
            <button
              key={m}
              role="radio"
              aria-checked={mode === m}
              data-testid={`mode-${m}`}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                mode === m ? "bg-white text-black shadow" : "text-white/70 hover:text-white"
              }`}
              onClick={() => onMode(m)}
            >
              {m === "casual" ? "Casual" : "Tactical"}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
