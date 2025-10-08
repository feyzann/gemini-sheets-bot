"""Request models for the chat endpoint."""

from typing import Optional
from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """User information from the request."""
    name: Optional[str] = Field(None, description="User's full name")
    phone: Optional[str] = Field(None, description="User's phone number in E.164 format")
    locale: Optional[str] = Field(None, description="User's locale (e.g., tr-TR)")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User's message", min_length=1)
    user: Optional[UserInfo] = Field(None, description="Optional user information")
