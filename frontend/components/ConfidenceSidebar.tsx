import type { Dashboard } from "@/types";
import { Database, Globe, HardDrive, Gauge, Zap } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface ConfidenceSidebarProps {
  dashboard: Dashboard;
}

export function ConfidenceSidebar({ dashboard }: ConfidenceSidebarProps) {
  const confidencePercent = Math.round(dashboard.critic_confidence * 100);
  const efficiencyPercent = Math.round(dashboard.retrieval_efficiency * 100);

  return (
    <div className="space-y-5 animate-fade-in-up">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Research Metrics
      </h3>

      {/* Citation score ring */}
      <div className="flex items-center gap-4 p-4 rounded-lg border border-border bg-surface/50">
        <CircularProgress
          value={dashboard.verified_claims}
          max={dashboard.total_claims}
        />
        <div>
          <p className="text-sm font-medium text-foreground">Citation Score</p>
          <p className="text-xs text-muted-foreground">
            {dashboard.verified_claims}/{dashboard.total_claims} claims verified
          </p>
        </div>
      </div>

      {/* Critic confidence */}
      <div className="p-4 rounded-lg border border-border bg-surface/50 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Gauge className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">
              Critic Confidence
            </span>
          </div>
          <span
            className={`text-sm font-semibold ${
              confidencePercent >= 80
                ? "text-emerald-400"
                : confidencePercent >= 50
                  ? "text-amber-400"
                  : "text-red-400"
            }`}
          >
            {confidencePercent}%
          </span>
        </div>
        <Progress value={confidencePercent} className="h-1.5" />
      </div>

      {/* Retrieval efficiency */}
      <div className="p-4 rounded-lg border border-border bg-surface/50 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">
              Retrieval Efficiency
            </span>
          </div>
          <span className="text-sm font-semibold text-foreground">
            {efficiencyPercent}%
          </span>
        </div>
        <Progress value={efficiencyPercent} className="h-1.5" />
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-2">
        <StatCard
          icon={HardDrive}
          label="Cache"
          value={dashboard.cache_hits}
        />
        <StatCard
          icon={Database}
          label="Qdrant"
          value={dashboard.qdrant_hits}
        />
        <StatCard
          icon={Globe}
          label="Web"
          value={dashboard.web_searches}
        />
      </div>

      {/* Iterations */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-muted-foreground">
          Iterations needed
        </span>
        <span className="text-xs font-medium text-foreground">
          {dashboard.iterations_needed}
        </span>
      </div>
    </div>
  );
}

// ── Circular Progress Ring ───────────────────────────────────

function CircularProgress({
  value,
  max,
}: {
  value: number;
  max: number;
}) {
  const size = 52;
  const strokeWidth = 4;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = max > 0 ? value / max : 0;
  const offset = circumference - progress * circumference;

  return (
    <div className="relative flex items-center justify-center shrink-0">
      <svg
        width={size}
        height={size}
        className="-rotate-90"
        aria-hidden="true"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-border"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="text-emerald-400 transition-all duration-700 ease-out"
        />
      </svg>
      <span className="absolute text-xs font-semibold text-foreground">
        {value}/{max}
      </span>
    </div>
  );
}

// ── Small Stat Card ──────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Database;
  label: string;
  value: number;
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-border bg-surface/50">
      <Icon className="w-3.5 h-3.5 text-muted-foreground" />
      <span className="text-lg font-semibold text-foreground">{value}</span>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}
