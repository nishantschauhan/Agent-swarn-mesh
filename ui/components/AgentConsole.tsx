"use client";

import { useEffect, useRef, useState } from "react";
import { useSwarm } from "@/lib/swarm-context";
import type { ConsoleLine } from "@/lib/types";
import { statusTextClass } from "./StatusIcon";

function formatTime(ms: number): string {
  return new Date(ms).toLocaleTimeString("en-US", { hour12: false });
}

function LineRow({ line }: { line: ConsoleLine }) {
  const text = line.agent_thought ?? line.message;
  return (
    <div className="flex gap-2 py-0.5 text-xs leading-relaxed">
      <span className="shrink-0 text-zinc-600">{formatTime(line.receivedAt)}</span>
      <span className={`w-20 shrink-0 font-semibold uppercase ${statusTextClass(line.status)}`}>
        [{line.status}]
      </span>
      <span className="shrink-0 text-zinc-500">{line.task_id.slice(0, 8)}</span>
      <span className="whitespace-pre-wrap break-words text-zinc-300">{text}</span>
    </div>
  );
}

/** Scroll-locked terminal: auto-scrolls on new lines unless the user has scrolled up to read history. */
export function AgentConsole() {
  const { lines } = useSwarm();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (!autoScroll || !scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [lines, autoScroll]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 32;
    setAutoScroll(atBottom);
  }

  function jumpToLatest() {
    setAutoScroll(true);
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }

  return (
    <section className="flex flex-1 flex-col rounded-lg border border-zinc-800 bg-black/60">
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Agent Console
        </h2>
        <div className="flex items-center gap-2">
          {!autoScroll && (
            <button
              onClick={jumpToLatest}
              className="rounded border border-zinc-700 px-2 py-0.5 text-[11px] text-zinc-400 hover:border-emerald-500 hover:text-emerald-400"
            >
              Jump to latest
            </button>
          )}
          <span className="font-mono text-[11px] text-zinc-600">{lines.length} lines</span>
        </div>
      </div>
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="min-h-[360px] flex-1 overflow-y-auto px-4 py-2 font-mono"
      >
        {lines.length === 0 ? (
          <p className="text-xs text-zinc-600">Waiting for agent activity...</p>
        ) : (
          lines.map((line) => <LineRow key={line.id} line={line} />)
        )}
      </div>
    </section>
  );
}
