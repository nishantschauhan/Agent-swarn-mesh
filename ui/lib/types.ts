// Mirrors shared/schemas.py — keep in sync with the backend Pydantic models.

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

/** Payload published on the Redis `agent_logs` Pub/Sub channel and relayed by the gateway. */
export interface AgentLogEvent {
  job_id: string;
  task_id: string;
  status: TaskStatus;
  message: string;
  agent_thought?: string | null;
}

/** One step of an LLM-generated plan, as returned by the planner. */
export interface TaskSummary {
  task_id: string;
  step: string;
  detail: string;
}

/** Response body of POST /api/v1/execute. */
export interface ExecuteResponse {
  job_id: string;
  task_ids: string[];
  tasks: TaskSummary[];
  status: string;
}

/** Client-side view of a task: the planner summary plus live status derived from agent_logs. */
export interface TaskState extends TaskSummary {
  job_id: string;
  status: TaskStatus;
  updatedAt: number;
  lastThought?: string;
}

/** A single line in the Agent Console terminal. */
export interface ConsoleLine extends AgentLogEvent {
  id: string;
  receivedAt: number;
}

export type SocketConnectionState =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";
