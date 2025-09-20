"""Test Pydantic models."""

import pytest
from datetime import datetime

from app.models.schemas import (
    BidOutline,
    BidSection,
    CompanyProfile,
    Evidence,
    Gap,
    MappedInsight,
    Requirement,
    RequirementCategory,
    ResearchFindings,
    RFPMeta,
    SystemState,
    ValidationReport,
)


class TestRequirement:
    """Test Requirement model."""

    def test_valid_requirement(self) -> None:
        """Test creating a valid requirement."""
        req = Requirement(
            id="REQ-001",
            text="System must support user authentication",
            category=RequirementCategory.FEATURES
        )
        
        assert req.id == "REQ-001"
        assert req.text == "System must support user authentication"
        assert req.category == RequirementCategory.FEATURES

    def test_requirement_categories(self) -> None:
        """Test all requirement categories are valid."""
        categories = [
            RequirementCategory.FEATURES,
            RequirementCategory.INTEGRATION,
            RequirementCategory.LICENSING,
            RequirementCategory.ROI,
            RequirementCategory.SUPPORT,
            RequirementCategory.TIMELINE,
        ]
        
        for category in categories:
            req = Requirement(
                id="REQ-001",
                text="Test requirement",
                category=category
            )
            assert req.category == category


class TestEvidence:
    """Test Evidence model."""

    def test_valid_evidence(self) -> None:
        """Test creating valid evidence."""
        evidence = Evidence(
            source_url="https://example.com/case-study",
            snippet="Company successfully implemented solution",
            confidence=0.8,
            tags=["case-study", "implementation"]
        )
        
        assert evidence.source_url == "https://example.com/case-study"
        assert evidence.confidence == 0.8
        assert "case-study" in evidence.tags

    def test_confidence_bounds(self) -> None:
        """Test confidence score validation."""
        # Valid confidence scores
        Evidence(source_url="http://test.com", snippet="test", confidence=0.0)
        Evidence(source_url="http://test.com", snippet="test", confidence=1.0)
        Evidence(source_url="http://test.com", snippet="test", confidence=0.5)
        
        # Invalid confidence scores should raise validation error
        with pytest.raises(ValueError):
            Evidence(source_url="http://test.com", snippet="test", confidence=-0.1)
        
        with pytest.raises(ValueError):
            Evidence(source_url="http://test.com", snippet="test", confidence=1.1)


class TestResearchFindings:
    """Test ResearchFindings model."""

    def test_empty_findings(self) -> None:
        """Test creating empty research findings."""
        rfp_meta = RFPMeta(
            title="Test RFP",
            version="1.0",
            deadline_iso="2024-12-31T23:59:59"
        )
        
        company_profile = CompanyProfile(
            name="Test Company",
            overview="A test company",
            hq="London, UK",
            sites=["London", "Manchester"]
        )
        
        findings = ResearchFindings(
            rfp_meta=rfp_meta,
            company_profile=company_profile
        )
        
        assert len(findings.extracted_requirements) == 0
        assert len(findings.evidence) == 0
        assert len(findings.mapped_insights) == 0

    def test_complete_findings(self) -> None:
        """Test creating complete research findings."""
        rfp_meta = RFPMeta(
            title="Test RFP",
            version="1.0", 
            deadline_iso="2024-12-31T23:59:59"
        )
        
        company_profile = CompanyProfile(
            name="Test Company",
            overview="A test company",
            hq="London, UK"
        )
        
        requirements = [
            Requirement(
                id="REQ-001",
                text="Test requirement",
                category=RequirementCategory.FEATURES
            )
        ]
        
        evidence = [
            Evidence(
                source_url="http://test.com",
                snippet="Test evidence",
                confidence=0.7,
                tags=["test"]
            )
        ]
        
        insights = [
            MappedInsight(
                requirement_id="REQ-001",
                rationale="Test mapping",
                supporting_evidence_idx=[0],
                confidence=0.7
            )
        ]
        
        findings = ResearchFindings(
            rfp_meta=rfp_meta,
            company_profile=company_profile,
            extracted_requirements=requirements,
            evidence=evidence,
            mapped_insights=insights
        )
        
        assert len(findings.extracted_requirements) == 1
        assert len(findings.evidence) == 1
        assert len(findings.mapped_insights) == 1


class TestValidationReport:
    """Test ValidationReport model."""

    def test_sufficient_report(self) -> None:
        """Test creating a sufficient validation report."""
        report = ValidationReport(
            coverage_score=0.9,
            gaps=[],
            quality_notes=["High quality evidence"],
            is_sufficient=True
        )
        
        assert report.coverage_score == 0.9
        assert report.is_sufficient is True
        assert len(report.gaps) == 0

    def test_insufficient_report(self) -> None:
        """Test creating an insufficient validation report."""
        gaps = [
            Gap(
                requirement_id="REQ-001",
                why="No evidence found",
                suggested_queries=["search query 1", "search query 2"]
            )
        ]
        
        report = ValidationReport(
            coverage_score=0.3,
            gaps=gaps,
            quality_notes=["Low coverage", "Missing evidence"],
            is_sufficient=False
        )
        
        assert report.coverage_score == 0.3
        assert report.is_sufficient is False
        assert len(report.gaps) == 1


class TestBidOutline:
    """Test BidOutline model."""

    def test_empty_outline(self) -> None:
        """Test creating empty bid outline."""
        outline = BidOutline()
        assert len(outline.sections) == 0

    def test_complete_outline(self) -> None:
        """Test creating complete bid outline."""
        sections = [
            BidSection(
                title="Executive Summary",
                markdown="# Executive Summary\n\nThis is the executive summary."
            ),
            BidSection(
                title="Technical Approach",
                markdown="# Technical Approach\n\nOur technical approach..."
            )
        ]
        
        outline = BidOutline(sections=sections)
        
        assert len(outline.sections) == 2
        assert outline.sections[0].title == "Executive Summary"
        assert "executive summary" in outline.sections[0].markdown.lower()


class TestSystemState:
    """Test SystemState model."""

    def test_initial_state(self) -> None:
        """Test creating initial system state."""
        state = SystemState(
            run_id="test-run-123",
            company_name="Test Company"
        )
        
        assert state.run_id == "test-run-123"
        assert state.company_name == "Test Company"
        assert state.iterations == 0
        assert len(state.requirements) == 0
        assert len(state.queries_run) == 0
        assert isinstance(state.created_at, datetime)
