import type { AuthAdapter, AuthUser } from "./types";

/**
 * Firebase Authentication (free Spark plan, Google sign-in with no OAuth
 * client to configure). Firebase is imported lazily so it costs nothing
 * unless NEXT_PUBLIC_AUTH_PROVIDER=firebase.
 */
async function firebase() {
  const [{ getApps, initializeApp }, authModule] = await Promise.all([
    import("firebase/app"),
    import("firebase/auth"),
  ]);
  const app =
    getApps()[0] ??
    initializeApp({
      apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
      authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
      projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
      appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
    });
  return { auth: authModule.getAuth(app), mod: authModule };
}

function toUser(u: { uid: string; email: string | null } | null): AuthUser | null {
  return u ? { id: u.uid, email: u.email } : null;
}

export const firebaseAdapter: AuthAdapter = {
  name: "firebase",

  async getUser() {
    const { auth } = await firebase();
    await auth.authStateReady();
    return toUser(auth.currentUser);
  },

  onChange(cb) {
    let unsubscribe: (() => void) | null = null;
    let cancelled = false;
    void firebase().then(({ auth, mod }) => {
      if (cancelled) return;
      unsubscribe = mod.onAuthStateChanged(auth, (u) => cb(toUser(u)));
    });
    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  },

  async signInWithGoogle() {
    const { auth, mod } = await firebase();
    const provider = new mod.GoogleAuthProvider();
    try {
      await mod.signInWithPopup(auth, provider);
      return { redirected: false };
    } catch (err) {
      const code = (err as { code?: string }).code;
      // Some mobile browsers block popups; fall back to a full-page redirect.
      if (code === "auth/popup-blocked" || code === "auth/operation-not-supported-in-this-environment") {
        await mod.signInWithRedirect(auth, provider);
        return { redirected: true };
      }
      if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") {
        return { redirected: false };
      }
      throw err;
    }
  },

  async signOut() {
    const { auth } = await firebase();
    await auth.signOut();
  },

  async getAccessToken() {
    const { auth } = await firebase();
    await auth.authStateReady();
    return (await auth.currentUser?.getIdToken()) ?? null;
  },
};
