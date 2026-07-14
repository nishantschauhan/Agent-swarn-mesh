import { CheckCircle2, CircleDot, Loader2, XCircle } from "lucide-react";
import type { TaskStatus } from "@/lib/types";

const STATUS_META: Record<
  TaskStatus,
  { label: string; className: string; Icon: typeof CheckCircle2 }
> = {
  pending: { label: "Pending", className: "text-zinc-500", Icon: CircleDot },
  processing: { label: "Processing", className: "text-amber-400", Icon: Loader2 },
  completed: { label: "Completed", className: "text-emerald-400", Icon: CheckCircle2 },
  failed: { label: "Failed", className: "text-red-400", Icon: XCircle },
};

export function StatusIcon({ status, className = "" }: { status: TaskStatus; className?: string }) {
  const meta = STATUS_META[status];
  const spin = status === "processing" ? "animate-spin" : "";
  return (
    <meta.Icon
      className={`h-4 w-4 shrink-0 ${meta.className} ${spin} ${className}`}
      aria-label={meta.label}
    />
  );
}

export function statusLabel(status: TaskStatus): string {
  return STATUS_META[status].label;
}

export function statusTextClass(status: TaskStatus): string {
  return STATUS_META[status].className;
}
