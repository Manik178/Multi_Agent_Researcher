"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getStreamUrl } from "@/lib/api";
import type {
  AgentTimelineEntry,
  AgentNode,
  AgentStatus,
  VerifiedClaim,
  Dashboard,
  SSEEvent,
} from "@/types";

interface UseResearchStreamReturn {
  agents: AgentTimelineEntry[];
  answer: string | null;
  subQuestions: string[];
  verifiedClaims: VerifiedClaim[];
  followUpQuestions: string[];
  dashboard: Dashboard | null;
  isStreaming: boolean;
  threadId: string | null;
  error: string | null;
}

interface StreamState {
  agents: AgentTimelineEntry[];
  answer: string | null;
  subQuestions: string[];
  verifiedClaims: VerifiedClaim[];
  followUpQuestions: string[];
  dashboard: Dashboard | null;
  threadId: string | null;
  error: string | null;
}

const STATUS_MAP: Record<string, string> = {
  planner: "Planning sub-questions…",
  researcher: "Researching…",
  critic: "Reviewing research quality…",
  writer: "Writing final answer…",
  citation_verifier: "Verifying citations…",
  followup_suggester: "Generating follow-ups…",
};

let entryCounter = 0;

function createTimelineEntry(
  node: AgentNode,
  status: AgentStatus,
  message: string,
  subQuestion?: string,
): AgentTimelineEntry {
  entryCounter += 1;
  return {
    id: `${node}-${entryCounter}`,
    node,
    status,
    message,
    timestamp: new Date(),
    subQuestion,
  };
}

