import type { GenerationAttempt } from "@/lib/types";

const WHO: Record<string, string> = { foundry: "Foundry draft", mock: "Mock draft", template: "Template" };

/** An honest account of what the grounding validator did with each draft. */
export function summarize(attempts: GenerationAttempt[] | undefined): { tone: "ok" | "warn"; text: string } {
  if (!attempts || attempts.length === 0) return { tone: "warn", text: "Not recorded" };
  const last = attempts.at(-1)!;
  if (attempts.length === 1 && last.passed) return { tone: "ok", text: "Passed first time" };
  if (last.generated_by === "template") return { tone: "warn", text: "Fell back to the template" };
  return { tone: "ok", text: `Draft rejected, regenerated, then passed` };
}

export function GroundingCheck({ attempts }: { attempts?: GenerationAttempt[] }) {
  const summary = summarize(attempts);
  return (
    <div className="mt-2" data-testid="grounding-check">
      <p>
        <span className="font-semibold text-foreground">Grounding check:</span>{" "}
        <span className={summary.tone === "ok" ? "text-accent" : "text-warn"}>{summary.text}</span>
        <span className="text-muted"> · every number, name and cited event is checked against the facts</span>
      </p>
      {attempts && attempts.length > 1 && (
        <ol className="mt-1 list-decimal space-y-0.5 pl-5">
          {attempts.map((a, i) => (
            <li key={i}>
              {WHO[a.generated_by] ?? a.generated_by}: {a.passed ? "passed" : `rejected (${a.violations.join("; ")})`}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
