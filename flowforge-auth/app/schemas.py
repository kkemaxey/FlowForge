"""Pydantic request/response models — the API contract the frontend sees."""
from pydantic import BaseModel


class UserProfile(BaseModel):
    uid: str
    email: str
    role: str
    is_supervisor: bool


class LoginResponse(BaseModel):
    message: str
    user: UserProfile
