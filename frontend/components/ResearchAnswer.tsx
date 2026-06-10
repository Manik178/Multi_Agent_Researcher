"use client";

import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";

interface ResearchAnswerProps {
  answer: string | null;
  subQuestions: string[];
  isStreaming: boolean;
}

export function ResearchAnswer({
  answer,
  subQuestions,
  isStreaming,
}: ResearchAnswerProps) {
  return (
    <div className="space-y-6">
      {/* Sub-question pills */}
      {subQuestions.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Research Questions
          </h3>
          <div className="flex flex-wrap gap-2">
            {subQuestions.map((q, i) => (
              <Badge
                key={i}
                variant="secondary"
                className="px-3 py-1.5 text-xs font-normal bg-surface border border-border text-muted-foreground animate-fade-in-up"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                {q}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Streaming indicator */}
      {isStreaming && !answer && subQuestions.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span
              className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"
              style={{ animationDelay: "300ms" }}
            />
          </div>
          <span>Agents are working on your research…</span>
        </div>
      )}

      {/* Final answer with markdown */}
      {answer && (
        <div className="animate-fade-in-up">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">
            Answer
          </h2>
          <div className="prose-research text-sm">
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>

          {/* Typing cursor while still streaming */}
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary/70 animate-blink ml-0.5 align-text-bottom rounded-sm" />
          )}
        </div>
      )}
    </div>
  );
}
