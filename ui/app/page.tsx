import { ConnectionBadge } from "@/components/ConnectionBadge";
import { TriggerPanel } from "@/components/TriggerPanel";
import { TaskPipeline } from "@/components/TaskPipeline";
import { AgentConsole } from "@/components/AgentConsole";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-800 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-100">
            Agent Swarm Mesh
          </h1>
          <p className="text-xs text-zinc-500">Real-time multi-agent control deck</p>
        </div>
        <ConnectionBadge />
      </header>

      <main className="flex flex-1 flex-col gap-4 overflow-hidden p-6">
        <TriggerPanel />

        <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-5">
          <div className="overflow-y-auto lg:col-span-2">
            <TaskPipeline />
          </div>
          <div className="flex lg:col-span-3">
            <AgentConsole />
          </div>
        </div>
      </main>
    </div>
  );
}
