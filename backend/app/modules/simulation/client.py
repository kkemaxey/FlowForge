"""HTTP client for the simulator. Auth is off for the MVP, so it sends no credentials.

SIM_API_URL sets the server. The default suits running inside the backend container.
"""
import os

import httpx


def client_from_env() -> httpx.Client:
    """An HTTP client pointed at SIM_API_URL."""
    # base_url lets callers write client.get("/api/v1/...") without the host.
    return httpx.Client(base_url=os.getenv("SIM_API_URL", "http://localhost:8080"), timeout=10)


class ApiCallError(RuntimeError):
    """An error response from the API, with its status code and machine-readable code."""

    def __init__(self, response: httpx.Response) -> None:
        try:
            body = response.json()
        except ValueError:
            # Not JSON (e.g. a proxy error page): keep the raw text.
            body = {"detail": response.text}
        self.status_code = response.status_code
        # Our API's error bodies look like {"detail": "...", "code": "version_conflict"}.
        self.code = body.get("code") if isinstance(body, dict) else None
        super().__init__(f"{response.request.method} {response.request.url.path} -> {response.status_code}: {body}")


def checked(response: httpx.Response) -> httpx.Response:
    """Return the response if it succeeded (2xx); raise ApiCallError if it's a 4xx/5xx."""
    if response.is_error:
        raise ApiCallError(response)
    return response
