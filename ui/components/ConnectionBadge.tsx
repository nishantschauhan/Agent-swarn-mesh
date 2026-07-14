"use client";

import { Wifi, WifiOff, Loader2 } from "lucide-react";
import { useSwarm } from "@/lib/swarm-context";

const STATE_META = {
  connected: { label: "Live", className: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10" },
  connecting: { label: "Connecting", className: "text-amber-400 border-amber-400/30 bg-amber-400/10" },
  disconnected: { label: "Disconnected", className: "text-zinc-400 border-zinc-500/30 bg-zinc-500/10" },
  error: { label: "Connection error", className: "text-red-400 border-red-400/30 bg-red-400/10" },
} as const;

export function ConnectionBadge() {
  const { connectionState, connectionError } = useSwarm();
  const meta = STATE_META[connectionState];

  return (
    <div
      className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-mono ${meta.className}`}
      title={connectionError ?? undefined}
    >
      {connectionState === "connected" && <Wifi className="h-3.5 w-3.5" />}
      {connectionState === "connecting" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {(connectionState === "disconnected" || connectionState === "error") && (
        <WifiOff className="h-3.5 w-3.5" />
      )}
      {meta.label}
    </div>
  );
}
