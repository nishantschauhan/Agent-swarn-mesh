"use client";

import { useSwarm } from "@/lib/swarm-context";
import { StatusIcon, statusLabel, statusTextClass } from "./StatusIcon";

export function TaskPipeline() {
  const { tasks, jobId } = useSwarm();

  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Task Pipeline
        </h2>
        {jobId && (
          <span className="font-mono text-xs text-zinc-600">
            {tasks.filter((t) => t.status === "completed").length}/{tasks.length} done
          </span>
        )}
      </div>

      {tasks.length === 0 ? (
        <p className="text-sm text-zinc-600">
          No active job. Submit a goal above to generate a task plan.
        </p>
      ) : (
        <ol className="space-y-2">
          {tasks.map((task, i) => (
            <li
              key={task.task_id}
              className="rounded-md border border-zinc-800 bg-zinc-950/60 p-3"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-zinc-600">{i + 1}</span>
                <StatusIcon status={task.status} />
                <span className="flex-1 text-sm font-medium text-zinc-100">{task.step}</span>
                <span className={`text-xs font-mono ${statusTextClass(task.status)}`}>
                  {statusLabel(task.status)}
                </span>
              </div>
              {task.detail && (
                <p className="mt-1 pl-6 text-xs text-zinc-500">{task.detail}</p>
              )}
              <p className="mt-1 pl-6 font-mono text-[11px] text-zinc-700">{task.task_id}</p>
              {task.lastThought && (
                <p className="mt-1 line-clamp-2 pl-6 text-xs text-zinc-500">
                  {task.lastThought}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
