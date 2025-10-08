"""Response models for the chat endpoint."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Reference(BaseModel):
    """Reference to a data source."""
    source: str = Field(..., description="Source of the information (e.g., 'People')")
    person_id: Optional[str] = Field(None, description="Person ID if applicable")


class ChatResponse(BaseModel):
    """Standardized chat response model."""
    answer_text: str = Field(..., description="The response text")
    intent: str = Field(..., description="Intent classification (e.g., 'genel', 'bilgi', 'randevu')")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    references: List[Reference] = Field(default_factory=list, description="List of references")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ErrorResponse(BaseModel):
    """Error response model."""
    answer_text: str = Field(..., description="Error message")
    intent: str = Field(default="genel", description="Intent classification")
    confidence: float = Field(default=0.0, description="Confidence score")
    references: List[Reference] = Field(default_factory=list, description="List of references")