export function useResearchStream(
  question: string | null,
): UseResearchStreamReturn {
  const [state, setState] = useState<StreamState>({
    agents: [],
    answer: null,
    subQuestions: [],
    verifiedClaims: [],
    followUpQuestions: [],
    dashboard: null,
    threadId: null,
    error: null,
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const handleNodeUpdate = useCallback((event: SSEEvent) => {
    if (event.type === "done") return;

    const { node, data, thread_id } = event;
    const nodeData = data as Record<string, unknown>;

    setState((prev) => {
      const updatedAgents = [...prev.agents];

      // Mark previous same-node entries as done (for researcher stacking)
      if (node === "researcher") {
        for (let i = updatedAgents.length - 1; i >= 0; i--) {
          if (
            updatedAgents[i].node === "researcher" &&
            updatedAgents[i].status === "running"
          ) {
            updatedAgents[i] = { ...updatedAgents[i], status: "done" };
          }
        }
      } else {
        // For non-researcher nodes, mark the last running researcher as done
        for (let i = updatedAgents.length - 1; i >= 0; i--) {
          if (
            updatedAgents[i].node === "researcher" &&
            updatedAgents[i].status === "running"
          ) {
            updatedAgents[i] = { ...updatedAgents[i], status: "done" };
            break;
          }
        }
        // Mark previous same-type node as done
        for (let i = updatedAgents.length - 1; i >= 0; i--) {
          if (
            updatedAgents[i].node === node &&
            updatedAgents[i].status === "running"
          ) {
            updatedAgents[i] = { ...updatedAgents[i], status: "done" };
          }
        }
      }

      // Determine sub-question text for researcher rows
      const subQuestion =
        node === "researcher" && Array.isArray(nodeData.sub_questions)
          ? (nodeData.sub_questions as string[])[0]
          : undefined;

      // Add new entry as running
      const newEntry = createTimelineEntry(
        node,
        "running",
        STATUS_MAP[node] ?? "Processing…",
        subQuestion,
      );
      updatedAgents.push(newEntry);

      // Build updated partial state from node data
      let newAnswer = prev.answer;
      let newSubQuestions = prev.subQuestions;
      let newVerifiedClaims = prev.verifiedClaims;
      let newFollowUpQuestions = prev.followUpQuestions;
      let newDashboard = prev.dashboard;

      // Update global dashboard metrics from ANY node's output
      if (
        typeof nodeData.cache_hits === "number" ||
        typeof nodeData.qdrant_hits === "number" ||
        typeof nodeData.total_sources === "number" ||
        node === "critic"
      ) {
        newDashboard = {
          critic_confidence: newDashboard?.critic_confidence ?? 0,
          citation_score: newDashboard?.citation_score ?? 0,
          verified_claims: newDashboard?.verified_claims ?? 0,
          total_claims: newDashboard?.total_claims ?? 0,
          cache_hits:
            (newDashboard?.cache_hits ?? 0) +
            (typeof nodeData.cache_hits === "number" ? nodeData.cache_hits : 0),
          qdrant_hits:
            (newDashboard?.qdrant_hits ?? 0) +
            (typeof nodeData.qdrant_hits === "number" ? nodeData.qdrant_hits : 0),
          web_searches:
            (newDashboard?.web_searches ?? 0) +
            (typeof nodeData.total_sources === "number"
              ? nodeData.total_sources
              : 0),
          iterations_needed: newDashboard?.iterations_needed ?? 1,
          retrieval_efficiency: newDashboard?.retrieval_efficiency ?? 0,
        };
      }

      switch (node) {
        case "planner":
          if (Array.isArray(nodeData.sub_questions)) {
            newSubQuestions = nodeData.sub_questions as string[];
          }
          break;
        case "writer":
          if (typeof nodeData.final_answer === "string") {
            newAnswer = nodeData.final_answer;
          }
          break;
        case "citation_verifier":
          if (Array.isArray(nodeData.verified_claims)) {
            newVerifiedClaims = nodeData.verified_claims as VerifiedClaim[];
          }
          break;
        case "followup_suggester":
          if (Array.isArray(nodeData.follow_up_questions)) {
            newFollowUpQuestions = nodeData.follow_up_questions as string[];
          }
          break;
        case "critic":
          if (newDashboard && typeof nodeData.critic_confidence === "number") {
            newDashboard.critic_confidence = nodeData.critic_confidence;
            if (typeof nodeData.iteration === "number") {
              newDashboard.iterations_needed = nodeData.iteration;
            }
          }
          break;
      }

      return {
        ...prev,
        agents: updatedAgents,
        answer: newAnswer,
        subQuestions: newSubQuestions,
        verifiedClaims: newVerifiedClaims,
        followUpQuestions: newFollowUpQuestions,
        dashboard: newDashboard,
        threadId: thread_id ?? prev.threadId,
      };
    });
  }, []);

  const handleDone = useCallback(() => {
    setState((prev) => {
      // Mark all running agents as done
      const finalAgents = prev.agents.map((a) =>
        a.status === "running" ? { ...a, status: "done" as AgentStatus } : a,
      );

      // Compute final dashboard from accumulated data
      let finalDashboard = prev.dashboard;
      if (prev.verifiedClaims.length > 0) {
        const verifiedCount = prev.verifiedClaims.filter(
          (c) => c.verified,
        ).length;
        const totalClaims = prev.verifiedClaims.length;
        const cacheHits = finalDashboard?.cache_hits ?? 0;
        const qdrantHits = finalDashboard?.qdrant_hits ?? 0;
        const webSearches = finalDashboard?.web_searches ?? 0;
        const totalRetrievals = cacheHits + qdrantHits + webSearches;

        finalDashboard = {
          critic_confidence: finalDashboard?.critic_confidence ?? 0,
          citation_score:
            totalClaims > 0
              ? Math.round((verifiedCount / totalClaims) * 100) / 100
              : 0,
          verified_claims: verifiedCount,
          total_claims: totalClaims,
          cache_hits: cacheHits,
          qdrant_hits: qdrantHits,
          web_searches: webSearches,
          iterations_needed: finalDashboard?.iterations_needed ?? 1,
          retrieval_efficiency:
            totalRetrievals > 0
              ? Math.round(
                  ((cacheHits + qdrantHits) / totalRetrievals) * 100,
                ) / 100
              : 0,
        };
      }

      return {
        ...prev,
        agents: finalAgents,
        dashboard: finalDashboard,
      };
    });
    setIsStreaming(false);
  }, []);

  useEffect(() => {
    if (!question) return;

    // Reset state
    entryCounter = 0;
    setState({
      agents: [],
      answer: null,
      subQuestions: [],
      verifiedClaims: [],
      followUpQuestions: [],
      dashboard: null,
      threadId: null,
      error: null,
    });
    setIsStreaming(true);

    const url = getStreamUrl(question);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.addEventListener("message", (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data as string) as SSEEvent;
        if (parsed.type === "node_update") {
          handleNodeUpdate(parsed);
        }
      } catch {
        // Skip malformed events
      }
    });

    es.addEventListener("done", (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data as string) as SSEEvent;
        if (parsed.type === "done" && parsed.thread_id) {
          setState((prev) => ({ ...prev, threadId: parsed.thread_id }));
        }
      } catch {
        // Skip
      }
      handleDone();
      es.close();
    });

    es.onerror = () => {
      // EventSource auto-reconnects on network errors.
      // If the connection is closed intentionally, readyState === CLOSED.
      if (es.readyState === EventSource.CLOSED) {
        handleDone();
      } else {
        setState((prev) => ({
          ...prev,
          error: "Connection lost. Retrying…",
        }));
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [question, handleNodeUpdate, handleDone]);

  return {
    agents: state.agents,
    answer: state.answer,
    subQuestions: state.subQuestions,
    verifiedClaims: state.verifiedClaims,
    followUpQuestions: state.followUpQuestions,
    dashboard: state.dashboard,
    isStreaming,
    threadId: state.threadId,
    error: state.error,
  };
}
