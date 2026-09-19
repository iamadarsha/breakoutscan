import { createClient } from "@/lib/supabase/client";
import type { AuthAdapter, AuthUser } from "./types";

function toUser(u: { id: string; email?: string | null } | null | undefined): AuthUser | null {
  return u ? { id: u.id, email: u.email ?? null } : null;
}

export const supabaseAdapter: AuthAdapter = {
  name: "supabase",

  async getUser() {
    const { data } = await createClient().auth.getUser();
    return toUser(data.user);
  },

  onChange(cb) {
    const {
      data: { subscription },
    } = createClient().auth.onAuthStateChange((_event, session) => {
      cb(toUser(session?.user));
    });
    return () => subscription.unsubscribe();
  },

  async signInWithGoogle() {
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) throw new Error(error.message);
    return { redirected: true };
  },

  async signOut() {
    await createClient().auth.signOut();
  },

  async getAccessToken() {
    const { data } = await createClient().auth.getSession();
    return data.session?.access_token ?? null;
  },
};
