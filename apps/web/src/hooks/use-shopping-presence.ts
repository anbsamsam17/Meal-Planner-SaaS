// apps/web/src/hooks/use-shopping-presence.ts
// Track les utilisateurs connectés à la shopping list via Supabase Presence
// Retourne la liste des membres du foyer actuellement en ligne
"use client";

import { useEffect, useState } from "react";
import { createBrowserClient } from "@/lib/supabase/client";

export interface OnlineUser {
  userId: string;
  displayName: string;
}

/**
 * Track la presence des utilisateurs sur la shopping list d'un plan.
 * Utilise Supabase Presence pour detecter les connexions/deconnexions.
 *
 * @param planId - UUID du plan
 * @param currentUser - Info de l'utilisateur courant
 * @returns Liste des utilisateurs en ligne (sans l'utilisateur courant)
 */
export function useShoppingPresence(
  planId: string | null,
  currentUser: { userId: string; displayName: string } | null,
) {
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);

  useEffect(() => {
    if (!planId || !currentUser) return;

    const supabase = createBrowserClient();
    const channelName = `presence:shopping:${planId}`;

    const channel = supabase.channel(channelName, {
      config: { presence: { key: currentUser.userId } },
    });

    channel
      .on("presence", { event: "sync" }, () => {
        const state = channel.presenceState<{
          userId: string;
          displayName: string;
        }>();

        const users: OnlineUser[] = [];
        for (const [key, presences] of Object.entries(state)) {
          if (key === currentUser.userId) continue;
          const latest = presences[presences.length - 1];
          if (latest) {
            users.push({
              userId: latest.userId,
              displayName: latest.displayName,
            });
          }
        }
        setOnlineUsers(users);
      })
      .subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
          await channel.track({
            userId: currentUser.userId,
            displayName: currentUser.displayName,
          });
        }
      });

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [planId, currentUser]);

  return onlineUsers;
}
