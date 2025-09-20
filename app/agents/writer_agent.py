"""Writer Agent for creating bid outlines from research findings."""

from typing import Any, Dict, Optional

from app.agents.base_agent import BaseAgent
from app.models.schemas import BidOutline, BidSection, ResearchFindings
from app.prompts import WRITER_AGENT_PROMPT


class WriterAgent(BaseAgent):
    """Agent responsible for writing bid outlines."""

    def __init__(self) -> None:
        super().__init__("WriterAgent", WRITER_AGENT_PROMPT)

    def _create_executive_summary(self, findings: ResearchFindings) -> str:
        """Create executive summary section."""
        company = findings.company_profile
        req_count = len(findings.extracted_requirements)
        evidence_count = len(findings.evidence)
        
        summary = f"""# Executive Summary

We are pleased to respond to **{findings.rfp_meta.title}** for {company.name}.

## Key Value Proposition

Based on our research of {company.name}'s operations and requirements, we have identified {req_count} key requirements across multiple categories. Our analysis of {evidence_count} evidence sources demonstrates our deep understanding of your needs.

## Our Differentiators

- Comprehensive understanding of {company.name}'s business context
- Proven experience in {', '.join(set(req.category.value for req in findings.extracted_requirements[:3]))}
- Evidence-based approach to solution design
- Commitment to meeting your {findings.rfp_meta.deadline_iso} deadline

## Company Overview

{company.overview}

**Headquarters:** {company.hq}
"""
        
        if company.sites:
            summary += f"**Locations:** {', '.join(company.sites[:5])}\n"
        
        return summary

    def _create_requirements_understanding(self, findings: ResearchFindings) -> str:
        """Create requirements understanding section."""
        content = """# Understanding of Requirements

We have carefully analyzed your RFP and identified the following key requirement categories:

"""
        
        # Group requirements by category
        by_category = {}
        for req in findings.extracted_requirements:
            if req.category.value not in by_category:
                by_category[req.category.value] = []
            by_category[req.category.value].append(req)
        
        for category, reqs in by_category.items():
            content += f"## {category.title()} Requirements\n\n"
            
            for req in reqs[:3]:  # Limit for outline
                # Find supporting evidence
                supporting_insights = [
                    insight for insight in findings.mapped_insights 
                    if insight.requirement_id == req.id
                ]
                
                content += f"- **{req.id}:** {req.text}\n"
                
                if supporting_insights:
                    insight = supporting_insights[0]
                    content += f"  - *Confidence: {insight.confidence:.1f}*\n"
                    content += f"  - *Rationale: {insight.rationale}*\n"
                
                content += "\n"
        
        return content

    def _create_solution_approach(self, findings: ResearchFindings) -> str:
        """Create solution approach section."""
        content = """# Proposed Solution Approach

## Methodology

Our approach is built on evidence-based understanding of {company_name}'s specific context and requirements.

## Key Solution Components

""".format(company_name=findings.company_profile.name)
        
        # Organize by category
        categories = set(req.category.value for req in findings.extracted_requirements)
        
        for category in categories:
            content += f"### {category.title()} Solution\n\n"
            
            category_reqs = [req for req in findings.extracted_requirements if req.category.value == category]
            content += f"Addressing {len(category_reqs)} requirements in this category:\n\n"
            
            # Add evidence-based insights
            category_evidence = []
            for req in category_reqs:
                insights = [i for i in findings.mapped_insights if i.requirement_id == req.id]
                for insight in insights:
                    for idx in insight.supporting_evidence_idx:
                        if idx < len(findings.evidence):
                            category_evidence.append(findings.evidence[idx])
            
            if category_evidence:
                best_evidence = max(category_evidence, key=lambda e: e.confidence)
                content += f"Based on our research: *{best_evidence.snippet[:100]}...*\n\n"
            
            content += "\n"
        
        return content

    def _create_implementation_timeline(self, findings: ResearchFindings) -> str:
        """Create implementation timeline section."""
        content = f"""# Implementation Approach & Timeline

## Project Timeline

**RFP Deadline:** {findings.rfp_meta.deadline_iso}

## Phases

### Phase 1: Requirements Analysis (Weeks 1-2)
- Detailed requirements gathering
- Stakeholder interviews
- Technical architecture design

### Phase 2: Solution Development (Weeks 3-8)
- Core functionality implementation
- Integration development
- Testing and quality assurance

### Phase 3: Deployment & Support (Weeks 9-10)
- Production deployment
- User training
- Go-live support

## Risk Mitigation

Based on our analysis of {findings.company_profile.name}'s environment:
- Regular stakeholder communication
- Iterative delivery approach
- Comprehensive testing strategy
"""
        return content

    def process(self, input_data: ResearchFindings, context: Optional[Dict[str, Any]] = None) -> BidOutline:
        """Create bid outline from research findings."""
        sections = []
        
        # Executive Summary
        sections.append(BidSection(
            title="Executive Summary",
            markdown=self._create_executive_summary(input_data)
        ))
        
        # Requirements Understanding
        sections.append(BidSection(
            title="Understanding of Requirements", 
            markdown=self._create_requirements_understanding(input_data)
        ))
        
        # Solution Approach
        sections.append(BidSection(
            title="Proposed Solution",
            markdown=self._create_solution_approach(input_data)
        ))
        
        # Implementation
        sections.append(BidSection(
            title="Implementation Approach",
            markdown=self._create_implementation_timeline(input_data)
        ))
        
        return BidOutline(sections=sections)
