"""Pydantic models for authentication."""

from pydantic import BaseModel


class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user data returned to the client."""
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True