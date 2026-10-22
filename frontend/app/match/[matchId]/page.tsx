import { Suspense } from "react";
import { HealthBadge } from "@/components/HealthBadge";

async function MatchShell({ params }: { params: Promise<{ matchId: string }> }) {
  const { matchId } = await params;
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">InsideMatch</h1>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-amber-400/15 px-3 py-1 text-xs font-medium text-amber-200">Synthetic data</span>
          <HealthBadge />
        </div>
      </header>
      <p className="text-white/70">Match <code className="text-white">{matchId}</code>: live view coming in Phase 6.</p>
    </main>
  );
}

export default function MatchPage({ params }: PageProps<"/match/[matchId]">) {
  return (
    <Suspense fallback={<main className="flex-1" />}>
      <MatchShell params={params} />
    </Suspense>
  );
}
