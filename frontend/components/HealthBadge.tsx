"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/config";

type Health = { status: string; version: string; ai_provider: string; event_source: string; db: string };

export function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/health`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((h: Health) => !cancelled && setHealth(h))
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const ok = health?.status === "ok";
  const label = error ? "API offline" : ok ? `API ok · AI ${health.ai_provider}` : "Checking API…";
  const tone = error ? "bg-red-500/15 text-red-300" : ok ? "bg-emerald-500/15 text-emerald-300" : "bg-white/10 text-white/70";

  return (
    <span data-testid="health-badge" role="status" className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${tone}`}>
      <span className={`h-2 w-2 rounded-full ${error ? "bg-red-400" : ok ? "bg-emerald-400" : "bg-white/50"}`} />
      {label}
    </span>
  );
}
