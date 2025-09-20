"""Integration tests for the workflow."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.models.schemas import ResearchFindings, ValidationReport
from app.orchestrator.workflow import ResearchWorkflow


class TestResearchWorkflow:
    """Test the complete research workflow."""

    @pytest.fixture
    def sample_pdf(self) -> Path:
        """Create a sample PDF file for testing."""
        # This is a mock - in real tests you'd want actual PDF content
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Write some basic PDF structure (minimal)
            f.write(b"%PDF-1.4\n")
            f.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
            f.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
            f.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n")
            f.write(b"xref\n0 4\n0000000000 65535 f \n")
            f.write(b"0000000009 00000 n \n0000000074 00000 n \n")
            f.write(b"0000000120 00000 n \ntrailer\n")
            f.write(b"<< /Size 4 /Root 1 0 R >>\nstartxref\n173\n%%EOF")
            
            return Path(f.name)

    @patch('app.agents.research_agent.ResearchAgent.process')
    @patch('app.agents.validator_agent.ValidatorAgent.process')
    @patch('app.agents.writer_agent.WriterAgent.process')
    def test_workflow_success_path(
        self,
        mock_writer: Mock,
        mock_validator: Mock,
        mock_research: Mock,
        sample_pdf: Path
    ) -> None:
        """Test successful workflow execution."""
        
        # Mock agent responses
        mock_research.return_value = ResearchFindings(
            rfp_meta={
                "title": "Test RFP",
                "version": "1.0",
                "deadline_iso": "2024-12-31T23:59:59"
            },
            company_profile={
                "name": "Test Company",
                "overview": "Test overview",
                "hq": "London",
                "sites": []
            },
            extracted_requirements=[
                {
                    "id": "REQ-001",
                    "text": "Test requirement",
                    "category": "features"
                }
            ],
            evidence=[
                {
                    "source_url": "http://example.com",
                    "snippet": "Test evidence",
                    "confidence": 0.8,
                    "tags": ["test"]
                }
            ],
            mapped_insights=[
                {
                    "requirement_id": "REQ-001",
                    "rationale": "Test insight",
                    "supporting_evidence_idx": [0],
                    "confidence": 0.8
                }
            ]
        )
        
        mock_validator.return_value = ValidationReport(
            coverage_score=0.8,
            gaps=[],
            quality_notes=["Good coverage"],
            is_sufficient=True
        )
        
        from app.models.schemas import BidOutline, BidSection
        mock_writer.return_value = BidOutline(
            sections=[
                BidSection(
                    title="Executive Summary",
                    markdown="# Executive Summary\n\nTest summary"
                )
            ]
        )
        
        try:
            # Run workflow
            workflow = ResearchWorkflow()
            result = workflow.run(
                rfp_path=str(sample_pdf),
                company_name="Test Company",
                max_iterations=2
            )
            
            # Verify result structure
            assert "run_id" in result
            assert "is_complete" in result
            assert result["is_complete"] is True
            assert result["current_iteration"] >= 0
            
            # Verify agents were called
            mock_research.assert_called()
            mock_validator.assert_called()
            mock_writer.assert_called()
            
        finally:
            # Clean up
            sample_pdf.unlink(missing_ok=True)

    @patch('app.agents.research_agent.ResearchAgent.process')
    @patch('app.agents.validator_agent.ValidatorAgent.process')
    def test_workflow_refinement_loop(
        self,
        mock_validator: Mock,
        mock_research: Mock,
        sample_pdf: Path
    ) -> None:
        """Test workflow refinement loop."""
        
        # Mock research agent
        mock_research.return_value = ResearchFindings(
            rfp_meta={
                "title": "Test RFP",
                "version": "1.0",
                "deadline_iso": "2024-12-31T23:59:59"
            },
            company_profile={
                "name": "Test Company",
                "overview": "Test overview",
                "hq": "London",
                "sites": []
            },
            extracted_requirements=[
                {
                    "id": "REQ-001",
                    "text": "Test requirement",
                    "category": "features"
                }
            ],
            evidence=[],
            mapped_insights=[]
        )
        
        # Mock validator to return insufficient first, then sufficient
        validation_responses = [
            ValidationReport(
                coverage_score=0.3,
                gaps=[
                    {
                        "requirement_id": "REQ-001",
                        "why": "No evidence found",
                        "suggested_queries": ["test query 1", "test query 2"]
                    }
                ],
                quality_notes=["Low coverage"],
                is_sufficient=False
            ),
            ValidationReport(
                coverage_score=0.8,
                gaps=[],
                quality_notes=["Improved coverage"],
                is_sufficient=True
            )
        ]
        mock_validator.side_effect = validation_responses
        
        try:
            # Run workflow
            workflow = ResearchWorkflow()
            result = workflow.run(
                rfp_path=str(sample_pdf),
                company_name="Test Company",
                max_iterations=2
            )
            
            # Should have done at least one refinement iteration
            assert result["current_iteration"] >= 1
            
            # Research agent should have been called multiple times
            assert mock_research.call_count >= 2
            
        finally:
            # Clean up
            sample_pdf.unlink(missing_ok=True)

    def test_workflow_error_handling(self, sample_pdf: Path) -> None:
        """Test workflow error handling."""
        
        try:
            workflow = ResearchWorkflow()
            
            # Test with non-existent file
            result = workflow.run(
                rfp_path="nonexistent.pdf",
                company_name="Test Company",
                max_iterations=1
            )
            
            # Should complete with errors
            assert result["is_complete"] is True
            assert len(result["errors"]) > 0
            
        finally:
            # Clean up
            sample_pdf.unlink(missing_ok=True)

    def test_workflow_artifacts_saved(self, sample_pdf: Path) -> None:
        """Test that workflow artifacts are saved."""
        
        # This test would require mocking the agents to avoid API calls
        # For now, just test the artifact saving structure
        workflow = ResearchWorkflow()
        
        # Create a mock state
        from app.orchestrator.workflow import WorkflowState
        state = WorkflowState(
            run_id="test-run-123",
            rfp_path=str(sample_pdf),
            company_name="Test Company",
            max_iterations=1,
            current_iteration=1,
            research_findings={
                "rfp_meta": {"title": "Test", "version": "1.0", "deadline_iso": "2024-12-31T23:59:59"},
                "company_profile": {"name": "Test Co", "overview": "Test", "hq": "London", "sites": []},
                "extracted_requirements": [],
                "evidence": [],
                "mapped_insights": []
            },
            validation_report={
                "coverage_score": 0.5,
                "gaps": [],
                "quality_notes": [],
                "is_sufficient": True
            },
            bid_outline={
                "sections": [
                    {"title": "Summary", "markdown": "# Summary\nTest content"}
                ]
            },
            is_complete=True,
            errors=[]
        )
        
        # Save artifacts
        workflow._save_artifacts(state)
        
        # Check that files were created
        from app.config import settings
        run_dir = settings.data_dir / "runs" / "test-run-123"
        
        assert (run_dir / "inputs.json").exists()
        assert (run_dir / "findings.json").exists()
        assert (run_dir / "validation.json").exists()
        assert (run_dir / "outline.md").exists()
        assert (run_dir / "summary.json").exists()
        
        # Verify content
        with open(run_dir / "summary.json") as f:
            summary = json.load(f)
            assert summary["run_id"] == "test-run-123"
            assert summary["coverage_score"] == 0.5
        
        # Clean up
        import shutil
        shutil.rmtree(run_dir, ignore_errors=True)
        sample_pdf.unlink(missing_ok=True)
