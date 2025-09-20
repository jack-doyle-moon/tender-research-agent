"""Validator Agent for assessing research quality and completeness using LLM-based analysis."""

import json
from typing import Any, Dict, List, Optional

from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.models.schemas import Gap, ResearchFindings, ValidationReport
from app.prompts import VALIDATOR_AGENT_PROMPT
from app.tools import DocumentProcessor


class ValidatorAgent(BaseAgent):
    """Agent responsible for validating research findings using LLM-based analysis."""

    def __init__(self) -> None:
        super().__init__("ValidatorAgent", VALIDATOR_AGENT_PROMPT)
        self.document_processor = DocumentProcessor()

    def process(self, input_data: ResearchFindings, context: Optional[Dict[str, Any]] = None) -> ValidationReport:
        """Simple validation: check research quality against RFP and provide additional queries if needed."""
        
        # Get RFP document content for validation
        rfp_content = None
        if context and context.get("rfp_path"):
            rfp_path = Path(context["rfp_path"])
            if rfp_path.exists():
                try:
                    chunks = self.document_processor.process_document(rfp_path)
                    rfp_content = "\n".join([chunk.text for chunk in chunks])
                    print(f"Loaded RFP document for validation: {rfp_path.name}")
                except (FileNotFoundError, ValueError, OSError) as e:
                    print(f"Failed to load RFP document: {e}")
        
        # Create simple validation prompt
        validation_prompt = self._create_simple_validation_prompt(input_data, rfp_content)
        
        # Get LLM validation
        messages = self._create_messages(validation_prompt)
        response = self.llm.invoke(messages)
        
        try:
            # Parse simple validation response
            validation_data = self._parse_validation_response(response.content)
            
            # Calculate single validation score
            validation_score = validation_data.get("validation_score", 0.0)
            additional_queries = validation_data.get("additional_search_queries", [])
            validation_notes = validation_data.get("validation_notes", [])
            
            # Threshold check (0.7 = 70% threshold)
            is_sufficient = validation_score >= 0.7
            
            # Create gaps with additional queries if validation fails
            gaps = []
            if not is_sufficient and additional_queries:
                gaps = [Gap(
                    requirement_id="ADDITIONAL_RESEARCH",
                    why=f"Validation score {validation_score:.2f} below threshold 0.7 - additional research needed",
                    suggested_queries=additional_queries
                )]
            
            return ValidationReport(
                coverage_score=validation_score,
                rfp_validation_score=validation_score,  # Same single metric
                extraction_accuracy=validation_score,   # Same single metric
                gaps=gaps,
                quality_notes=validation_notes,
                rfp_validation_notes=[],
                is_sufficient=is_sufficient
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"LLM validation failed, using fallback: {e}")
            return self._simple_fallback_validation(input_data)

    def _create_validation_prompt(self, findings: ResearchFindings) -> str:
        """Create comprehensive validation prompt for LLM analysis."""
        
        # Prepare findings summary for analysis
        findings_summary = {
            "rfp_title": findings.rfp_meta.title,
            "company_name": findings.company_profile.name,
            "total_requirements": len(findings.extracted_requirements),
            "total_evidence": len(findings.evidence),
            "total_insights": len(findings.mapped_insights)
        }
        
        # Prepare detailed requirement analysis
        requirement_analysis = []
        for req in findings.extracted_requirements:
            req_insights = [i for i in findings.mapped_insights if i.requirement_id == req.id]
            req_evidence = []
            
            for insight in req_insights:
                for idx in insight.supporting_evidence_idx:
                    if idx < len(findings.evidence):
                        req_evidence.append({
                            "source": findings.evidence[idx].source_url,
                            "confidence": findings.evidence[idx].confidence,
                            "snippet": findings.evidence[idx].snippet[:500] + "..."
                        })
            
            requirement_analysis.append({
                "id": req.id,
                "text": req.text,
                "category": req.category.value,
                "insights_count": len(req_insights),
                "evidence_count": len(req_evidence),
                "avg_confidence": sum(i.confidence for i in req_insights) / len(req_insights) if req_insights else 0.0,
                "evidence_sample": req_evidence[:2]  # Sample evidence
            })
        
        prompt = f"""
        Conduct comprehensive validation analysis of research findings for RFP response preparation.
        
        ## RESEARCH FINDINGS SUMMARY
        {json.dumps(findings_summary, indent=2)}
        
        ## DETAILED REQUIREMENT ANALYSIS
        {json.dumps(requirement_analysis, indent=2)}
        
        ## VALIDATION TASKS
        
        ### 1. Coverage Analysis
        - Evaluate completeness of requirement coverage
        - Assess evidence quality and depth for each requirement
        - Identify critical requirements with insufficient evidence
        - Calculate overall coverage score (0.0-1.0)
        
        ### 2. Strategic Gap Identification
        For each significant gap, provide:
        - Requirement ID affected
        - Gap category (capability|competitive|risk|evidence|strategic)
        - Priority level (critical|important|enhancement)
        - Detailed explanation of why this is a gap
        - Business impact assessment
        - 3-5 sophisticated research queries to address the gap
        
        ### 3. Quality Assessment
        - Evidence credibility and recency analysis
        - Source diversity evaluation
        - Confidence score calibration assessment
        - Overall research quality notes
        
        ### 4. Sufficiency Determination
        Based on analysis, determine if research is sufficient for bid progression:
        - >80% coverage of critical requirements with >0.7 confidence = Sufficient
        - Clear competitive differentiation with supporting evidence = Sufficient
        - Major gaps in critical areas = Insufficient
        
        Return ONLY valid JSON in this format:
        {{
          "coverage_score": 0.0,
          "strategic_gaps": [
            {{
              "requirement_id": "REQ-001",
              "category": "capability",
              "priority": "critical",
              "description": "Detailed gap description",
              "business_impact": "Impact on bid success",
              "suggested_research_queries": ["query1", "query2", "query3"]
            }}
          ],
          "quality_notes": ["Specific quality assessment note"],
          "is_sufficient": false
        }}
        """
        
        return prompt
    
    def _create_simple_validation_prompt(self, findings: ResearchFindings, rfp_content: Optional[str] = None) -> str:
        """Create simple validation prompt with single score and additional queries."""
        
        # Prepare key findings summary
        requirements_summary = []
        for req in findings.extracted_requirements[:5]:  # Top 5 requirements
            # Find evidence for this requirement
            req_evidence = []
            for insight in findings.mapped_insights:
                if insight.requirement_id == req.id:
                    for idx in insight.supporting_evidence_idx:
                        if idx < len(findings.evidence):
                            req_evidence.append({
                                "confidence": findings.evidence[idx].confidence,
                                "source": findings.evidence[idx].source_url[:50]
                            })
            
            requirements_summary.append({
                "id": req.id,
                "text": req.text[:80],
                "priority": req.priority,
                "evidence_count": len(req_evidence),
                "avg_confidence": sum(e["confidence"] for e in req_evidence) / len(req_evidence) if req_evidence else 0.0
            })
        
        # Prepare RFP validation section
        rfp_section = ""
        if rfp_content:
            rfp_sample = rfp_content[:2000] + "..." if len(rfp_content) > 2000 else rfp_content
            rfp_section = f"""
        ## ORIGINAL RFP DOCUMENT
        {rfp_sample}
        """
        
        prompt = f"""
        Validate research findings against RFP requirements. Provide a single validation score and additional search queries if needed.
        
        ## RESEARCH FINDINGS TO VALIDATE
        **RFP Title:** {findings.rfp_meta.title}
        **Organization:** {findings.rfp_meta.organization}
        **Company Researched:** {findings.company_profile.name}
        **Total Requirements:** {len(findings.extracted_requirements)}
        **Total Evidence:** {len(findings.evidence)}
        
        **Key Requirements & Evidence:**
        {json.dumps(requirements_summary, indent=2)}
        
        {rfp_section}
        
        ## VALIDATION TASK
        
        Evaluate the research quality by checking:
        1. **RFP Coverage**: Are key requirements properly extracted and covered?
        2. **Evidence Quality**: Is there sufficient, credible evidence for critical requirements?
        3. **Company Intelligence**: Is there adequate information about company capabilities?
        4. **RFP Alignment**: Does the research align with the original RFP content?
        
        Provide a single validation score (0.0-1.0):
        - 0.8-1.0: Excellent research, ready for bid preparation
        - 0.7-0.8: Good research, minor gaps acceptable
        - 0.5-0.7: Adequate research but needs improvement
        - 0.0-0.5: Poor research, significant additional work needed
        
        If score < 0.7, provide 5-8 additional search queries to improve research quality.
        
        Return ONLY valid JSON:
        {{
          "validation_score": 0.75,
          "validation_notes": [
            "Brief assessment of research quality",
            "Key strengths identified",
            "Areas needing attention"
          ],
          "additional_search_queries": [
            "specific search query 1",
            "specific search query 2",
            "specific search query 3"
          ]
        }}
        
        **Keep it simple - one score, brief notes, and targeted queries if needed.**
        """
        
        return prompt

    def _parse_validation_response(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM validation response into structured data."""
        
        # Clean response content
        response_text = response_content.strip()
        
        # Extract JSON from response
        json_text = response_text
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                json_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                json_text = response_text[start:end].strip()
        
        # Parse JSON
        try:
            data = json.loads(json_text)
            return data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response content: {response_content[:500]}...")
            raise

    def _simple_fallback_validation(self, findings: ResearchFindings) -> ValidationReport:
        """Simple fallback validation when LLM fails."""
        print("Using simple fallback validation")
        
        # Simple score calculation based on evidence coverage
        if not findings.extracted_requirements:
            validation_score = 0.0
        else:
            # Count requirements with evidence
            covered_requirements = set(insight.requirement_id for insight in findings.mapped_insights)
            coverage_ratio = len(covered_requirements) / len(findings.extracted_requirements)
            
            # Adjust for evidence quality
            if findings.evidence:
                avg_confidence = sum(e.confidence for e in findings.evidence) / len(findings.evidence)
                validation_score = coverage_ratio * avg_confidence
            else:
                validation_score = coverage_ratio * 0.5  # No evidence penalty
        
        # Generate simple additional queries if score is low
        additional_queries = []
        if validation_score < 0.7:
            company_name = findings.company_profile.name
            additional_queries = [
                f"{company_name} case studies and success stories",
                f"{company_name} technical capabilities and certifications",
                f"{company_name} relevant project experience",
                f"{company_name} competitive advantages and differentiators",
                f"{company_name} industry expertise and partnerships"
            ]
        
        # Create gaps if additional research needed
        gaps = []
        if validation_score < 0.7 and additional_queries:
            gaps = [Gap(
                requirement_id="ADDITIONAL_RESEARCH",
                why=f"Validation score {validation_score:.2f} below threshold 0.7 - additional research needed",
                suggested_queries=additional_queries
            )]
        
        return ValidationReport(
            coverage_score=validation_score,
            rfp_validation_score=validation_score,
            extraction_accuracy=validation_score,
            gaps=gaps,
            quality_notes=[f"Simple validation score: {validation_score:.2f}"],
            rfp_validation_notes=[],
            is_sufficient=validation_score >= 0.7
        )

