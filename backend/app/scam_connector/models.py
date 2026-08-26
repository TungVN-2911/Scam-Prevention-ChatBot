from typing import Optional

from pydantic import BaseModel, Field

class ScamPattern(BaseModel):
    id: str
    slug: str
    name: str
    category: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    scenario: Optional[str] = Field(default=None)
    target: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    warning_signs: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list)
    prevention: list[str] = Field(default_factory=list)
    if_victim: list[str] = Field(default_factory=list)
    severity: Optional[str] = Field(default=None)
    related_patterns: list[str] = Field(default_factory=list)
    source: dict = Field(default_factory=dict)
    
class ScamCase(BaseModel):
    id: str
    scam_type: str
    title: str
    reported_at: str
    status: str
    channel: str
    amount_lost_vnd: int = 0
    summary: str
    actions_taken: list[str] = Field(default_factory=list)
    
class Hotline(BaseModel):
    id: str
    name: str
    channel_type: str
    contact: str
    organization: str
    when_to_use: str
    scope: str    