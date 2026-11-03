"""Response schemas for the auth module."""
from pydantic import BaseModel, ConfigDict, computed_field

from app.core.schemas import UtcDatetime
from app.modules.auth.models import UserRole


class UserOut(BaseModel):
    """The current app user, as returned by /auth/session and /auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    firebase_uid: str
    email: str | None
    role: UserRole
    created_at: UtcDatetime

    @computed_field
    @property
    def is_supervisor(self) -> bool:
        """Convenience flag the frontend uses to gate supervisor-only UI."""
        return self.role == UserRole.supervisor
