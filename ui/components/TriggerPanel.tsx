"use client";

import { useState, type FormEvent } from "react";
import { Send, Loader2, AlertTriangle } from "lucide-react";
import { useSwarm } from "@/lib/swarm-context";

export function TriggerPanel() {
  const { submitGoal, isSubmitting, submitError, jobId } = useSwarm();
  const [prompt, setPrompt] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || isSubmitting) return;
    try {
      await submitGoal(trimmed);
      setPrompt("");
    } catch {
      // surfaced via submitError below
    }
  }

  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        Trigger Panel
      </h2>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isSubmitting}
          placeholder="Analyze the tech trends for software engineering and summarize the top 3 tools..."
          className="flex-1 rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isSubmitting || !prompt.trim()}
          className="flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-400"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          {isSubmitting ? "Dispatching..." : "Execute"}
        </button>
      </form>

      {submitError && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-red-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          {submitError}
        </p>
      )}

      {jobId && !submitError && (
        <p className="mt-2 text-xs text-zinc-500">
          Latest job: <span className="font-mono text-zinc-400">{jobId}</span>
        </p>
      )}
    </section>
  );
}
