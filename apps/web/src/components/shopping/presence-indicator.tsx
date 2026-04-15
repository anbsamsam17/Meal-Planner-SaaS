// apps/web/src/components/shopping/presence-indicator.tsx
// Badge indiquant les autres membres du foyer connectés à la shopping list
"use client";

import type { OnlineUser } from "@/hooks/use-shopping-presence";

interface PresenceIndicatorProps {
  onlineUsers: OnlineUser[];
}

export function PresenceIndicator({ onlineUsers }: PresenceIndicatorProps) {
  if (onlineUsers.length === 0) return null;

  const names = onlineUsers.map((u) => u.displayName);
  const label =
    names.length === 1
      ? `${names[0]} est connecté(e)`
      : `${names.slice(0, -1).join(", ")} et ${names[names.length - 1]} sont connecté(e)s`;

  return (
    <div
      className="flex items-center gap-2 rounded-full bg-green-50 px-3 py-1.5 text-xs text-green-700
        dark:bg-green-950 dark:text-green-300"
      role="status"
      aria-live="polite"
    >
      <span
        className="inline-block h-2 w-2 rounded-full bg-green-500 animate-pulse"
        aria-hidden="true"
      />
      {label}
    </div>
  );
}
