"""LangGraph workflow for orchestrating the research agents."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from app.agents import ResearchAgent, ValidatorAgent, WriterAgent
from app.config import settings
from app.models.schemas import SystemState, ResearchFindings, ValidationReport, BidOutline
from app.tools import BidResearchStorage, UnifiedBidGenerator, ComprehensiveResultGenerator


class WorkflowState(TypedDict):
    """State for the LangGraph workflow."""
    
    run_id: str
    rfp_path: str
    company_name: str
    max_iterations: int
    current_iteration: int
    research_findings: Dict[str, Any]
    validation_report: Dict[str, Any]
    bid_outline: Dict[str, Any]
    bid_research_package_path: str
    unified_bid_document_path: str
    comprehensive_result_path: str
    is_complete: bool
    errors: List[str]


class ResearchWorkflow:
    """LangGraph workflow for research and validation."""

    def __init__(self) -> None:
        self.research_agent = ResearchAgent()
        self.validator_agent = ValidatorAgent()
        self.writer_agent = WriterAgent()
        self.storage = BidResearchStorage()
        self.unified_generator = UnifiedBidGenerator()
        self.comprehensive_generator = ComprehensiveResultGenerator()
        
        # Build the graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("research", self._research_node)
        workflow.add_node("validate", self._validate_node) 
        workflow.add_node("write", self._write_node)
        workflow.add_node("refine", self._refine_node)
        workflow.add_node("save_research", self._save_research_node)
        workflow.add_node("generate_unified", self._generate_unified_node)
        workflow.add_node("generate_comprehensive", self._generate_comprehensive_node)
        
        # Add edges
        workflow.set_entry_point("research")
        workflow.add_edge("research", "validate")
        workflow.add_conditional_edges(
            "validate",
            self._should_refine,
            {
                "refine": "refine",
                "write": "write",
                "end": END
            }
        )
        workflow.add_edge("refine", "research")
        workflow.add_edge("write", "save_research")
        workflow.add_edge("save_research", "generate_unified")
        workflow.add_edge("generate_unified", "generate_comprehensive")
        workflow.add_edge("generate_comprehensive", END)
        
        return workflow.compile()

    def _research_node(self, state: WorkflowState) -> WorkflowState:
        """Execute research phase."""
        try:
            input_data = {
                "rfp_path": state["rfp_path"],
                "company_name": state["company_name"]
            }
            
            # Add refinement context if this is a retry
            context = {}
            if state["current_iteration"] > 0 and state.get("validation_report"):
                validation = state["validation_report"]
                if "gaps" in validation:
                    # Add suggested queries from gaps
                    suggested_queries = []
                    for gap in validation["gaps"]:
                        suggested_queries.extend(gap.get("suggested_queries", []))
                    context["additional_queries"] = suggested_queries
            
            findings = self.research_agent.process(input_data, context)
            
            state["research_findings"] = findings.model_dump()
            return state
            
        except Exception as e:
            state["errors"].append(f"Research error: {str(e)}")
            state["is_complete"] = True
            return state

    def _validate_node(self, state: WorkflowState) -> WorkflowState:
        """Execute validation phase."""
        try:
            if not state.get("research_findings"):
                state["errors"].append("No research findings to validate")
                state["is_complete"] = True
                return state
            
            # Convert dict back to Pydantic model
            from app.models.schemas import ResearchFindings
            findings = ResearchFindings(**state["research_findings"])
            
            # Pass RFP path context for enhanced validation
            context = {"rfp_path": state["rfp_path"]}
            validation_report = self.validator_agent.process(findings, context)
            state["validation_report"] = validation_report.model_dump()
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Validation error: {str(e)}")
            state["is_complete"] = True
            return state

    def _write_node(self, state: WorkflowState) -> WorkflowState:
        """Execute writing phase."""
        try:
            if not state.get("research_findings"):
                state["errors"].append("No research findings for writing")
                state["is_complete"] = True
                return state
            
            # Convert dict back to Pydantic model
            from app.models.schemas import ResearchFindings
            findings = ResearchFindings(**state["research_findings"])
            
            bid_outline = self.writer_agent.process(findings)
            state["bid_outline"] = bid_outline.model_dump()
            state["is_complete"] = True
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Writing error: {str(e)}")
            state["is_complete"] = True
            return state

    def _refine_node(self, state: WorkflowState) -> WorkflowState:
        """Prepare for refinement iteration."""
        state["current_iteration"] += 1
        return state
    
    def _save_research_node(self, state: WorkflowState) -> WorkflowState:
        """Save comprehensive research package for bid preparation."""
        try:
            if not state.get("research_findings") or not state.get("validation_report"):
                state["errors"].append("Missing research findings or validation report for saving")
                return state
            
            # Convert dicts back to Pydantic models
            research_findings = ResearchFindings(**state["research_findings"])
            validation_report = ValidationReport(**state["validation_report"])
            bid_outline = BidOutline(**state["bid_outline"]) if state.get("bid_outline") else None
            
            # Save comprehensive bid research package
            package_file = self.storage.save_bid_research_package(
                run_id=state["run_id"],
                research_findings=research_findings,
                validation_report=validation_report,
                bid_outline=bid_outline,
                rfp_file_path=state.get("rfp_path")
            )
            
            # Update state with package location
            state["bid_research_package_path"] = str(package_file)
            
            print(f"Comprehensive bid research package saved for run {state['run_id']}")
            return state
            
        except Exception as e:
            state["errors"].append(f"Research package saving error: {str(e)}")
            return state
    
    def _generate_unified_node(self, state: WorkflowState) -> WorkflowState:
        """Generate unified bid document."""
        try:
            if not state.get("research_findings") or not state.get("validation_report"):
                state["errors"].append("Missing research findings or validation report for unified document generation")
                return state
            
            # Convert dicts back to Pydantic models
            research_findings = ResearchFindings(**state["research_findings"])
            validation_report = ValidationReport(**state["validation_report"])
            bid_outline = BidOutline(**state["bid_outline"]) if state.get("bid_outline") else None
            
            # Collect search queries used (if available from research agent)
            search_queries_used = getattr(self.research_agent, '_last_queries_used', [])
            
            # Generate unified bid document
            unified_doc_path = self.unified_generator.generate_unified_bid_document(
                run_id=state["run_id"],
                research_findings=research_findings,
                validation_report=validation_report,
                bid_outline=bid_outline,
                rfp_file_path=state.get("rfp_path"),
                search_queries_used=search_queries_used
            )
            
            # Update state with unified document path
            state["unified_bid_document_path"] = str(unified_doc_path)
            
            print(f"Unified bid document generated for run {state['run_id']}")
            return state
            
        except Exception as e:
            state["errors"].append(f"Unified document generation error: {str(e)}")
            return state
    
    def _generate_comprehensive_node(self, state: WorkflowState) -> WorkflowState:
        """Generate comprehensive result.json file."""
        try:
            if not state.get("research_findings") or not state.get("validation_report"):
                state["errors"].append("Missing research findings or validation report for comprehensive result generation")
                return state
            
            # Convert dicts back to Pydantic models
            research_findings = ResearchFindings(**state["research_findings"])
            validation_report = ValidationReport(**state["validation_report"])
            bid_outline = BidOutline(**state["bid_outline"]) if state.get("bid_outline") else None
            
            # Collect search queries used (if available from research agent)
            search_queries_used = getattr(self.research_agent, '_last_queries_used', [])
            
            # Generate comprehensive result.json
            result_file_path = self.comprehensive_generator.generate_comprehensive_result(
                run_id=state["run_id"],
                research_findings=research_findings,
                validation_report=validation_report,
                bid_outline=bid_outline,
                rfp_file_path=state.get("rfp_path"),
                search_queries_used=search_queries_used
            )
            
            # Update state with result file path
            state["comprehensive_result_path"] = str(result_file_path)
            
            print(f"Comprehensive result.json generated for run {state['run_id']}")
            return state
            
        except Exception as e:
            state["errors"].append(f"Comprehensive result generation error: {str(e)}")
            return state

    def _should_refine(self, state: WorkflowState) -> str:
        """Decide whether to refine, write, or end."""
        # Check for errors
        if state.get("errors"):
            return "end"
        
        # Check iteration limit
        if state["current_iteration"] >= state["max_iterations"]:
            return "write"
        
        # Check validation results
        validation = state.get("validation_report")
        if not validation:
            return "end"
        
        # If sufficient, proceed to writing
        if validation.get("is_sufficient", False):
            return "write"
        
        # If not sufficient and under iteration limit, refine
        return "refine"

    def _save_artifacts(self, state: WorkflowState) -> None:
        """Save workflow artifacts to disk."""
        run_dir = settings.data_dir / "runs" / state["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save input parameters
        inputs = {
            "run_id": state["run_id"],
            "rfp_path": state["rfp_path"],
            "company_name": state["company_name"],
            "max_iterations": state["max_iterations"],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(run_dir / "inputs.json", "w") as f:
            json.dump(inputs, f, indent=2)
        
        # Save research findings
        if state.get("research_findings"):
            with open(run_dir / "findings.json", "w") as f:
                json.dump(state["research_findings"], f, indent=2)
        
        # Save validation report
        if state.get("validation_report"):
            with open(run_dir / "validation.json", "w") as f:
                json.dump(state["validation_report"], f, indent=2)
        
        # Save bid outline as markdown
        if state.get("bid_outline"):
            outline_md = ""
            bid_outline = state["bid_outline"]
            for section in bid_outline.get("sections", []):
                outline_md += f"{section['markdown']}\n\n---\n\n"
            
            with open(run_dir / "outline.md", "w") as f:
                f.write(outline_md)
        
        # Save run summary
        summary = {
            "run_id": state["run_id"],
            "iterations": state["current_iteration"],
            "is_complete": state.get("is_complete", False),
            "errors": state.get("errors", []),
            "coverage_score": state.get("validation_report", {}).get("coverage_score", 0.0),
            "requirements_count": len(state.get("research_findings", {}).get("extracted_requirements", [])),
            "evidence_count": len(state.get("research_findings", {}).get("evidence", [])),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(run_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

    def run(self, rfp_path: str, company_name: str, max_iterations: int = None) -> Dict[str, Any]:
        """Run the complete research workflow."""
        if max_iterations is None:
            max_iterations = settings.max_iterations
        
        # Initialize state
        initial_state = WorkflowState(
            run_id=str(uuid.uuid4()),
            rfp_path=rfp_path,
            company_name=company_name,
            max_iterations=max_iterations,
            current_iteration=0,
            research_findings={},
            validation_report={},
            bid_outline={},
            bid_research_package_path="",
            unified_bid_document_path="",
            comprehensive_result_path="",
            is_complete=False,
            errors=[]
        )
        
        # Execute workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Save artifacts
        self._save_artifacts(final_state)
        
        return final_state
