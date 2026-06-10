"use client";

import { useState, useCallback, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SearchInput } from "@/components/SearchInput";
import { AgentTimeline } from "@/components/AgentTimeline";
import { ResearchAnswer } from "@/components/ResearchAnswer";
import { VerifiedClaims } from "@/components/VerifiedClaims";
import { FollowUpChips } from "@/components/FollowUpChips";
import { ConfidenceSidebar } from "@/components/ConfidenceSidebar";
import { useResearchStream } from "@/hooks/useResearchStream";
import { getSession, saveSessionToHistory } from "@/lib/api";
import type { SessionResponse } from "@/types";
import { Sparkles } from "lucide-react";

export default function ResearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      }
    >
      <ResearchPageContent />
    </Suspense>
  );
}

function ResearchPageContent() {
  const searchParams = useSearchParams();
  const threadIdParam = searchParams.get("thread_id");

  const [activeQuestion, setActiveQuestion] = useState<string | null>(null);
  const [displayedQuestion, setDisplayedQuestion] = useState<string | null>(
    null,
  );

  // Loaded session (from history navigation)
  const [loadedSession, setLoadedSession] = useState<SessionResponse | null>(
    null,
  );
  const [loadingSession, setLoadingSession] = useState(false);

  // SSE stream hook
  const {
    agents,
    answer,
    subQuestions,
    verifiedClaims,
    followUpQuestions,
    dashboard,
    isStreaming,
    threadId,
    error,
  } = useResearchStream(activeQuestion);

  // Save session to history when streaming completes
  useEffect(() => {
    if (!isStreaming && threadId && displayedQuestion) {
      saveSessionToHistory(threadId, displayedQuestion);
    }
  }, [isStreaming, threadId, displayedQuestion]);

  // Load session from URL param
  useEffect(() => {
    if (!threadIdParam) return;

    let cancelled = false;
    setLoadingSession(true);

    getSession(threadIdParam)
      .then((session) => {
        if (cancelled) return;
        setLoadedSession(session);
        setDisplayedQuestion(session.question);
      })
      .catch(() => {
        // Session not found — ignore
      })
      .finally(() => {
        if (!cancelled) setLoadingSession(false);
      });

    return () => {
      cancelled = true;
    };
  }, [threadIdParam]);

  const handleSearch = useCallback((question: string) => {
    // Reset loaded session
    setLoadedSession(null);
    setDisplayedQuestion(question);
    setActiveQuestion(question);
  }, []);

  const handleFollowUp = useCallback(
    (question: string) => {
      handleSearch(question);
    },
    [handleSearch],
  );

  // Determine what to show
  const isActive =
    isStreaming || loadedSession !== null || answer !== null;
  const showAnswer = loadedSession?.final_answer ?? answer;
  const showSubQuestions = loadedSession ? [] : subQuestions;
  const showClaims = loadedSession?.verified_claims ?? verifiedClaims;
  const showFollowUp =
    loadedSession?.follow_up_questions ?? followUpQuestions;
  const showDashboard = loadedSession?.dashboard ?? dashboard;

  // Landing page
  if (!isActive && !loadingSession) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 pb-20">
        <div className="flex flex-col items-center gap-6 mb-10 animate-fade-in-up">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20">
            <Sparkles className="w-7 h-7 text-primary" />
          </div>
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">
              Research Assistant
            </h1>
            <p className="text-sm text-muted-foreground max-w-md">
              Ask any question. Multiple AI agents will plan, research, critique,
              and synthesize a comprehensive answer.
            </p>
          </div>
        </div>
        <SearchInput onSubmit={handleSearch} />
      </div>
    );
  }

  // Research results layout
  return (
    <div className="flex flex-col min-h-screen">
      {/* Top bar with compact search */}
      <header className="sticky top-0 z-40 flex items-center gap-4 px-6 py-3 border-b border-border bg-background/80 backdrop-blur-lg">
        <div className="flex-1">
          <SearchInput
            onSubmit={handleSearch}
            defaultValue={displayedQuestion ?? ""}
            compact
            isLoading={isStreaming}
          />
        </div>
      </header>

      {/* Loading session state */}
      {loadingSession && (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            Loading session…
          </div>
        </div>
      )}

      {/* Two-column layout */}
      {!loadingSession && (
        <div className="flex-1 flex flex-col lg:flex-row">
          {/* LEFT: Agent Timeline (30%) — only show during streaming */}
          {agents.length > 0 && (
            <aside className="lg:w-[30%] shrink-0 border-b lg:border-b-0 lg:border-r border-border p-5 overflow-y-auto max-h-[40vh] lg:max-h-none">
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-4">
                Agent Activity
              </h2>
              <AgentTimeline agents={agents} />
            </aside>
          )}

          {/* RIGHT: Results (70%) */}
          <div
            className={`flex-1 p-6 lg:p-8 overflow-y-auto ${
              agents.length === 0 ? "max-w-4xl mx-auto w-full" : ""
            }`}
          >
            {/* Current question */}
            {displayedQuestion && (
              <h2 className="text-lg font-semibold text-foreground mb-6">
                {displayedQuestion}
              </h2>
            )}

            {/* Error state */}
            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400 mb-4">
                {error}
              </div>
            )}

            <div className="space-y-8">
              {/* Answer area */}
              <ResearchAnswer
                answer={showAnswer}
                subQuestions={showSubQuestions}
                isStreaming={isStreaming}
              />

              {/* Verified claims */}
              {showClaims.length > 0 && (
                <VerifiedClaims claims={showClaims} />
              )}

              {/* Confidence metrics */}
              {showDashboard && !isStreaming && (
                <ConfidenceSidebar dashboard={showDashboard} />
              )}

              {/* Follow-up questions */}
              {showFollowUp.length > 0 && !isStreaming && (
                <FollowUpChips
                  questions={showFollowUp}
                  onSelect={handleFollowUp}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
