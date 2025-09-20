"""Unified Bid Generation System - Creates a single comprehensive document for bid preparation."""

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
    MappedInsight,
    RequirementCategory
)


class UnifiedBidGenerator:
    """Creates a single, comprehensive document with all information needed for bid generation."""
    
    def __init__(self, storage_dir: Path = None):
        """Initialize unified bid generator."""
        self.storage_dir = storage_dir or Path("data/unified_bids")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_unified_bid_document(
        self,
        run_id: str,
        research_findings: ResearchFindings,
        validation_report: ValidationReport,
        bid_outline: Optional[BidOutline] = None,
        rfp_file_path: Optional[str] = None,
        search_queries_used: Optional[List[str]] = None
    ) -> Path:
        """Generate a single comprehensive bid document with all necessary information."""
        
        # Create the unified document structure
        unified_document = self._create_unified_structure(
            run_id, research_findings, validation_report, bid_outline, 
            rfp_file_path, search_queries_used
        )
        
        # Generate markdown document
        markdown_content = self._generate_markdown_document(unified_document)
        
        # Save the unified document
        run_dir = self.storage_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save markdown version (main document)
        markdown_file = run_dir / "UNIFIED_BID_DOCUMENT.md"
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        # Save JSON version for programmatic access
        json_file = run_dir / "unified_bid_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(unified_document, f, indent=2, default=str)
        
        print(f"Unified bid document created: {markdown_file}")
        return markdown_file
    
    def _create_unified_structure(
        self,
        run_id: str,
        research_findings: ResearchFindings,
        validation_report: ValidationReport,
        bid_outline: Optional[BidOutline],
        rfp_file_path: Optional[str],
        search_queries_used: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Create the unified document structure."""
        
        return {
            "metadata": {
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
                "rfp_file": rfp_file_path,
                "validation_score": validation_report.coverage_score
            },
            
            "rfp_summary": {
                "title": research_findings.rfp_meta.title,
                "organization": research_findings.rfp_meta.organization,
                "purpose": research_findings.rfp_meta.purpose,
                "deadline": research_findings.rfp_meta.deadline_iso,
                "project_description": research_findings.rfp_meta.project_description,
                "key_contacts": [
                    {
                        "name": contact.name,
                        "title": contact.title,
                        "email": contact.email,
                        "organization": contact.organization
                    }
                    for contact in research_findings.rfp_meta.contact_info
                ],
                "presentation_required": research_findings.rfp_meta.presentation_details is not None,
                "presentation_details": {
                    "date": research_findings.rfp_meta.presentation_details.date if research_findings.rfp_meta.presentation_details else None,
                    "location": research_findings.rfp_meta.presentation_details.location if research_findings.rfp_meta.presentation_details else None,
                    "topics": research_findings.rfp_meta.presentation_details.topics_to_cover if research_findings.rfp_meta.presentation_details else []
                } if research_findings.rfp_meta.presentation_details else None
            },
            
            "requirements_analysis": self._analyze_requirements(research_findings.extracted_requirements),
            
            "company_intelligence": {
                "name": research_findings.company_profile.name,
                "overview": research_findings.company_profile.overview,
                "key_strengths": self._extract_key_strengths(research_findings.company_profile),
                "relevant_experience": self._extract_relevant_experience(research_findings.evidence),
                "competitive_advantages": self._identify_competitive_advantages(research_findings)
            },
            
            "search_intelligence": {
                "queries_used": search_queries_used or [],
                "evidence_sources": len(research_findings.evidence),
                "confidence_score": validation_report.coverage_score
            },
            
            "bid_strategy": self._create_bid_strategy(research_findings, validation_report),
            
            "response_template": self._create_response_template(research_findings),
            
            "bid_examples": self._generate_bid_examples(research_findings)
        }
    
    def _analyze_requirements(self, requirements: List[Requirement]) -> Dict[str, Any]:
        """Analyze and categorize requirements for bid response."""
        
        # Group by category and priority
        by_category = {}
        by_priority = {"critical": [], "high": [], "medium": [], "low": []}
        
        for req in requirements:
            # Group by category
            category = req.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append({
                "id": req.id,
                "text": req.text,
                "priority": req.priority,
                "business_impact": req.business_impact,
                "source": req.source_section
            })
            
            # Group by priority
            if req.priority in by_priority:
                by_priority[req.priority].append({
                    "id": req.id,
                    "text": req.text,
                    "category": req.category.value,
                    "business_impact": req.business_impact
                })
        
        return {
            "total_requirements": len(requirements),
            "by_category": by_category,
            "by_priority": by_priority,
            "critical_count": len(by_priority["critical"]),
            "high_priority_count": len(by_priority["high"]),
            "categories_covered": list(by_category.keys())
        }
    
    def _extract_key_strengths(self, company_profile) -> List[str]:
        """Extract key company strengths from profile."""
        strengths = []
        
        if company_profile.market_position:
            strengths.append(f"Market Position: {company_profile.market_position}")
        
        if company_profile.technology_stack:
            strengths.append(f"Technology Expertise: {', '.join(company_profile.technology_stack[:3])}")
        
        if company_profile.certifications:
            strengths.append(f"Certifications: {', '.join(company_profile.certifications[:3])}")
        
        if company_profile.partnerships:
            strengths.append(f"Key Partnerships: {', '.join(company_profile.partnerships[:3])}")
        
        return strengths[:5]  # Top 5 strengths
    
    def _extract_relevant_experience(self, evidence: List[Evidence]) -> List[Dict[str, Any]]:
        """Extract relevant experience from evidence."""
        experience = []
        
        for ev in evidence[:10]:  # Top 10 pieces of evidence
            if ev.confidence > 0.5:  # Only high-confidence evidence
                experience.append({
                    "source": ev.source_url,
                    "description": ev.snippet[:200] + "..." if len(ev.snippet) > 200 else ev.snippet,
                    "confidence": ev.confidence,
                    "tags": ev.tags
                })
        
        return experience
    
    def _identify_competitive_advantages(self, research_findings: ResearchFindings) -> List[str]:
        """Identify competitive advantages based on research."""
        advantages = []
        
        # Based on company profile
        profile = research_findings.company_profile
        if profile.size and "large" in profile.size.lower():
            advantages.append("Enterprise-scale experience and resources")
        
        if profile.financial_info and any(term in profile.financial_info.lower() for term in ["stable", "growing", "profitable"]):
            advantages.append("Financial stability and growth trajectory")
        
        # Based on evidence
        high_confidence_evidence = [ev for ev in research_findings.evidence if ev.confidence > 0.7]
        if len(high_confidence_evidence) > 5:
            advantages.append("Strong track record with documented success stories")
        
        # Based on requirements coverage
        critical_reqs = [req for req in research_findings.extracted_requirements if req.priority == "critical"]
        if len(critical_reqs) > 0:
            advantages.append("Demonstrated capability to meet critical requirements")
        
        return advantages
    
    def _create_bid_strategy(self, research_findings: ResearchFindings, validation_report: ValidationReport) -> Dict[str, Any]:
        """Create bid strategy based on research findings."""
        
        return {
            "win_themes": [
                "Proven experience in similar projects",
                "Strong technical capabilities",
                "Reliable partnership and support",
                "Cost-effective solution delivery"
            ],
            "key_differentiators": self._identify_competitive_advantages(research_findings),
            "risk_mitigation": [
                "Comprehensive project management approach",
                "Proven implementation methodology", 
                "24/7 support and maintenance",
                "Risk assessment and contingency planning"
            ],
            "value_propositions": [
                "Reduced implementation time and costs",
                "Improved operational efficiency",
                "Enhanced user experience",
                "Long-term strategic partnership"
            ],
            "coverage_assessment": {
                "overall_score": validation_report.coverage_score,
                "strengths": "Strong alignment with RFP requirements",
                "areas_for_focus": validation_report.quality_notes[:3] if validation_report.quality_notes else []
            }
        }
    
    def _create_response_template(self, research_findings: ResearchFindings) -> Dict[str, Any]:
        """Create a template structure for the bid response."""
        
        requirements_by_category = {}
        for req in research_findings.extracted_requirements:
            category = req.category.value
            if category not in requirements_by_category:
                requirements_by_category[category] = []
            requirements_by_category[category].append(req)
        
        template_sections = []
        
        # Executive Summary
        template_sections.append({
            "section": "Executive Summary",
            "content": f"Response to {research_findings.rfp_meta.title}",
            "key_points": [
                "Understanding of requirements",
                "Proposed solution overview",
                "Key benefits and value proposition",
                "Company qualifications"
            ]
        })
        
        # Technical Response by Category
        for category, reqs in requirements_by_category.items():
            template_sections.append({
                "section": f"Technical Response - {category.title()}",
                "requirements_addressed": len(reqs),
                "critical_requirements": len([r for r in reqs if r.priority == "critical"]),
                "key_points": [f"Address {req.text[:50]}..." for req in reqs[:3]]
            })
        
        # Company Qualifications
        template_sections.append({
            "section": "Company Qualifications",
            "content": "Demonstrate relevant experience and capabilities",
            "key_points": [
                "Company overview and experience",
                "Relevant case studies and references",
                "Team qualifications and expertise",
                "Certifications and partnerships"
            ]
        })
        
        # Project Approach
        template_sections.append({
            "section": "Project Approach",
            "content": "Detailed implementation methodology",
            "key_points": [
                "Project management approach",
                "Implementation timeline",
                "Risk management strategy",
                "Quality assurance process"
            ]
        })
        
        return {
            "total_sections": len(template_sections),
            "sections": template_sections,
            "estimated_pages": len(template_sections) * 3,  # Rough estimate
            "presentation_required": research_findings.rfp_meta.presentation_details is not None
        }
    
    def _generate_bid_examples(self, research_findings: ResearchFindings) -> Dict[str, Any]:
        """Generate example bid responses for key requirements."""
        
        examples = {}
        
        # Get top 3 critical requirements for examples
        critical_reqs = [req for req in research_findings.extracted_requirements if req.priority == "critical"][:3]
        
        for req in critical_reqs:
            example_response = self._create_requirement_example(req, research_findings)
            examples[req.id] = example_response
        
        return {
            "total_examples": len(examples),
            "examples": examples,
            "usage_notes": [
                "Customize examples based on specific company capabilities",
                "Include specific metrics and quantifiable benefits",
                "Reference relevant case studies and experience",
                "Align with RFP evaluation criteria"
            ]
        }
    
    def _create_requirement_example(self, requirement: Requirement, research_findings: ResearchFindings) -> Dict[str, Any]:
        """Create an example response for a specific requirement."""
        
        # Find relevant evidence for this requirement
        relevant_evidence = []
        for evidence in research_findings.evidence:
            if any(tag in evidence.tags for tag in [requirement.category.value, "case-study"]):
                relevant_evidence.append(evidence)
        
        example = {
            "requirement": {
                "id": requirement.id,
                "text": requirement.text,
                "category": requirement.category.value,
                "priority": requirement.priority
            },
            "response_structure": {
                "understanding": f"We understand the need for {requirement.text.lower()}",
                "approach": f"Our approach to {requirement.category.value} involves...",
                "solution": f"We propose a solution that addresses {requirement.text.lower()}",
                "benefits": f"This approach provides {requirement.business_impact or 'significant business value'}"
            },
            "supporting_evidence": [
                {
                    "type": "experience",
                    "description": ev.snippet[:100] + "..." if len(ev.snippet) > 100 else ev.snippet,
                    "confidence": ev.confidence
                }
                for ev in relevant_evidence[:2]
            ],
            "example_text": self._generate_example_text(requirement, research_findings.company_profile.name)
        }
        
        return example
    
    def _generate_example_text(self, requirement: Requirement, company_name: str) -> str:
        """Generate example bid text for a requirement."""
        
        category_templates = {
            RequirementCategory.INTEGRATION: f"""
**Integration Capability Response:**

{company_name} has extensive experience in {requirement.text.lower()}. Our integration approach includes:

• **Technical Expertise**: Proven track record with similar integration projects
• **Methodology**: Structured approach to ensure seamless connectivity
• **Support**: Dedicated integration team with 24/7 support
• **Timeline**: Efficient implementation with minimal disruption

We propose a phased approach that ensures {requirement.business_impact or 'successful integration'}.
            """.strip(),
            
            RequirementCategory.FEATURES: f"""
**Feature Implementation Response:**

{company_name} delivers comprehensive functionality for {requirement.text.lower()}:

• **Core Features**: Full implementation of required capabilities
• **User Experience**: Intuitive interface design for optimal usability  
• **Scalability**: Solution designed to grow with your organization
• **Customization**: Flexible configuration to meet specific needs

Our solution provides {requirement.business_impact or 'enhanced operational efficiency'}.
            """.strip(),
            
            RequirementCategory.SUPPORT: f"""
**Support Services Response:**

{company_name} provides comprehensive support for {requirement.text.lower()}:

• **24/7 Availability**: Round-the-clock technical support
• **Expert Team**: Dedicated support professionals with deep expertise
• **Response Times**: Guaranteed response times based on priority levels
• **Training**: Comprehensive user training and documentation

This ensures {requirement.business_impact or 'continuous system availability and user satisfaction'}.
            """.strip()
        }
        
        return category_templates.get(
            requirement.category, 
            f"{company_name} addresses {requirement.text} through our proven capabilities and experience."
        )
    
    def _generate_markdown_document(self, unified_document: Dict[str, Any]) -> str:
        """Generate the comprehensive markdown document."""
        
        md_content = f"""# Unified Bid Document

**Generated:** {unified_document['metadata']['created_at']}  
**Run ID:** {unified_document['metadata']['run_id']}  
**Validation Score:** {unified_document['metadata']['validation_score']:.2f}

---

## RFP Summary

**Title:** {unified_document['rfp_summary']['title']}  
**Organization:** {unified_document['rfp_summary']['organization']}  
**Deadline:** {unified_document['rfp_summary']['deadline']}

**Purpose:**  
{unified_document['rfp_summary']['purpose']}

**Project Description:**  
{unified_document['rfp_summary']['project_description']}

### Key Contacts
"""
        
        for contact in unified_document['rfp_summary']['key_contacts']:
            md_content += f"- **{contact['name']}** ({contact['title']}) - {contact['email']}\n"
        
        if unified_document['rfp_summary']['presentation_required']:
            md_content += f"""
### Presentation Requirements
**Date:** {unified_document['rfp_summary']['presentation_details']['date']}  
**Location:** {unified_document['rfp_summary']['presentation_details']['location']}  
**Topics to Cover:** {', '.join(unified_document['rfp_summary']['presentation_details']['topics'])}
"""
        
        md_content += f"""
---

## Requirements Analysis

**Total Requirements:** {unified_document['requirements_analysis']['total_requirements']}  
**Critical:** {unified_document['requirements_analysis']['critical_count']}  
**High Priority:** {unified_document['requirements_analysis']['high_priority_count']}  
**Categories:** {', '.join(unified_document['requirements_analysis']['categories_covered'])}

### Critical Requirements (Must Address)
"""
        
        for req in unified_document['requirements_analysis']['by_priority']['critical']:
            md_content += f"- **{req['id']}:** {req['text']} *(Category: {req['category']})*\n"
        
        md_content += """
### Requirements by Category
"""
        
        for category, reqs in unified_document['requirements_analysis']['by_category'].items():
            md_content += f"\n#### {category.title()} ({len(reqs)} requirements)\n"
            for req in reqs[:3]:  # Show top 3 per category
                md_content += f"- **{req['id']}:** {req['text'][:80]}{'...' if len(req['text']) > 80 else ''}\n"
        
        md_content += f"""
---

## 🏢 Company Intelligence

**Company:** {unified_document['company_intelligence']['name']}

**Overview:**  
{unified_document['company_intelligence']['overview'][:500]}{'...' if len(unified_document['company_intelligence']['overview']) > 500 else ''}

### Key Strengths
"""
        
        for strength in unified_document['company_intelligence']['key_strengths']:
            md_content += f"- {strength}\n"
        
        md_content += """
### Competitive Advantages
"""
        
        for advantage in unified_document['company_intelligence']['competitive_advantages']:
            md_content += f"- {advantage}\n"
        
        md_content += f"""
### Relevant Experience
**Evidence Sources:** {len(unified_document['company_intelligence']['relevant_experience'])} high-confidence sources

"""
        
        for exp in unified_document['company_intelligence']['relevant_experience'][:5]:
            md_content += f"- **Source:** {exp['source'][:50]}{'...' if len(exp['source']) > 50 else ''}\n"
            md_content += f"  **Description:** {exp['description']}\n"
            md_content += f"  **Confidence:** {exp['confidence']:.2f}\n\n"
        
        md_content += f"""
---

## Search Intelligence

**Queries Used:** {len(unified_document['search_intelligence']['queries_used'])}  
**Evidence Sources:** {unified_document['search_intelligence']['evidence_sources']}  
**Overall Confidence:** {unified_document['search_intelligence']['confidence_score']:.2f}

### Search Queries Used
"""
        
        for i, query in enumerate(unified_document['search_intelligence']['queries_used'][:10], 1):
            md_content += f"{i}. {query}\n"
        
        md_content += f"""
---

## Bid Strategy

### Win Themes
"""
        
        for theme in unified_document['bid_strategy']['win_themes']:
            md_content += f"- {theme}\n"
        
        md_content += """
### Key Differentiators
"""
        
        for diff in unified_document['bid_strategy']['key_differentiators']:
            md_content += f"- {diff}\n"
        
        md_content += """
### Value Propositions
"""
        
        for value in unified_document['bid_strategy']['value_propositions']:
            md_content += f"- {value}\n"
        
        md_content += f"""
### Coverage Assessment
**Overall Score:** {unified_document['bid_strategy']['coverage_assessment']['overall_score']:.2f}  
**Strengths:** {unified_document['bid_strategy']['coverage_assessment']['strengths']}

**Areas for Focus:**
"""
        
        for area in unified_document['bid_strategy']['coverage_assessment']['areas_for_focus']:
            md_content += f"- {area}\n"
        
        md_content += f"""
---

## 📝 Response Template

**Total Sections:** {unified_document['response_template']['total_sections']}  
**Estimated Pages:** {unified_document['response_template']['estimated_pages']}  
**Presentation Required:** {'Yes' if unified_document['response_template']['presentation_required'] else 'No'}

### Recommended Structure
"""
        
        for section in unified_document['response_template']['sections']:
            md_content += f"\n#### {section['section']}\n"
            if 'requirements_addressed' in section:
                md_content += f"*Addresses {section['requirements_addressed']} requirements ({section['critical_requirements']} critical)*\n\n"
            else:
                md_content += f"*{section['content']}*\n\n"
            
            md_content += "**Key Points:**\n"
            for point in section['key_points']:
                md_content += f"- {point}\n"
        
        md_content += f"""
---

## 💡 Bid Examples

**Total Examples:** {unified_document['bid_examples']['total_examples']} (for critical requirements)

### Usage Notes
"""
        
        for note in unified_document['bid_examples']['usage_notes']:
            md_content += f"- {note}\n"
        
        md_content += """
### Example Responses
"""
        
        for req_id, example in unified_document['bid_examples']['examples'].items():
            req = example['requirement']
            md_content += f"""
#### {req['id']}: {req['text'][:60]}{'...' if len(req['text']) > 60 else ''}
*Category: {req['category']}, Priority: {req['priority']}*

**Response Structure:**
- **Understanding:** {example['response_structure']['understanding']}
- **Approach:** {example['response_structure']['approach']}
- **Solution:** {example['response_structure']['solution']}
- **Benefits:** {example['response_structure']['benefits']}

**Example Text:**
{example['example_text']}

**Supporting Evidence:** {len(example['supporting_evidence'])} sources available

---
"""
        
        md_content += f"""
## Summary

This unified document provides all essential information for bid preparation:

**RFP Requirements:** {unified_document['requirements_analysis']['total_requirements']} requirements analyzed  
**Company Research:** Comprehensive intelligence gathered using {len(unified_document['search_intelligence']['queries_used'])} targeted queries  
**Bid Strategy:** Win themes, differentiators, and value propositions identified  
**Response Template:** Structured approach with {unified_document['response_template']['total_sections']} sections  
**Example Responses:** {unified_document['bid_examples']['total_examples']} detailed examples for critical requirements  

**Next Steps:**
1. Review critical requirements and ensure full understanding
2. Customize example responses with specific company capabilities
3. Develop detailed technical responses using the template structure
4. Prepare presentation materials if required
5. Review and validate response against RFP evaluation criteria

---
"""
        
        return md_content
