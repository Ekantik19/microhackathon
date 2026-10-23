import type { Mode, Recap } from "@/lib/types";
import { GroundingCheck } from "./GroundingCheck";

const SCOPE: Record<string, string> = { half_time: "Half-time recap", full_time: "Full-time recap", now: "Recap so far" };

export function RecapPanel({ recaps, mode, onGenerate, busy }: { recaps: Recap[]; mode: Mode; onGenerate: () => void; busy: boolean }) {
  const mine = recaps.filter((r) => r.mode === mode).sort((a, b) => b.match_second - a.match_second);
  return (
    <section className="panel p-4" aria-label="Recaps">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">Recap</h2>
        <button
          onClick={onGenerate}
          disabled={busy}
          className="rounded-lg bg-white/10 px-3 py-1.5 text-xs font-medium hover:bg-white/15 disabled:opacity-50"
        >
          {busy ? "Generating…" : "Generate recap now"}
        </button>
      </div>
      {mine.length === 0 ? (
        <p className="text-sm text-muted">Half-time and full-time recaps appear here automatically. They only use events received so far.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {mine.map((r) => (
            <article key={r.recap_id} className="card-in rounded-xl border border-line bg-black/30 p-4" data-testid="recap">
              <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider">
                <span className="text-accent">{SCOPE[r.scope] ?? r.scope}</span>
                <span className="tabular text-muted">at {r.minute}&apos;</span>
                <span className="ml-auto font-normal normal-case text-muted">{r.generated_by === "foundry" ? "AI · Foundry" : r.generated_by === "mock" ? "Mock" : "Template"}</span>
              </div>
              <p className="text-sm leading-relaxed text-white/85">{r.body}</p>
              {r.key_moments.length > 0 && (
                <>
                  <h3 className="mt-3 text-xs font-semibold uppercase tracking-wider text-muted">Key moments</h3>
                  <ul className="mt-1 space-y-1 text-sm">
                    {r.key_moments.map((k) => (
                      <li key={`${k.minute}-${k.type}-${k.text}`}>
                        <span className="tabular mr-2 text-muted">{k.minute}&apos;</span>
                        {k.text}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <div className="mt-3 text-xs text-muted">
                <GroundingCheck attempts={r.attempts} />
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
