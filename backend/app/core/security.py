"""Firebase ID-token verification, used as a FastAPI dependency on protected routes."""
import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _firebase_app() -> firebase_admin.App:
    if not firebase_admin._apps:
        cred = (
            credentials.Certificate(settings.firebase_credentials)
            if settings.firebase_credentials
            else credentials.ApplicationDefault()
        )
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Return the decoded Firebase token ({uid, email, ...}) or raise 401."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        return auth.verify_id_token(creds.credentials, app=_firebase_app())
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
