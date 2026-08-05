from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class ResponseIntent(str, Enum):
    HEALTH_GUIDANCE = "health_guidance"
    FACILITY_SEARCH = "facility_search"
    MEDICINE = "medicine"
    HOME_REMEDY = "home_remedy"
    AMBULANCE = "ambulance"
    APPOINTMENT = "appointment"
    ANGANWADI = "anganwadi"
    GOVERNMENT_SCHEME = "government_scheme"
    REMINDER = "reminder"
    EMERGENCY = "emergency"
    GENERAL = "general"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EMERGENCY = "emergency"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's message in any supported language.",
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Conversation session identifier.",
    )

    language: Optional[str] = Field(
        default=None,
        description="Optional language hint such as hi, en, bn, mr.",
    )

class AIAction(BaseModel):

    type: str

    page: Optional[str] = None

    button: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str

    response: str

    detected_language: Optional[str] = None

    intent: ResponseIntent = ResponseIntent.GENERAL

    risk_level: RiskLevel = RiskLevel.LOW

    requires_professional_care: bool = False

    emergency: bool = False