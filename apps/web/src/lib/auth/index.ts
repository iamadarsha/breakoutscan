import { firebaseAdapter } from "./firebase-adapter";
import { supabaseAdapter } from "./supabase-adapter";
import type { AuthAdapter } from "./types";

export type { AuthAdapter, AuthUser } from "./types";

/** Chosen at build time: NEXT_PUBLIC_AUTH_PROVIDER = "supabase" (default) | "firebase". */
export const auth: AuthAdapter =
  process.env.NEXT_PUBLIC_AUTH_PROVIDER === "firebase" ? firebaseAdapter : supabaseAdapter;
