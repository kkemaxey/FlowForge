import { getApp, getApps, initializeApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// False until the NEXT_PUBLIC_FIREBASE_* values are set (see .env.example). Firebase throws on any call
// without them, so callers check this first.
export const FIREBASE_CONFIGURED = Boolean(firebaseConfig.apiKey);

// Initialized lazily so pages that never touch auth don't need Firebase config.
export function getFirebaseAuth(): Auth {
  const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  return getAuth(app);
}
