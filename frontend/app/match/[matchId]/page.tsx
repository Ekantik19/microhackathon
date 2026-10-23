import { Suspense } from "react";
import { MatchScreen } from "@/components/MatchScreen";

async function MatchLoader({ params }: { params: Promise<{ matchId: string }> }) {
  const { matchId } = await params;
  return <MatchScreen matchId={matchId} />;
}

export default function MatchPage({ params }: PageProps<"/match/[matchId]">) {
  return (
    <Suspense fallback={<main className="flex-1" />}>
      <MatchLoader params={params} />
    </Suspense>
  );
}
