"""Comprehensive Result Generator - Creates a single result.json with all RFP analysis and research results."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    ResearchFindings, 
    ValidationReport, 
    BidOutline,
    Requirement,
    Evidence,
    MappedInsight
)


class ComprehensiveResultGenerator:
    """Creates a comprehensive result.json file with all RFP and research data."""
    
    def __init__(self, storage_dir: Path = None):
        """Initialize comprehensive result generator."""
        self.storage_dir = storage_dir or Path("data/comprehensive_results")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comprehensive_result(
        self,
        run_id: str,
        research_findings: ResearchFindings,
        validation_report: ValidationReport,
        bid_outline: Optional[BidOutline] = None,
        rfp_file_path: Optional[str] = None,
        search_queries_used: Optional[List[str]] = None
    ) -> Path:
        """Generate a comprehensive result.json file with all analysis and research data."""
        
        # Create the comprehensive result structure
        comprehensive_result = self._create_comprehensive_structure(
            run_id, research_findings, validation_report, bid_outline, 
            rfp_file_path, search_queries_used
        )
        
        # Save the comprehensive result
        run_dir = self.storage_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        result_file = run_dir / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(comprehensive_result, f, indent=2, default=str)
        
        print(f"Comprehensive result.json created: {result_file}")
        return result_file
    
    def _create_comprehensive_structure(
        self,
        run_id: str,
        research_findings: ResearchFindings,
        validation_report: ValidationReport,
        bid_outline: Optional[BidOutline],
        rfp_file_path: Optional[str],
        search_queries_used: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Create the comprehensive result structure."""
        
        return {
            "metadata": {
                "run_id": run_id,
                "generated_at": datetime.now().isoformat(),
                "rfp_file_path": rfp_file_path,
                "validation_score": validation_report.coverage_score,
                "research_quality": "Excellent" if validation_report.coverage_score >= 0.8 
                                 else "Good" if validation_report.coverage_score >= 0.7
                                 else "Needs Improvement" if validation_report.coverage_score >= 0.5
                                 else "Poor",
                "is_sufficient_for_bid": validation_report.is_sufficient
            },
            
            "rfp_document_analysis": {
                "basic_information": {
                    "title": research_findings.rfp_meta.title,
                    "organization": research_findings.rfp_meta.organization,
                    "purpose": research_findings.rfp_meta.purpose,
                    "project_description": research_findings.rfp_meta.project_description,
                    "deadline": research_findings.rfp_meta.deadline_iso,
                    "budget_indication": research_findings.rfp_meta.budget_indication,
                    "contract_duration": research_findings.rfp_meta.contract_duration
                },
                
                "contacts_and_stakeholders": [
                    {
                        "name": contact.name,
                        "title": contact.title,
                        "email": contact.email,
                        "phone": contact.phone,
                        "organization": contact.organization
                    }
                    for contact in research_findings.rfp_meta.contact_info
                ],
                
                "presentation_requirements": {
                    "required": research_findings.rfp_meta.presentation_details is not None,
                    "details": {
                        "date": research_findings.rfp_meta.presentation_details.date if research_findings.rfp_meta.presentation_details else None,
                        "location": research_findings.rfp_meta.presentation_details.location if research_findings.rfp_meta.presentation_details else None,
                        "duration": research_findings.rfp_meta.presentation_details.duration if research_findings.rfp_meta.presentation_details else None,
                        "format": research_findings.rfp_meta.presentation_details.format if research_findings.rfp_meta.presentation_details else None,
                        "attendees": research_findings.rfp_meta.presentation_details.attendees if research_findings.rfp_meta.presentation_details else [],
                        "topics_to_cover": research_findings.rfp_meta.presentation_details.topics_to_cover if research_findings.rfp_meta.presentation_details else []
                    } if research_findings.rfp_meta.presentation_details else None
                },
                
                "timeline_and_milestones": [
                    {
                        "milestone": item.milestone,
                        "date": item.date,
                        "status": item.status
                    }
                    for item in research_findings.rfp_meta.timeline
                ],
                
                "evaluation_criteria": [
                    {
                        "criterion": criteria.criterion,
                        "weight": criteria.weight,
                        "description": criteria.description,
                        "scoring_method": criteria.scoring_method
                    }
                    for criteria in research_findings.rfp_meta.evaluation_criteria
                ],
                
                "submission_requirements": research_findings.rfp_meta.submission_requirements,
                "special_conditions": research_findings.rfp_meta.special_conditions
            },
            
            "requirements_analysis": {
                "summary": {
                    "total_requirements": len(research_findings.extracted_requirements),
                    "critical_requirements": len([r for r in research_findings.extracted_requirements if r.priority == "critical"]),
                    "high_priority_requirements": len([r for r in research_findings.extracted_requirements if r.priority == "high"]),
                    "medium_priority_requirements": len([r for r in research_findings.extracted_requirements if r.priority == "medium"]),
                    "low_priority_requirements": len([r for r in research_findings.extracted_requirements if r.priority == "low"])
                },
                
                "requirements_by_category": self._group_requirements_by_category(research_findings.extracted_requirements),
                
                "requirements_by_priority": self._group_requirements_by_priority(research_findings.extracted_requirements),
                
                "detailed_requirements": [
                    {
                        "id": req.id,
                        "text": req.text,
                        "category": req.category.value,
                        "priority": req.priority,
                        "business_impact": req.business_impact,
                        "evaluation_weight": req.evaluation_weight,
                        "source_section": req.source_section
                    }
                    for req in research_findings.extracted_requirements
                ]
            },
            
            "research_results": {
                "company_profile": {
                    "basic_information": {
                        "name": research_findings.company_profile.name,
                        "overview": research_findings.company_profile.overview,
                        "headquarters": research_findings.company_profile.hq,
                        "industry": research_findings.company_profile.industry,
                        "size": research_findings.company_profile.size,
                        "financial_info": research_findings.company_profile.financial_info
                    },
                    
                    "capabilities_and_strengths": {
                        "technology_stack": research_findings.company_profile.technology_stack,
                        "certifications": research_findings.company_profile.certifications,
                        "service_areas": research_findings.company_profile.service_areas,
                        "partnerships": research_findings.company_profile.partnerships
                    },
                    
                    "experience_and_track_record": {
                        "office_locations": research_findings.company_profile.sites,
                        "leadership": research_findings.company_profile.leadership,
                        "recent_projects": research_findings.company_profile.recent_projects,
                        "market_position": research_findings.company_profile.market_position
                    },
                    
                    "additional_intelligence": research_findings.company_profile.additional_info
                },
                
                "evidence_and_supporting_data": {
                    "total_evidence_sources": len(research_findings.evidence),
                    "high_confidence_evidence": len([e for e in research_findings.evidence if e.confidence >= 0.7]),
                    "medium_confidence_evidence": len([e for e in research_findings.evidence if 0.5 <= e.confidence < 0.7]),
                    "low_confidence_evidence": len([e for e in research_findings.evidence if e.confidence < 0.5]),
                    
                    "evidence_by_category": self._group_evidence_by_tags(research_findings.evidence),
                    
                    "detailed_evidence": [
                        {
                            "source_url": evidence.source_url,
                            "snippet": evidence.snippet,
                            "confidence": evidence.confidence,
                            "tags": evidence.tags,
                            "relevance": "High" if evidence.confidence >= 0.7 
                                      else "Medium" if evidence.confidence >= 0.5 
                                      else "Low"
                        }
                        for evidence in research_findings.evidence
                    ]
                },
                
                "requirement_coverage_analysis": {
                    "total_insights": len(research_findings.mapped_insights),
                    "requirements_with_evidence": len(set(insight.requirement_id for insight in research_findings.mapped_insights)),
                    "requirements_without_evidence": len(research_findings.extracted_requirements) - len(set(insight.requirement_id for insight in research_findings.mapped_insights)),
                    
                    "coverage_by_requirement": [
                        {
                            "requirement_id": insight.requirement_id,
                            "rationale": insight.rationale,
                            "confidence": insight.confidence,
                            "supporting_evidence_count": len(insight.supporting_evidence_idx)
                        }
                        for insight in research_findings.mapped_insights
                    ]
                },
                
                "search_methodology": {
                    "queries_used": search_queries_used or [],
                    "total_queries": len(search_queries_used) if search_queries_used else 0,
                    "search_approach": "RFP-specific targeted queries" if search_queries_used else "Standard queries"
                }
            },
            
            "validation_and_quality_assessment": {
                "overall_validation": {
                    "validation_score": validation_report.coverage_score,
                    "is_sufficient_for_bid": validation_report.is_sufficient,
                    "quality_assessment": validation_report.quality_notes,
                    "validation_notes": validation_report.rfp_validation_notes
                },
                
                "identified_gaps": [
                    {
                        "requirement_id": gap.requirement_id,
                        "gap_description": gap.why,
                        "suggested_queries": gap.suggested_queries,
                        "priority": "High" if "critical" in gap.why.lower() else "Medium"
                    }
                    for gap in validation_report.gaps
                ],
                
                "recommendations": {
                    "next_steps": self._generate_next_steps(validation_report),
                    "areas_for_improvement": self._identify_improvement_areas(validation_report, research_findings),
                    "bid_readiness": "Ready" if validation_report.is_sufficient else "Needs Additional Research"
                }
            },
            
            "bid_preparation_insights": {
                "key_opportunities": self._identify_key_opportunities(research_findings),
                "competitive_advantages": self._identify_competitive_advantages(research_findings),
                "potential_challenges": self._identify_potential_challenges(research_findings, validation_report),
                "strategic_recommendations": self._generate_strategic_recommendations(research_findings, validation_report)
            }
        }
    
    def _group_requirements_by_category(self, requirements: List[Requirement]) -> Dict[str, List[Dict[str, Any]]]:
        """Group requirements by category."""
        by_category = {}
        for req in requirements:
            category = req.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append({
                "id": req.id,
                "text": req.text,
                "priority": req.priority,
                "business_impact": req.business_impact
            })
        return by_category
    
    def _group_requirements_by_priority(self, requirements: List[Requirement]) -> Dict[str, List[Dict[str, Any]]]:
        """Group requirements by priority."""
        by_priority = {"critical": [], "high": [], "medium": [], "low": []}
        for req in requirements:
            if req.priority in by_priority:
                by_priority[req.priority].append({
                    "id": req.id,
                    "text": req.text,
                    "category": req.category.value,
                    "business_impact": req.business_impact
                })
        return by_priority
    
    def _group_evidence_by_tags(self, evidence: List[Evidence]) -> Dict[str, int]:
        """Group evidence by tags."""
        tag_counts = {}
        for ev in evidence:
            for tag in ev.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts
    
    def _generate_next_steps(self, validation_report: ValidationReport) -> List[str]:
        """Generate next steps based on validation results."""
        if validation_report.is_sufficient:
            return [
                "Proceed with bid preparation and proposal writing",
                "Review and customize bid examples for specific requirements",
                "Prepare presentation materials if required",
                "Finalize proposal structure and content"
            ]
        else:
            next_steps = ["Address identified research gaps before proceeding"]
            if validation_report.gaps:
                next_steps.append("Execute additional search queries to improve coverage")
                next_steps.append("Focus on critical requirements with insufficient evidence")
            next_steps.append("Re-validate research quality after improvements")
            return next_steps
    
    def _identify_improvement_areas(self, validation_report: ValidationReport, research_findings: ResearchFindings) -> List[str]:
        """Identify areas needing improvement."""
        areas = []
        
        if validation_report.coverage_score < 0.7:
            areas.append("Overall research coverage needs improvement")
        
        # Check evidence quality
        if research_findings.evidence:
            low_confidence_count = len([e for e in research_findings.evidence if e.confidence < 0.5])
            if low_confidence_count > len(research_findings.evidence) * 0.3:
                areas.append("Evidence quality - need more authoritative sources")
        
        # Check requirement coverage
        covered_reqs = set(insight.requirement_id for insight in research_findings.mapped_insights)
        uncovered_count = len(research_findings.extracted_requirements) - len(covered_reqs)
        if uncovered_count > 0:
            areas.append(f"Requirement coverage - {uncovered_count} requirements lack supporting evidence")
        
        # Check critical requirements
        critical_reqs = [r for r in research_findings.extracted_requirements if r.priority == "critical"]
        critical_covered = len([r for r in critical_reqs if r.id in covered_reqs])
        if critical_covered < len(critical_reqs):
            areas.append("Critical requirements coverage - some critical items lack evidence")
        
        return areas or ["Research quality is adequate for current scope"]
    
    def _identify_key_opportunities(self, research_findings: ResearchFindings) -> List[str]:
        """Identify key bid opportunities."""
        opportunities = []
        
        # High-confidence evidence opportunities
        high_conf_evidence = [e for e in research_findings.evidence if e.confidence >= 0.8]
        if high_conf_evidence:
            opportunities.append(f"Strong evidence base with {len(high_conf_evidence)} high-confidence sources")
        
        # Company strengths
        if research_findings.company_profile.certifications:
            opportunities.append(f"Relevant certifications: {', '.join(research_findings.company_profile.certifications[:3])}")
        
        if research_findings.company_profile.partnerships:
            opportunities.append(f"Strategic partnerships: {', '.join(research_findings.company_profile.partnerships[:3])}")
        
        # Critical requirement coverage
        critical_insights = [i for i in research_findings.mapped_insights 
                           if any(r.priority == "critical" and r.id == i.requirement_id 
                                 for r in research_findings.extracted_requirements)]
        if critical_insights:
            opportunities.append(f"Strong coverage of {len(critical_insights)} critical requirements")
        
        return opportunities or ["Identify specific opportunities through additional research"]
    
    def _identify_competitive_advantages(self, research_findings: ResearchFindings) -> List[str]:
        """Identify competitive advantages."""
        advantages = []
        
        # Technology stack advantages
        if research_findings.company_profile.technology_stack:
            advantages.append(f"Advanced technology capabilities: {', '.join(research_findings.company_profile.technology_stack[:3])}")
        
        # Market position
        if research_findings.company_profile.market_position:
            advantages.append(f"Market positioning: {research_findings.company_profile.market_position}")
        
        # Experience and projects
        if research_findings.company_profile.recent_projects:
            advantages.append(f"Relevant project experience: {len(research_findings.company_profile.recent_projects)} documented projects")
        
        # Financial stability
        if research_findings.company_profile.financial_info and "stable" in research_findings.company_profile.financial_info.lower():
            advantages.append("Financial stability and growth trajectory")
        
        return advantages or ["Competitive advantages need further research and documentation"]
    
    def _identify_potential_challenges(self, research_findings: ResearchFindings, validation_report: ValidationReport) -> List[str]:
        """Identify potential bid challenges."""
        challenges = []
        
        # Validation challenges
        if not validation_report.is_sufficient:
            challenges.append(f"Research quality below threshold (score: {validation_report.coverage_score:.2f})")
        
        # Coverage gaps
        covered_reqs = set(insight.requirement_id for insight in research_findings.mapped_insights)
        uncovered_reqs = [r for r in research_findings.extracted_requirements if r.id not in covered_reqs]
        critical_uncovered = [r for r in uncovered_reqs if r.priority == "critical"]
        
        if critical_uncovered:
            challenges.append(f"Critical requirements without evidence: {len(critical_uncovered)} items")
        
        # Evidence quality
        low_conf_evidence = [e for e in research_findings.evidence if e.confidence < 0.5]
        if len(low_conf_evidence) > len(research_findings.evidence) * 0.3:
            challenges.append("High proportion of low-confidence evidence sources")
        
        # Missing company intelligence
        missing_info = []
        if not research_findings.company_profile.certifications:
            missing_info.append("certifications")
        if not research_findings.company_profile.recent_projects:
            missing_info.append("recent projects")
        if not research_findings.company_profile.technology_stack:
            missing_info.append("technology capabilities")
        
        if missing_info:
            challenges.append(f"Missing company intelligence: {', '.join(missing_info)}")
        
        return challenges or ["No significant challenges identified in current research"]
    
    def _generate_strategic_recommendations(self, research_findings: ResearchFindings, validation_report: ValidationReport) -> List[str]:
        """Generate strategic recommendations for bid preparation."""
        recommendations = []
        
        if validation_report.is_sufficient:
            recommendations.extend([
                "Leverage high-confidence evidence in proposal narrative",
                "Emphasize company strengths that align with critical requirements",
                "Develop compelling case studies from documented project experience",
                "Create differentiated value proposition based on competitive advantages"
            ])
        else:
            recommendations.extend([
                "Prioritize additional research for critical requirements",
                "Seek authoritative sources to improve evidence quality",
                "Focus on company capability documentation",
                "Consider partnering to address capability gaps"
            ])
        
        # RFP-specific recommendations
        if research_findings.rfp_meta.presentation_details:
            recommendations.append("Prepare comprehensive presentation addressing all required topics")
        
        if research_findings.rfp_meta.evaluation_criteria:
            recommendations.append("Align proposal structure with stated evaluation criteria")
        
        recommendations.append("Ensure proposal addresses all submission requirements and special conditions")
        
        return recommendations
