"use client";

import type { AgentTimelineEntry, AgentNode } from "@/types";
import { Search, ClipboardList, Eye, PenTool, ShieldCheck, Lightbulb } from "lucide-react";

const AGENT_CONFIG: Record<
  AgentNode,
  { icon: typeof Search; label: string; emoji: string }
> = {
  planner: { icon: ClipboardList, label: "Planner", emoji: "📋" },
  researcher: { icon: Search, label: "Researcher", emoji: "🔍" },
  critic: { icon: Eye, label: "Critic", emoji: "🧐" },
  writer: { icon: PenTool, label: "Writer", emoji: "✍️" },
  citation_verifier: { icon: ShieldCheck, label: "Verifier", emoji: "✅" },
  followup_suggester: { icon: Lightbulb, label: "Follow-up", emoji: "💡" },
};

interface AgentTimelineProps {
  agents: AgentTimelineEntry[];
}

export function AgentTimeline({ agents }: AgentTimelineProps) {
  if (agents.length === 0) return null;

  return (
    <div className="relative">
      {/* Vertical connecting line */}
      <div className="absolute left-4 top-6 bottom-6 w-px bg-border" />

      <div className="space-y-1">
        {agents.map((entry, index) => {
          const config = AGENT_CONFIG[entry.node];

          return (
            <div
              key={entry.id}
              className="relative flex items-start gap-3 pl-1 pr-2 py-2 animate-slide-in-left"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              {/* Status dot */}
              <div className="relative z-10 flex items-center justify-center w-7 h-7 rounded-full bg-surface border border-border shrink-0 mt-0.5">
                {entry.status === "running" ? (
                  <div className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse-indigo" />
                ) : entry.status === "done" ? (
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                ) : entry.status === "retrying" ? (
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
                ) : (
                  <div className="w-2.5 h-2.5 rounded-full bg-muted-foreground/30" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm" aria-hidden="true">
                    {config.emoji}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {config.label}
                  </span>
                  <StatusBadge status={entry.status} />
                </div>

                {/* Sub-question text for researcher nodes */}
                {entry.node === "researcher" && entry.subQuestion && (
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed line-clamp-2">
                    {entry.subQuestion}
                  </p>
                )}

                {/* Status message for non-researcher nodes */}
                {entry.node !== "researcher" && entry.status === "running" && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {entry.message}
                  </p>
                )}

                {/* Timestamp */}
                <p className="text-[10px] text-muted-foreground/50 mt-1">
                  {formatTimestamp(entry.timestamp)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: AgentTimelineEntry["status"] }) {
  const styles = {
    running:
      "bg-primary/10 text-primary border-primary/20",
    done: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    retrying: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    waiting: "bg-muted text-muted-foreground border-border",
  };

  const labels = {
    running: "Running",
    done: "Done",
    retrying: "Retrying",
    waiting: "Waiting",
  };

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
