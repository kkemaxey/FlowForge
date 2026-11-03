"""HTTP client for the simulator and order generator, authenticated as a Firebase service user.

The simulator signs in like any console user (email/password via Firebase's REST API), so the
backend's normal token check applies and production code has no bypass. Env vars:
SIM_API_URL, SIM_EMAIL, SIM_PASSWORD, FIREBASE_WEB_API_KEY.
"""
import os
import time
from collections.abc import Generator

import httpx

# Firebase's REST endpoint for email/password sign-in. It returns an ID token.
SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
# Sign in again this many seconds before the token would expire, to be safe.
REFRESH_MARGIN_S = 120


class FirebasePasswordAuth(httpx.Auth):
    """Attach a Firebase ID token, signing in again shortly before it expires (tokens last 1 hour).

    httpx calls auth_flow() for every request the client sends, so the token handling is automatic.
    """

    def __init__(self, email: str, password: str, api_key: str) -> None:
        self.email, self.password, self.api_key = email, password, api_key
        # No token until the first request triggers a sign-in.
        self._token: str | None = None
        self._expires_at = 0.0

    def _sign_in(self) -> None:
        """Exchange email + password for a fresh ID token."""
        response = httpx.post(
            SIGN_IN_URL,
            params={"key": self.api_key},
            json={"email": self.email, "password": self.password, "returnSecureToken": True},
            timeout=10,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Firebase sign-in for {self.email} failed: {response.text}")
        body = response.json()
        self._token = body["idToken"]
        # expiresIn is in seconds (usually 3600). Plan to refresh a little before then.
        self._expires_at = time.monotonic() + int(body["expiresIn"]) - REFRESH_MARGIN_S

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Add 'Authorization: Bearer <token>' to the request; retry once with a new token on 401."""
        # No token yet, or it's about to expire: sign in first.
        if self._token is None or time.monotonic() >= self._expires_at:
            self._sign_in()
        request.headers["Authorization"] = f"Bearer {self._token}"
        # Send the request and get the response back.
        response = yield request
        # The backend rejected the token (e.g. revoked): sign in again and resend once.
        if response.status_code == 401:
            self._sign_in()
            request.headers["Authorization"] = f"Bearer {self._token}"
            yield request


def client_from_env() -> httpx.Client:
    """An HTTP client pointed at SIM_API_URL and signed in as SIM_EMAIL."""
    # Fail early with a clear message if any credential is missing.
    missing = [name for name in ("SIM_EMAIL", "SIM_PASSWORD", "FIREBASE_WEB_API_KEY") if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Set {', '.join(missing)} so the simulator can sign in. "
            "`cli seed` creates the SIM_EMAIL Firebase user; the web API key is in Firebase project settings."
        )
    auth = FirebasePasswordAuth(os.environ["SIM_EMAIL"], os.environ["SIM_PASSWORD"], os.environ["FIREBASE_WEB_API_KEY"])
    # base_url lets callers write client.get("/api/v1/...") without the host.
    return httpx.Client(base_url=os.getenv("SIM_API_URL", "http://localhost:8000"), auth=auth, timeout=10)


class ApiCallError(RuntimeError):
    """An error response from the API, with its status code and machine-readable code."""

    def __init__(self, response: httpx.Response) -> None:
        try:
            body = response.json()
        except ValueError:
            # Not JSON (e.g. a proxy error page): keep the raw text.
            body = {"detail": response.text}
        self.status_code = response.status_code
        # Our API's error bodies look like {"detail": "...", "code": "state_conflict"}.
        self.code = body.get("code") if isinstance(body, dict) else None
        super().__init__(f"{response.request.method} {response.request.url.path} -> {response.status_code}: {body}")


def checked(response: httpx.Response) -> httpx.Response:
    """Return the response if it succeeded (2xx); raise ApiCallError if it's a 4xx/5xx."""
    if response.is_error:
        raise ApiCallError(response)
    return response
