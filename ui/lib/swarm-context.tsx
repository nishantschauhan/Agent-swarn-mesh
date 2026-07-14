"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { io, type Socket } from "socket.io-client";
import type {
  AgentLogEvent,
  ConsoleLine,
  ExecuteResponse,
  SocketConnectionState,
  TaskState,
} from "./types";

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8000";
const PLANNER_URL = process.env.NEXT_PUBLIC_PLANNER_URL ?? "http://localhost:8001";

/** Sliding window cap for the terminal — keeps the DOM and memory bounded under high throughput. */
const MAX_CONSOLE_LINES = 500;

interface SwarmContextValue {
  connectionState: SocketConnectionState;
  connectionError: string | null;
  lines: ConsoleLine[];
  jobId: string | null;
  tasks: TaskState[];
  isSubmitting: boolean;
  submitError: string | null;
  submitGoal: (prompt: string) => Promise<void>;
}

const SwarmContext = createContext<SwarmContextValue | null>(null);

export function SwarmProvider({ children }: { children: ReactNode }) {
  const [connectionState, setConnectionState] = useState<SocketConnectionState>("connecting");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lines, setLines] = useState<ConsoleLine[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<TaskState[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const lineCounter = useRef(0);

  useEffect(() => {
    const socket: Socket = io(GATEWAY_URL, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    socket.on("connect", () => {
      setConnectionState("connected");
      setConnectionError(null);
    });

    socket.on("disconnect", () => {
      setConnectionState("disconnected");
    });

    socket.on("connect_error", (err: Error) => {
      setConnectionState("error");
      setConnectionError(err.message || "Failed to reach gateway");
    });

    socket.on("agent_logs", (raw: unknown) => {
      let event: AgentLogEvent;
      try {
        event = typeof raw === "string" ? JSON.parse(raw) : (raw as AgentLogEvent);
      } catch {
        return; // Malformed payload — drop rather than crash the stream.
      }

      lineCounter.current += 1;
      const line: ConsoleLine = {
        ...event,
        id: `${event.task_id}-${lineCounter.current}`,
        receivedAt: Date.now(),
      };

      setLines((prev) => {
        const next = prev.length >= MAX_CONSOLE_LINES ? prev.slice(1) : prev;
        return [...next, line];
      });

      setTasks((prev) => {
        const idx = prev.findIndex((t) => t.task_id === event.task_id);
        if (idx === -1) return prev;
        const updated = [...prev];
        updated[idx] = {
          ...updated[idx],
          status: event.status,
          updatedAt: Date.now(),
          lastThought: event.agent_thought ?? updated[idx].lastThought,
        };
        return updated;
      });
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const submitGoal = useCallback(async (prompt: string) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const res = await fetch(`${PLANNER_URL}/api/v1/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) {
        throw new Error(`Planner responded with ${res.status} ${res.statusText}`);
      }
      const data: ExecuteResponse = await res.json();
      setJobId(data.job_id);
      setTasks(
        data.tasks.map((t) => ({
          ...t,
          job_id: data.job_id,
          status: "pending" as const,
          updatedAt: Date.now(),
        })),
      );
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "Failed to reach the planner service",
      );
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const value = useMemo<SwarmContextValue>(
    () => ({
      connectionState,
      connectionError,
      lines,
      jobId,
      tasks,
      isSubmitting,
      submitError,
      submitGoal,
    }),
    [connectionState, connectionError, lines, jobId, tasks, isSubmitting, submitError, submitGoal],
  );

  return <SwarmContext.Provider value={value}>{children}</SwarmContext.Provider>;
}

export function useSwarm(): SwarmContextValue {
  const ctx = useContext(SwarmContext);
  if (!ctx) {
    throw new Error("useSwarm must be used within a SwarmProvider");
  }
  return ctx;
}
