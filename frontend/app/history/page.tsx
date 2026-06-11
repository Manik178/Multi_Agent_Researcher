"use client";

import { useState, useEffect, useRef } from "react";
import { getSessionHistory, getSession } from "@/lib/api";
import { SessionCard } from "@/components/SessionCard";
import { Button } from "@/components/ui/button";
import type { SessionResponse, StoredSession } from "@/types";
import { Clock, Search } from "lucide-react";

interface LoadedSessionEntry {
  stored: StoredSession;
  session: SessionResponse | null;
  isLoading: boolean;
}

const PAGE_SIZE = 12;

export default function HistoryPage() {
  const [entries, setEntries] = useState<LoadedSessionEntry[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const fetchedIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    const stored = getSessionHistory();

    // Initialize with loading state
    const initial: LoadedSessionEntry[] = stored.map((s) => ({
      stored: s,
      session: null,
      isLoading: true,
    }));
    setEntries(initial);
    setInitialized(true);
  }, []);

  useEffect(() => {
    if (!initialized) return;

    // Fetch session details only for the visible slice
    entries.slice(0, visibleCount).forEach((entry) => {
      const threadId = entry.stored.threadId;
      if (!fetchedIds.current.has(threadId)) {
        fetchedIds.current.add(threadId);

        getSession(threadId)
          .then((session) => {
            setEntries((prev) =>
              prev.map((p) =>
                p.stored.threadId === threadId
                  ? { ...p, session, isLoading: false }
                  : p,
              ),
            );
          })
          .catch(() => {
            setEntries((prev) =>
              prev.map((p) =>
                p.stored.threadId === threadId
                  ? { ...p, isLoading: false }
                  : p,
              ),
            );
          });
      }
    });
  }, [initialized, visibleCount, entries]);

  if (!initialized) return null;

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 border border-primary/20">
          <Clock className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">
            Research History
          </h1>
          <p className="text-sm text-muted-foreground">
            Your past research sessions.
          </p>
        </div>
      </div>

      {/* Session grid */}
      {entries.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-surface border border-border">
            <Search className="w-6 h-6 text-muted-foreground/30" />
          </div>
          <p className="text-sm text-muted-foreground">
            No research sessions yet. Start by asking a question.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2">
            {entries.slice(0, visibleCount).map((entry) => (
              <SessionCard
                key={entry.stored.threadId}
                threadId={entry.stored.threadId}
                session={entry.session}
                storedQuestion={entry.stored.question}
                storedTimestamp={entry.stored.timestamp}
                isLoading={entry.isLoading}
              />
            ))}
          </div>
          
          {visibleCount < entries.length && (
            <div className="flex justify-center pt-4 pb-8">
              <Button 
                variant="outline" 
                onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
                className="w-full sm:w-auto"
              >
                Load More Sessions
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
