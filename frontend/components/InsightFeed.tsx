import { formatValue } from "@/lib/format";
import type { Insight, PendingInsight } from "@/lib/types";

const GENERATED_BY: Record<string, string> = { foundry: "AI · Foundry", mock: "Mock", template: "Template" };
const TYPE_LABEL: Record<string, string> = { pattern: "Pattern", key_moment: "Key moment", recap: "Recap" };

function InsightCard({ insight, onHighlight }: { insight: Insight; onHighlight: (id: string) => void }) {
  return (
    <article className="card-in rounded-xl border border-line bg-black/30 p-4" data-testid="insight-card">
      <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider">
        <span className="tabular rounded bg-white/10 px-1.5 py-0.5">{insight.minute}&apos;</span>
        <span className={insight.type === "key_moment" ? "text-warn" : "text-accent"}>{TYPE_LABEL[insight.type] ?? insight.type}</span>
        <span className="ml-auto font-normal normal-case tracking-normal text-muted">{GENERATED_BY[insight.generated_by] ?? insight.generated_by}</span>
      </div>
      <h3 className="text-base font-semibold leading-snug">{insight.headline}</h3>
      <p className="mt-1 text-sm leading-relaxed text-white/80">{insight.body}</p>
      {insight.supporting_stats.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Supporting stats">
          {insight.supporting_stats.map((s) => (
            <li key={s.label} className="rounded-md bg-white/5 px-2 py-1 text-xs">
              <span className="text-muted">{s.label}</span>{" "}
              <span className="tabular font-semibold">{typeof s.value === "number" ? formatValue(s.value, s.unit) : `${s.value}${s.unit}`}</span>
            </li>
          ))}
        </ul>
      )}
      <details className="mt-3 text-xs text-muted">
        <summary className="cursor-pointer select-none hover:text-foreground">Evidence ({insight.cited_event_ids.length} events)</summary>
        <p className="mt-2">
          Facts come from code-computed stats. Validator: {insight.validator.passed ? "passed" : `failed (${insight.validator.violations.join("; ")})`}.
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          {insight.cited_event_ids.map((id) => (
            <button
              key={id}
              onClick={() => onHighlight(id)}
              className="tabular rounded bg-white/5 px-1.5 py-0.5 font-mono hover:bg-warn/20 hover:text-warn"
              aria-label={`Highlight event ${id} on the pitch and timeline`}
            >
              {id}
            </button>
          ))}
        </div>
      </details>
    </article>
  );
}

function PendingCard({ minute }: { minute: number }) {
  return (
    <div className="animate-pulse rounded-xl border border-dashed border-line bg-black/20 p-4" data-testid="insight-pending" aria-live="polite">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{minute}&apos; · Analysing…</div>
      <div className="mt-3 h-3 w-2/3 rounded bg-white/10" />
      <div className="mt-2 h-3 w-full rounded bg-white/5" />
    </div>
  );
}

export function InsightFeed({
  insights,
  pending,
  onHighlight,
}: {
  insights: Insight[];
  pending: PendingInsight[];
  onHighlight: (id: string) => void;
}) {
  const newestFirst = [...insights].sort((a, b) => b.match_second - a.match_second);
  return (
    <section className="panel flex min-h-64 flex-col p-4" aria-label="Insight feed">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-muted">Insights</h2>
      <div className="flex flex-col gap-3 overflow-y-auto lg:max-h-[640px]" aria-live="polite">
        {pending.map((p) => (
          <PendingCard key={p.trigger_id} minute={p.minute} />
        ))}
        {newestFirst.map((i) => (
          <InsightCard key={i.insight_id} insight={i} onHighlight={onHighlight} />
        ))}
        {newestFirst.length === 0 && pending.length === 0 && (
          <p className="text-sm text-muted">Insights appear here when the replay detects a pattern or a key moment.</p>
        )}
      </div>
    </section>
  );
}
