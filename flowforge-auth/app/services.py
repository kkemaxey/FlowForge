"""Business layer — pure functions, no FastAPI and no database.

This is the "core code" the unit tests target. Keeping the supervisor-role
decision here (instead of inside the route handlers) is deliberate: it makes
the rule testable in isolation and keeps auth logic out of the controllers.
"""

SUPERVISOR_ROLE = "supervisor"
WORKER_ROLE = "worker"


def assign_role(email: str, supervisor_emails: list[str]) -> str:
    """Decide a user's role from their email and the supervisor allowlist."""
    allow = {e.lower() for e in supervisor_emails}
    if email and email.lower() in allow:
        return SUPERVISOR_ROLE
    return WORKER_ROLE


def is_supervisor(role: str) -> bool:
    """True only for the supervisor role. This is the gate other endpoints use."""
    return role == SUPERVISOR_ROLE


def build_profile(uid: str, email: str, role: str) -> dict:
    """Shape the user profile returned by the API, with the derived flag."""
    return {
        "uid": uid,
        "email": email,
        "role": role,
        "is_supervisor": is_supervisor(role),
    }
