"""Pydantic schemas for the multi-agent research system."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    """Categories for RFP requirements."""

    FEATURES = "features"
    INTEGRATION = "integration"
    LICENSING = "licensing"
    ROI = "roi"
    SUPPORT = "support"
    TIMELINE = "timeline"
    PRESENTATION = "presentation"
    EVALUATION = "evaluation"
    IMPLEMENTATION = "implementation"
    USERS = "users"
    CAPABILITIES = "capabilities"


class Requirement(BaseModel):
    """A single requirement extracted from an RFP."""

    id: str = Field(..., description="Unique identifier for the requirement")
    text: str = Field(..., description="The requirement text")
    category: RequirementCategory = Field(..., description="Requirement category")
    priority: str = Field(default="medium", description="Priority level: critical, high, medium, low")
    business_impact: str = Field(default="", description="Business impact description")
    evaluation_weight: float = Field(default=0.0, description="Evaluation weighting if specified")
    source_section: str = Field(default="", description="Source section in RFP document")


class ContactInfo(BaseModel):
    """Contact information for RFP."""
    
    name: str = Field(default="", description="Contact person name")
    title: str = Field(default="", description="Contact person title")
    email: str = Field(default="", description="Contact email address")
    phone: str = Field(default="", description="Contact phone number")
    organization: str = Field(default="", description="Organization name")


class PresentationDetails(BaseModel):
    """Presentation requirements and details."""
    
    date: str = Field(default="", description="Presentation date")
    location: str = Field(default="", description="Presentation location")
    duration: str = Field(default="", description="Presentation duration")
    format: str = Field(default="", description="Presentation format requirements")
    attendees: List[str] = Field(default_factory=list, description="Expected attendees")
    topics_to_cover: List[str] = Field(default_factory=list, description="Required presentation topics")


class TimelineItem(BaseModel):
    """A timeline milestone or deadline."""
    
    milestone: str = Field(..., description="Milestone description")
    date: str = Field(..., description="Date or deadline")
    status: str = Field(default="pending", description="Status of milestone")


class EvaluationCriteria(BaseModel):
    """Evaluation criteria for the RFP."""
    
    criterion: str = Field(..., description="Evaluation criterion")
    weight: float = Field(default=0.0, description="Weight/importance (0.0-1.0)")
    description: str = Field(default="", description="Detailed description of criterion")
    scoring_method: str = Field(default="", description="How this criterion is scored")


class RFPMeta(BaseModel):
    """Comprehensive metadata about the RFP document."""

    title: str = Field(..., description="Title of the RFP")
    version: str = Field(default="1.0", description="Version of the RFP")
    deadline_iso: str = Field(..., description="Main deadline in ISO format")
    purpose: str = Field(default="", description="Purpose and background of the RFP")
    organization: str = Field(default="", description="Requesting organization")
    project_description: str = Field(default="", description="Project or service description")
    budget_indication: str = Field(default="", description="Budget information if provided")
    contract_duration: str = Field(default="", description="Expected contract duration")
    presentation_details: Optional[PresentationDetails] = Field(None, description="Presentation requirements")
    timeline: List[TimelineItem] = Field(default_factory=list, description="Project timeline and milestones")
    evaluation_criteria: List[EvaluationCriteria] = Field(default_factory=list, description="Evaluation criteria")
    contact_info: List[ContactInfo] = Field(default_factory=list, description="Contact information")
    submission_requirements: List[str] = Field(default_factory=list, description="Submission format and requirements")
    special_conditions: List[str] = Field(default_factory=list, description="Special terms and conditions")


class CompanyProfile(BaseModel):
    """Flexible company profile information with LLM-friendly structure."""

    name: str = Field(..., description="Company name")
    overview: str = Field(default="", description="Company overview and description")
    hq: str = Field(default="", description="Headquarters location")
    sites: List[str] = Field(default_factory=list, description="List of company sites")
    industry: str = Field(default="", description="Primary industry sector")
    size: str = Field(default="", description="Company size description (flexible format)")
    leadership: List[str] = Field(default_factory=list, description="Key leadership personnel")
    financial_info: str = Field(default="", description="Financial information as text description")
    certifications: List[str] = Field(default_factory=list, description="Certifications and accreditations")
    technology_stack: List[str] = Field(default_factory=list, description="Technology platforms and tools")
    service_areas: List[str] = Field(default_factory=list, description="Primary service offerings")
    market_position: str = Field(default="", description="Market positioning and competitive advantages")
    recent_projects: List[str] = Field(default_factory=list, description="Recent relevant projects")
    partnerships: List[str] = Field(default_factory=list, description="Strategic partnerships")
    
    # Flexible additional information field for LLM-analyzed data
    additional_info: str = Field(default="", description="Additional company information from LLM analysis")


class Evidence(BaseModel):
    """Evidence supporting a requirement mapping."""

    source_url: str = Field(..., description="Source URL for the evidence")
    snippet: str = Field(..., description="Relevant text snippet")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the evidence"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class MappedInsight(BaseModel):
    """An insight mapping a requirement to evidence."""

    requirement_id: str = Field(..., description="ID of the requirement")
    rationale: str = Field(..., description="Rationale for the mapping")
    supporting_evidence_idx: List[int] = Field(
        default_factory=list, description="Indices of supporting evidence"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the mapping"
    )


class ResearchFindings(BaseModel):
    """Output from the ResearchAgent."""

    rfp_meta: RFPMeta = Field(..., description="RFP metadata")
    extracted_requirements: List[Requirement] = Field(
        default_factory=list, description="Extracted requirements"
    )
    company_profile: CompanyProfile = Field(..., description="Company profile")
    evidence: List[Evidence] = Field(default_factory=list, description="Collected evidence")
    mapped_insights: List[MappedInsight] = Field(
        default_factory=list, description="Requirement-evidence mappings"
    )


class Gap(BaseModel):
    """A gap identified by the ValidatorAgent."""

    requirement_id: str = Field(..., description="ID of the requirement with gaps")
    why: str = Field(..., description="Explanation of why there's a gap")
    suggested_queries: List[str] = Field(
        default_factory=list, description="Suggested queries to fill the gap"
    )


class ValidationReport(BaseModel):
    """Enhanced output from the ValidatorAgent with RFP validation."""

    coverage_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall coverage score"
    )
    rfp_validation_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="RFP document validation score"
    )
    extraction_accuracy: float = Field(
        default=0.0, ge=0.0, le=1.0, description="RFP extraction accuracy score"
    )
    gaps: List[Gap] = Field(default_factory=list, description="Identified gaps")
    quality_notes: List[str] = Field(
        default_factory=list, description="Quality assessment notes"
    )
    rfp_validation_notes: List[str] = Field(
        default_factory=list, description="RFP document validation notes"
    )
    is_sufficient: bool = Field(..., description="Whether findings are sufficient")


class BidSection(BaseModel):
    """A section in the bid outline."""

    title: str = Field(..., description="Section title")
    markdown: str = Field(..., description="Section content in markdown")


class BidOutline(BaseModel):
    """Output from the Writer agent."""

    sections: List[BidSection] = Field(default_factory=list, description="Bid sections")


class SystemState(BaseModel):
    """Shared state for the orchestration system."""

    run_id: str = Field(..., description="Unique run identifier")
    rfp_path: Optional[str] = Field(None, description="Path to RFP document")
    company_name: str = Field(..., description="Target company name")
    requirements: List[Requirement] = Field(
        default_factory=list, description="Extracted requirements"
    )
    queries_run: List[str] = Field(
        default_factory=list, description="Queries that have been executed"
    )
    evidence: List[Evidence] = Field(
        default_factory=list, description="Collected evidence"
    )
    iterations: int = Field(default=0, description="Number of iterations completed")
    research_findings: Optional[ResearchFindings] = Field(
        None, description="Latest research findings"
    )
    validation_report: Optional[ValidationReport] = Field(
        None, description="Latest validation report"
    )
    bid_outline: Optional[BidOutline] = Field(None, description="Generated bid outline")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
