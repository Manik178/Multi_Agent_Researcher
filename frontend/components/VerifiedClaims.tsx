import { CheckCircle2, AlertTriangle } from "lucide-react";
import type { VerifiedClaim } from "@/types";

interface VerifiedClaimsProps {
  claims: VerifiedClaim[];
}

export function VerifiedClaims({ claims }: VerifiedClaimsProps) {
  if (claims.length === 0) return null;

  const verifiedCount = claims.filter((c) => c.verified).length;

  return (
    <div className="space-y-3 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Verified Claims
        </h3>
        <span className="text-xs text-muted-foreground">
          {verifiedCount}/{claims.length} verified
        </span>
      </div>

      <div className="space-y-2">
        {claims.map((claim, i) => (
          <div
            key={i}
            className="flex items-start gap-3 p-3 rounded-lg border border-border bg-surface/50 animate-fade-in-up"
            style={{ animationDelay: `${i * 75}ms` }}
          >
            {claim.verified ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            )}

            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground leading-relaxed">
                {claim.claim}
              </p>
            </div>

            {claim.source_index > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-medium bg-primary/10 text-primary border border-primary/20 shrink-0">
                {claim.source_index}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
