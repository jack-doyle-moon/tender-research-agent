"""Research result storage system for bid preparation."""

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


class BidResearchStorage:
    """Comprehensive storage system for research results optimized for bid generation."""
    
    def __init__(self, storage_dir: Path = None):
        """Initialize storage system."""
        self.storage_dir = storage_dir or Path("data/bid_research")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def create_comprehensive_bid_package(
        self, 
        run_id: str,
        research_findings: ResearchFindings,
        validation_report: ValidationReport,
        bid_outline: Optional[BidOutline] = None,
        rfp_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create comprehensive bid research package for bid generation."""
        
        # Create comprehensive bid package
        bid_package = {
            "metadata": {
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
                "rfp_file_path": rfp_file_path,
                "package_version": "2.0",
                "system_version": "enhanced"
            },
            
            # RFP Analysis Section
            "rfp_analysis": {
                "title": research_findings.rfp_meta.title,
                "organization": research_findings.rfp_meta.organization,
                "purpose": research_findings.rfp_meta.purpose,
                "project_description": research_findings.rfp_meta.project_description,
                "deadline": research_findings.rfp_meta.deadline_iso,
                "budget_indication": research_findings.rfp_meta.budget_indication,
                "contract_duration": research_findings.rfp_meta.contract_duration,
                
                "presentation_requirements": {
                    "date": research_findings.rfp_meta.presentation_details.date if research_findings.rfp_meta.presentation_details else None,
                    "location": research_findings.rfp_meta.presentation_details.location if research_findings.rfp_meta.presentation_details else None,
                    "duration": research_findings.rfp_meta.presentation_details.duration if research_findings.rfp_meta.presentation_details else None,
                    "format": research_findings.rfp_meta.presentation_details.format if research_findings.rfp_meta.presentation_details else None,
                    "attendees": research_findings.rfp_meta.presentation_details.attendees if research_findings.rfp_meta.presentation_details else [],
                    "topics_to_cover": research_findings.rfp_meta.presentation_details.topics_to_cover if research_findings.rfp_meta.presentation_details else []
                },
                
                "timeline": [
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
                
                "contact_information": [
                    {
                        "name": contact.name,
                        "title": contact.title,
                        "email": contact.email,
                        "phone": contact.phone,
                        "organization": contact.organization
                    }
                    for contact in research_findings.rfp_meta.contact_info
                ],
                
                "submission_requirements": research_findings.rfp_meta.submission_requirements,
                "special_conditions": research_findings.rfp_meta.special_conditions
            },
            
            # Requirements Analysis Section
            "requirements_analysis": self._create_requirements_analysis(
                research_findings.extracted_requirements,
                research_findings.mapped_insights,
                research_findings.evidence
            ),
            
            # Company Intelligence Section
            "company_intelligence": {
                "profile": {
                    "name": research_findings.company_profile.name,
                    "overview": research_findings.company_profile.overview,
                    "headquarters": research_findings.company_profile.hq,
                    "locations": research_findings.company_profile.sites,
                    "industry": research_findings.company_profile.industry,
                    "size": research_findings.company_profile.size,
                    "leadership": research_findings.company_profile.leadership,
                    "financial_info": research_findings.company_profile.financial_info,
                    "certifications": research_findings.company_profile.certifications,
                    "technology_stack": research_findings.company_profile.technology_stack,
                    "service_areas": research_findings.company_profile.service_areas,
                    "market_position": research_findings.company_profile.market_position,
                    "recent_projects": research_findings.company_profile.recent_projects,
                    "partnerships": research_findings.company_profile.partnerships
                }
            },
            
            # Evidence Repository Section
            "evidence_repository": self._create_evidence_repository(research_findings.evidence),
            
            # Validation Assessment Section
            "validation_assessment": {
                "scores": {
                    "coverage_score": validation_report.coverage_score,
                    "rfp_validation_score": validation_report.rfp_validation_score,
                    "extraction_accuracy": validation_report.extraction_accuracy
                },
                "quality_assessment": validation_report.quality_notes,
                "rfp_validation_notes": validation_report.rfp_validation_notes,
                "identified_gaps": [
                    {
                        "requirement_id": gap.requirement_id,
                        "description": gap.why,
                        "suggested_research": gap.suggested_queries
                    }
                    for gap in validation_report.gaps
                ],
                "is_sufficient_for_bidding": validation_report.is_sufficient
            },
            
            # Bid Strategy Section
            "bid_strategy": self._create_bid_strategy_section(
                research_findings, validation_report, bid_outline
            ),
            
            # Quick Reference Section for Bid Writers
            "quick_reference": self._create_quick_reference_section(research_findings)
        }
        
        return bid_package
    
    def _create_requirements_analysis(
        self, 
        requirements: List[Requirement], 
        insights: List[MappedInsight], 
        evidence: List[Evidence]
    ) -> Dict[str, Any]:
        """Create comprehensive requirements analysis for bid preparation."""
        
        # Group requirements by category and priority
        by_category = {}
        by_priority = {"critical": [], "high": [], "medium": [], "low": []}
        
        for req in requirements:
            # Group by category
            if req.category.value not in by_category:
                by_category[req.category.value] = []
            
            # Find supporting insights and evidence
            req_insights = [i for i in insights if i.requirement_id == req.id]
            supporting_evidence = []
            
            for insight in req_insights:
                for idx in insight.supporting_evidence_idx:
                    if idx < len(evidence):
                        supporting_evidence.append({
                            "source_url": evidence[idx].source_url,
                            "snippet": evidence[idx].snippet,
                            "confidence": evidence[idx].confidence,
                            "tags": evidence[idx].tags
                        })
            
            req_data = {
                "id": req.id,
                "text": req.text,
                "category": req.category.value,
                "priority": req.priority,
                "business_impact": req.business_impact,
                "evaluation_weight": req.evaluation_weight,
                "source_section": req.source_section,
                "supporting_evidence": supporting_evidence,
                "insights_count": len(req_insights),
                "average_evidence_confidence": sum(e["confidence"] for e in supporting_evidence) / len(supporting_evidence) if supporting_evidence else 0.0,
                "bid_response_guidance": self._generate_bid_response_guidance(req, supporting_evidence)
            }
            
            by_category[req.category.value].append(req_data)
            by_priority[req.priority].append(req_data)
        
        # Create coverage analysis
        coverage_analysis = {
            "total_requirements": len(requirements),
            "by_category": {cat: len(reqs) for cat, reqs in by_category.items()},
            "by_priority": {pri: len(reqs) for pri, reqs in by_priority.items()},
            "critical_requirements_count": len(by_priority["critical"]),
            "high_priority_count": len(by_priority["high"])
        }
        
        return {
            "requirements_by_category": by_category,
            "requirements_by_priority": by_priority,
            "coverage_analysis": coverage_analysis,
            "bid_writing_priorities": self._create_bid_writing_priorities(by_priority)
        }
    
    def _create_evidence_repository(self, evidence: List[Evidence]) -> Dict[str, Any]:
        """Create organized evidence repository for bid writers."""
        
        # Organize evidence by confidence level and tags
        by_confidence = {"high": [], "medium": [], "low": []}
        by_tags = {}
        
        for ev in evidence:
            # Categorize by confidence
            if ev.confidence >= 0.7:
                conf_level = "high"
            elif ev.confidence >= 0.4:
                conf_level = "medium"
            else:
                conf_level = "low"
            
            evidence_data = {
                "source_url": ev.source_url,
                "snippet": ev.snippet,
                "confidence": ev.confidence,
                "tags": ev.tags,
                "credibility_assessment": self._assess_source_credibility(ev.source_url),
                "usage_guidance": self._generate_evidence_usage_guidance(ev)
            }
            
            by_confidence[conf_level].append(evidence_data)
            
            # Organize by tags
            for tag in ev.tags:
                if tag not in by_tags:
                    by_tags[tag] = []
                by_tags[tag].append(evidence_data)
        
        return {
            "by_confidence_level": by_confidence,
            "by_topic_tags": by_tags,
            "evidence_summary": {
                "total_evidence": len(evidence),
                "high_confidence_count": len(by_confidence["high"]),
                "medium_confidence_count": len(by_confidence["medium"]),
                "low_confidence_count": len(by_confidence["low"]),
                "average_confidence": sum(e.confidence for e in evidence) / len(evidence) if evidence else 0.0
            },
            "source_diversity": self._analyze_source_diversity(evidence)
        }
    
    def _create_bid_strategy_section(
        self, 
        findings: ResearchFindings, 
        validation: ValidationReport,
        bid_outline: Optional[BidOutline]
    ) -> Dict[str, Any]:
        """Create strategic guidance section for bid preparation."""
        
        critical_reqs = [r for r in findings.extracted_requirements if r.priority == "critical"]
        high_reqs = [r for r in findings.extracted_requirements if r.priority == "high"]
        
        return {
            "executive_summary": {
                "rfp_opportunity": findings.rfp_meta.title,
                "client_organization": findings.rfp_meta.organization,
                "key_opportunity": findings.rfp_meta.purpose,
                "critical_success_factors": [req.text for req in critical_reqs[:5]],
                "competitive_advantages": self._identify_competitive_advantages(findings),
                "risk_factors": [gap.why for gap in validation.gaps if "critical" in gap.why.lower()]
            },
            
            "win_strategy": {
                "primary_value_propositions": self._generate_value_propositions(findings),
                "differentiation_strategy": self._generate_differentiation_strategy(findings),
                "risk_mitigation": self._generate_risk_mitigation_strategy(validation.gaps),
                "presentation_strategy": self._generate_presentation_strategy(findings.rfp_meta.presentation_details) if findings.rfp_meta.presentation_details else None
            },
            
            "response_priorities": {
                "must_address_first": [req.text for req in critical_reqs],
                "high_impact_areas": [req.text for req in high_reqs],
                "evidence_strengths": self._identify_evidence_strengths(findings.evidence),
                "areas_needing_attention": [gap.requirement_id for gap in validation.gaps]
            },
            
            "bid_outline_guidance": bid_outline.model_dump() if bid_outline else None
        }
    
    def _create_quick_reference_section(self, findings: ResearchFindings) -> Dict[str, Any]:
        """Create quick reference section for bid writers."""
        
        return {
            "key_facts": {
                "client_name": findings.company_profile.name,
                "client_industry": findings.company_profile.industry,
                "client_size": findings.company_profile.size,
                "client_hq": findings.company_profile.hq,
                "rfp_deadline": findings.rfp_meta.deadline_iso,
                "presentation_date": findings.rfp_meta.presentation_details.date if findings.rfp_meta.presentation_details else None,
                "total_requirements": len(findings.extracted_requirements)
            },
            
            "critical_requirements_checklist": [
                {
                    "requirement": req.text,
                    "category": req.category.value,
                    "evidence_available": len([i for i in findings.mapped_insights if i.requirement_id == req.id]) > 0
                }
                for req in findings.extracted_requirements if req.priority == "critical"
            ],
            
            "client_technology_stack": findings.company_profile.technology_stack,
            "client_partnerships": findings.company_profile.partnerships,
            "client_certifications": findings.company_profile.certifications,
            
            "presentation_checklist": {
                "date": findings.rfp_meta.presentation_details.date if findings.rfp_meta.presentation_details else None,
                "location": findings.rfp_meta.presentation_details.location if findings.rfp_meta.presentation_details else None,
                "duration": findings.rfp_meta.presentation_details.duration if findings.rfp_meta.presentation_details else None,
                "attendees": findings.rfp_meta.presentation_details.attendees if findings.rfp_meta.presentation_details else [],
                "required_topics": findings.rfp_meta.presentation_details.topics_to_cover if findings.rfp_meta.presentation_details else []
            },
            
            "contact_directory": [
                {
                    "name": contact.name,
                    "title": contact.title,
                    "email": contact.email,
                    "phone": contact.phone
                }
                for contact in findings.rfp_meta.contact_info
            ]
        }
    
    def save_bid_research_package(
        self, 
        run_id: str,
        research_findings: ResearchFindings,
        validation_report: ValidationReport,
        bid_outline: Optional[BidOutline] = None,
        rfp_file_path: Optional[str] = None
    ) -> Path:
        """Save comprehensive bid research package to file."""
        
        # Create comprehensive package
        bid_package = self.create_comprehensive_bid_package(
            run_id, research_findings, validation_report, bid_outline, rfp_file_path
        )
        
        # Create run-specific directory
        run_dir = self.storage_dir / run_id
        run_dir.mkdir(exist_ok=True)
        
        # Save comprehensive bid package
        bid_package_file = run_dir / "bid_research_package.json"
        with open(bid_package_file, 'w', encoding='utf-8') as f:
            json.dump(bid_package, f, indent=2, ensure_ascii=False, default=str)
        
        # Save individual components for easy access
        self._save_individual_components(run_dir, bid_package)
        
        # Create bid writer summary
        self._create_bid_writer_summary(run_dir, bid_package)
        
        print(f"Comprehensive bid research package saved to: {bid_package_file}")
        print(f"Bid writer summary available at: {run_dir / 'BID_WRITER_SUMMARY.md'}")
        
        return bid_package_file
    
    def _save_individual_components(self, run_dir: Path, bid_package: Dict[str, Any]) -> None:
        """Save individual components for easy access."""
        
        # Save requirements analysis
        with open(run_dir / "requirements_analysis.json", 'w', encoding='utf-8') as f:
            json.dump(bid_package["requirements_analysis"], f, indent=2, ensure_ascii=False)
        
        # Save evidence repository
        with open(run_dir / "evidence_repository.json", 'w', encoding='utf-8') as f:
            json.dump(bid_package["evidence_repository"], f, indent=2, ensure_ascii=False)
        
        # Save bid strategy
        with open(run_dir / "bid_strategy.json", 'w', encoding='utf-8') as f:
            json.dump(bid_package["bid_strategy"], f, indent=2, ensure_ascii=False)
        
        # Save quick reference
        with open(run_dir / "quick_reference.json", 'w', encoding='utf-8') as f:
            json.dump(bid_package["quick_reference"], f, indent=2, ensure_ascii=False)
    
    def _create_bid_writer_summary(self, run_dir: Path, bid_package: Dict[str, Any]) -> None:
        """Create markdown summary for bid writers."""
        
        rfp_analysis = bid_package["rfp_analysis"]
        requirements = bid_package["requirements_analysis"]
        strategy = bid_package["bid_strategy"]
        quick_ref = bid_package["quick_reference"]
        
        summary = f"""# Bid Research Summary
        
## RFP Overview
- **Title**: {rfp_analysis['title']}
- **Organization**: {rfp_analysis['organization']}
- **Deadline**: {rfp_analysis['deadline']}
- **Purpose**: {rfp_analysis['purpose']}

## Presentation Requirements
- **Date**: {rfp_analysis['presentation_requirements']['date'] or 'TBD'}
- **Location**: {rfp_analysis['presentation_requirements']['location'] or 'TBD'}
- **Duration**: {rfp_analysis['presentation_requirements']['duration'] or 'TBD'}
- **Attendees**: {', '.join(rfp_analysis['presentation_requirements']['attendees'])}

## Critical Requirements ({requirements['coverage_analysis']['critical_requirements_count']})
"""
        
        for req in requirements["requirements_by_priority"]["critical"]:
            summary += f"- **{req['id']}**: {req['text']}\n"
            summary += f"  - Priority: {req['priority']} | Evidence: {req['insights_count']} insights\n"
            summary += f"  - Business Impact: {req['business_impact']}\n\n"
        
        summary += f"""
## Client Intelligence
- **Name**: {quick_ref['key_facts']['client_name']}
- **Industry**: {quick_ref['key_facts']['client_industry']}
- **Size**: {quick_ref['key_facts']['client_size']}
- **Technology Stack**: {', '.join(quick_ref['client_technology_stack'][:5])}

## Win Strategy
### Primary Value Propositions
"""
        
        for vp in strategy["win_strategy"]["primary_value_propositions"]:
            summary += f"- {vp}\n"
        
        summary += """
### Competitive Advantages
"""
        
        for ca in strategy["executive_summary"]["competitive_advantages"]:
            summary += f"- {ca}\n"
        
        summary += """
## Response Priorities
### Must Address First
"""
        
        for priority in strategy["response_priorities"]["must_address_first"][:5]:
            summary += f"- {priority}\n"
        
        summary += """
## Contact Directory
"""
        
        for contact in quick_ref["contact_directory"]:
            summary += f"- **{contact['name']}** ({contact['title']}): {contact['email']}\n"
        
        summary += """
## Timeline Milestones
"""
        
        for milestone in rfp_analysis["timeline"]:
            summary += f"- **{milestone['date']}**: {milestone['milestone']}\n"
        
        # Save summary
        with open(run_dir / "BID_WRITER_SUMMARY.md", 'w', encoding='utf-8') as f:
            f.write(summary)
    
    # Helper methods for analysis
    def _generate_bid_response_guidance(self, req: Requirement, evidence: List[Dict]) -> str:
        """Generate guidance for responding to this requirement."""
        if not evidence:
            return f"ATTENTION: No supporting evidence found. Research needed for {req.category.value} requirement."
        
        confidence_avg = sum(e["confidence"] for e in evidence) / len(evidence)
        if confidence_avg >= 0.7:
            return f"Strong evidence available ({confidence_avg:.2f} confidence). Highlight capabilities and provide specific examples."
        elif confidence_avg >= 0.4:
            return f"Moderate evidence available ({confidence_avg:.2f} confidence). Strengthen with additional case studies or certifications."
        else:
            return f"Weak evidence ({confidence_avg:.2f} confidence). Requires significant research or consider partnership/subcontracting."
    
    def _assess_source_credibility(self, url: str) -> str:
        """Assess credibility of evidence source."""
        if any(domain in url.lower() for domain in [".gov", ".edu", ".org"]):
            return "High - Official/Academic source"
        elif "linkedin.com" in url.lower() or "company.com" in url.lower():
            return "Medium - Professional/Company source"
        else:
            return "Variable - Verify credibility"
    
    def _generate_evidence_usage_guidance(self, evidence: Evidence) -> str:
        """Generate guidance for using this evidence."""
        if evidence.confidence >= 0.8:
            return "Primary evidence - Use prominently in response"
        elif evidence.confidence >= 0.6:
            return "Supporting evidence - Use to reinforce main points"
        elif evidence.confidence >= 0.4:
            return "Background evidence - Use for context only"
        else:
            return "Verify before use - Low confidence"
    
    def _identify_competitive_advantages(self, findings: ResearchFindings) -> List[str]:
        """Identify competitive advantages from research."""
        advantages = []
        
        # Technology advantages
        if findings.company_profile.technology_stack:
            advantages.append(f"Technology integration with {', '.join(findings.company_profile.technology_stack[:3])}")
        
        # Certification advantages
        if findings.company_profile.certifications:
            advantages.append(f"Industry certifications: {', '.join(findings.company_profile.certifications[:2])}")
        
        # Partnership advantages
        if findings.company_profile.partnerships:
            advantages.append(f"Strategic partnerships with {', '.join(findings.company_profile.partnerships[:2])}")
        
        return advantages
    
    def _generate_value_propositions(self, findings: ResearchFindings) -> List[str]:
        """Generate value propositions based on research."""
        return [
            f"Comprehensive {findings.company_profile.industry.lower()} expertise",
            "Proven integration capabilities with existing systems",
            "Established track record with similar organizations",
            "Strong technology foundation for scalable solutions"
        ]
    
    def _generate_differentiation_strategy(self, findings: ResearchFindings) -> List[str]:
        """Generate differentiation strategy."""
        return [
            "Emphasize technology integration capabilities",
            "Highlight industry-specific experience",
            "Showcase partnership ecosystem",
            "Demonstrate proven implementation methodology"
        ]
    
    def _generate_risk_mitigation_strategy(self, gaps: List) -> List[str]:
        """Generate risk mitigation strategy."""
        strategies = []
        for gap in gaps[:3]:  # Top 3 gaps
            if "critical" in gap.why.lower():
                strategies.append(f"Address critical gap: {gap.requirement_id}")
        return strategies
    
    def _generate_presentation_strategy(self, presentation_details: Any) -> Dict[str, Any]:
        """Generate presentation strategy."""
        return {
            "key_preparation_points": [
                "Prepare demo of integration capabilities",
                "Develop ROI calculation examples",
                "Create client-specific use cases"
            ],
            "attendee_focus": {
                attendee: "Focus on strategic value and business outcomes" 
                for attendee in presentation_details.attendees
            },
            "time_allocation": "15 min overview, 20 min capabilities demo, 10 min Q&A"
        }
    
    def _identify_evidence_strengths(self, evidence: List[Evidence]) -> List[str]:
        """Identify evidence strengths."""
        high_conf_evidence = [e for e in evidence if e.confidence >= 0.7]
        return [f"Strong evidence for {', '.join(e.tags)}" for e in high_conf_evidence[:3]]
    
    def _analyze_source_diversity(self, evidence: List[Evidence]) -> Dict[str, int]:
        """Analyze diversity of evidence sources."""
        domains = {}
        for ev in evidence:
            domain = ev.source_url.split('/')[2] if '/' in ev.source_url else ev.source_url
            domains[domain] = domains.get(domain, 0) + 1
        return domains
    
    def _create_bid_writing_priorities(self, by_priority: Dict[str, List]) -> List[str]:
        """Create prioritized list for bid writing."""
        priorities = []
        
        if by_priority["critical"]:
            priorities.append(f"Address all {len(by_priority['critical'])} critical requirements first")
        
        if by_priority["high"]:
            priorities.append(f"Develop strong responses for {len(by_priority['high'])} high-priority requirements")
        
        priorities.extend([
            "Prepare presentation materials for required topics",
            "Develop client-specific case studies",
            "Create ROI calculations and examples"
        ])
        
        return priorities
