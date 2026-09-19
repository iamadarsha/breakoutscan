export interface AuthUser {
  id: string;
  email: string | null;
}

export interface AuthAdapter {
  name: "supabase" | "firebase";
  getUser(): Promise<AuthUser | null>;
  /** Subscribe to sign-in/out; returns an unsubscribe function. */
  onChange(cb: (user: AuthUser | null) => void): () => void;
  /** `redirected: true` means the page is navigating away to finish sign-in. */
  signInWithGoogle(): Promise<{ redirected: boolean }>;
  signOut(): Promise<void>;
  /** Bearer token the API verifies, or null when signed out. */
  getAccessToken(): Promise<string | null>;
}
