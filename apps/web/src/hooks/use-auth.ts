"use client";

import { useEffect, useState } from "react";
import { auth, type AuthUser } from "@/lib/auth";

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    auth
      .getUser()
      .then((u) => {
        if (alive) setUser(u);
      })
      .catch(() => {
        if (alive) setUser(null);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    const unsubscribe = auth.onChange((u) => {
      if (alive) setUser(u);
    });

    return () => {
      alive = false;
      unsubscribe();
    };
  }, []);

  return { user, loading, userId: user?.id ?? null };
}

export function useRequireAuth() {
  const authState = useAuth();
  // Feature-level gating (watchlist, alerts) renders the sign-in prompt itself;
  // this provides a typed non-null userId for components only shown when signed in.
  return authState as typeof authState & { userId: string };
}
