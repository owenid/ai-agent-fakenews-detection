from typing import Literal, Optional

from pydantic import BaseModel, Field

Verdict = Literal[
    "likely_credible",
    "mixed_or_uncertain",
    "likely_misinformation",
]

AIVerdict = Literal[
    "true",
    "mostly_true",
    "misleading",
    "false",
    "unverified",
    "satire_or_opinion",
]


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Article text or claim to analyze")
    url: Optional[str] = Field(None, description="URL of the original source, if known")
    source_name: Optional[str] = Field(None, description="Publisher/outlet name, if known")


class KeyClaim(BaseModel):
    claim: str
    assessment: AIVerdict
    explanation: str


class CitedSource(BaseModel):
    name: str
    url: Optional[str] = None
    stance: Literal["supports", "contradicts", "context"] = "context"


class AIFactCheck(BaseModel):
    verdict: AIVerdict = "unverified"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    summary: str = ""
    key_claims: list[KeyClaim] = Field(default_factory=list)
    cited_sources: list[CitedSource] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    ai_score: Optional[float] = Field(None, ge=0, le=100)
    used_web_search: bool = False
    error: Optional[str] = None


class SourceReputation(BaseModel):
    domain: Optional[str] = None
    category: Literal["high_credibility", "known_unreliable", "unknown"] = "unknown"
    score: float = Field(50.0, ge=0, le=100)
    notes: str = ""


class LanguageStyle(BaseModel):
    score: float = Field(..., ge=0, le=100)
    flags: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    source_reputation: SourceReputation
    language_style: LanguageStyle
    ai_fact_check: AIFactCheck
    weights: dict[str, float]


class AnalyzeResponse(BaseModel):
    composite_score: float = Field(..., ge=0, le=100)
    verdict: Verdict
    breakdown: ScoreBreakdown
