"""Authentication dependency.

Validates the incoming Firebase ID token from the Authorization: Bearer header
and returns the caller's identity {uid, email}. In dev mode a small set of fake
tokens is accepted so the flow can be demoed without a live Firebase project.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)

# Local-only fake tokens for demos/tests. Ignored unless DEV_MODE is on.
DEV_TOKENS = {
    "dev-supervisor": {"uid": "dev-supervisor-uid", "email": "maria@flowforge.example"},
    "dev-worker": {"uid": "dev-worker-uid", "email": "sam@flowforge.example"},
}


def verify_firebase_token(token: str) -> dict:
    """Verify a real Firebase ID token. firebase_admin is imported lazily so the
    service still runs in dev mode without the dependency configured."""
    import firebase_admin
    from firebase_admin import auth as fb_auth, credentials

    settings = get_settings()
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials)
        firebase_admin.initialize_app(cred)
    decoded = fb_auth.verify_id_token(token)
    return {"uid": decoded["uid"], "email": decoded.get("email", "")}


def get_current_identity(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """FastAPI dependency: turn a bearer token into an identity, or 401."""
    settings = get_settings()
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = creds.credentials

    if settings.dev_mode and token in DEV_TOKENS:
        return DEV_TOKENS[token]

    try:
        return verify_firebase_token(token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
