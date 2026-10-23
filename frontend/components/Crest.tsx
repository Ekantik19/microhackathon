import type { TeamMeta } from "@/lib/types";

/** A generated, fictional shield built only from the team's colours and initials. */
export function Crest({ team, size = 40 }: { team: TeamMeta; size?: number }) {
  const initials = team.short_name.slice(0, 1) + (team.team_id[1] ?? "");
  return (
    <svg width={size} height={size * 1.15} viewBox="0 0 40 46" role="img" aria-label={`${team.name} crest (generated)`}>
      <path d="M20 1 L38 7 V22 C38 34 30 41 20 45 C10 41 2 34 2 22 V7 Z" fill={team.primary_color} stroke={team.secondary_color} strokeWidth="2" />
      <path d="M2 18 H38 V24 H2 Z" fill={team.secondary_color} opacity="0.85" />
      <text x="20" y="36" textAnchor="middle" fontSize="11" fontWeight="700" fill={team.secondary_color} fontFamily="system-ui">
        {initials.toUpperCase()}
      </text>
    </svg>
  );
}
