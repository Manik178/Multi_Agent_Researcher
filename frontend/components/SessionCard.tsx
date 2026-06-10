import Link from "next/link";
import { CheckCircle2, Clock } from "lucide-react";
import type { SessionResponse } from "@/types";

interface SessionCardProps {
  threadId: string;
  session: SessionResponse | null;
  storedQuestion: string;
  storedTimestamp: number;
  isLoading: boolean;
}

export function SessionCard({
  threadId,
  session,
  storedQuestion,
  storedTimestamp,
  isLoading,
}: SessionCardProps) {
  const question = session?.question ?? storedQuestion;
  const verifiedCount =
    session?.verified_claims.filter((c) => c.verified).length ?? 0;
  const totalClaims = session?.verified_claims.length ?? 0;
  const confidence = session?.dashboard.critic_confidence ?? 0;
  const confidencePercent = Math.round(confidence * 100);

  return (
    <Link
      href={`/?thread_id=${threadId}`}
      className="group block p-5 rounded-xl border border-border bg-surface/50 hover:border-primary/30 hover:bg-surface transition-all duration-200"
    >
      {/* Question */}
      <p className="text-sm font-medium text-foreground line-clamp-2 group-hover:text-primary transition-colors">
        {question}
      </p>

      {/* Meta row */}
      <div className="flex items-center gap-3 mt-3 flex-wrap">
        {/* Date */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="w-3 h-3" />
          {formatDate(storedTimestamp)}
        </div>

        {/* Verified claims badge */}
        {!isLoading && session && totalClaims > 0 && (
          <div className="flex items-center gap-1 text-xs text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            {verifiedCount}/{totalClaims} verified
          </div>
        )}

        {/* Confidence */}
        {!isLoading && session && confidence > 0 && (
          <span
            className={`text-xs font-medium px-1.5 py-0.5 rounded border ${
              confidencePercent >= 80
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : confidencePercent >= 50
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  : "bg-red-500/10 text-red-400 border-red-500/20"
            }`}
          >
            {confidencePercent}% confidence
          </span>
        )}

        {/* Loading skeleton */}
        {isLoading && (
          <div className="h-3 w-24 rounded bg-muted animate-pulse" />
        )}
      </div>
    </Link>
  );
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}
