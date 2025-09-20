"""Research Agent for extracting requirements and gathering evidence."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.models.schemas import (
    CompanyProfile,
    ContactInfo,
    Evidence,
    EvaluationCriteria,
    MappedInsight,
    PresentationDetails,
    RFPMeta,
    Requirement,
    RequirementCategory,
    ResearchFindings,
    TimelineItem,
)
from app.prompts import RESEARCH_AGENT_PROMPT
from app.tools import DocumentProcessor, SearchTool


class ResearchAgent(BaseAgent):
    """Agent responsible for research and evidence gathering."""

    def __init__(self) -> None:
        super().__init__("ResearchAgent", RESEARCH_AGENT_PROMPT)
        self.document_processor = DocumentProcessor()
        self.search_tool = SearchTool()
        self._last_queries_used = []  # Track queries for unified document generation

    def _extract_rfp_requirements(self, rfp_path: Path) -> tuple[RFPMeta, List[Requirement]]:
        """Extract comprehensive requirements and metadata from RFP document."""
        chunks = self.document_processor.process_document(rfp_path)
        metadata = self.document_processor.extract_metadata(rfp_path)
        
        # Combine all chunks for comprehensive analysis
        full_text = "\n".join([chunk.text for chunk in chunks])
        
        prompt = f"""
        You are an expert RFP analyst. Conduct a comprehensive analysis of this RFP document to extract ALL relevant information for bid preparation.
        
        Document metadata: {json.dumps(metadata, default=str)}
        
        Document content:
        {full_text}
        
        Extract the following information with maximum detail and accuracy:

        ## ANALYSIS REQUIREMENTS:

        ### 1. RFP Metadata
        - Title and purpose of the RFP
        - Requesting organization details
        - Project description and background
        - Budget indications (if mentioned)
        - Contract duration expectations
        - Key dates and deadlines
        - Submission requirements and format
        - Special terms and conditions

        ### 2. Contact Information
        - All contact persons mentioned
        - Their titles, organizations, contact details
        - Roles in the evaluation process

        ### 3. Presentation Requirements
        - Date, time, location, duration
        - Expected attendees and their roles
        - Topics that must be covered
        - Format requirements and constraints

        ### 4. Timeline and Milestones
        - All dates mentioned in the document
        - Milestone descriptions and deadlines
        - Process stages and their timing

        ### 5. Evaluation Criteria
        - How proposals will be evaluated
        - Scoring methods and weightings
        - Key decision factors
        - Success metrics

        ### 6. Detailed Requirements
        Categorize ALL requirements found in the document:
        - **features**: System features and functionality
        - **integration**: Integration with existing systems/tools
        - **licensing**: Licensing models and user accounts
        - **roi**: ROI, cost savings, financial benefits
        - **support**: Ongoing support and maintenance
        - **timeline**: Implementation timelines and schedules
        - **presentation**: Presentation-specific requirements
        - **evaluation**: Evaluation and selection criteria
        - **implementation**: Implementation approach requirements
        - **users**: User accounts, permissions, access levels
        - **capabilities**: Specific system capabilities needed

        For each requirement, determine:
        - Priority level (critical/high/medium/low)
        - Business impact description
        - Source section in the document

        RETURN ONLY valid JSON in this exact format:
        {{
            "rfp_meta": {{
                "title": "exact title from document",
                "version": "version if specified, else '1.0'",
                "deadline_iso": "main deadline in ISO format",
                "purpose": "purpose and background description",
                "organization": "requesting organization name",
                "project_description": "detailed project description",
                "budget_indication": "budget info if mentioned",
                "contract_duration": "expected contract duration",
                "presentation_details": {{
                    "date": "presentation date",
                    "location": "presentation location",
                    "duration": "presentation duration",
                    "format": "format requirements",
                    "attendees": ["list of expected attendees"],
                    "topics_to_cover": ["required presentation topics"]
                }},
                "timeline": [
                    {{
                        "milestone": "milestone description",
                        "date": "date or deadline",
                        "status": "pending"
                    }}
                ],
                "evaluation_criteria": [
                    {{
                        "criterion": "evaluation criterion",
                        "weight": 0.0,
                        "description": "detailed description",
                        "scoring_method": "how it's scored"
                    }}
                ],
                "contact_info": [
                    {{
                        "name": "contact name",
                        "title": "contact title",
                        "email": "email if provided",
                        "phone": "phone if provided",
                        "organization": "organization name"
                    }}
                ],
                "submission_requirements": ["list of submission requirements"],
                "special_conditions": ["special terms and conditions"]
            }},
            "requirements": [
                {{
                    "id": "REQ-001",
                    "text": "detailed requirement text",
                    "category": "appropriate category",
                    "priority": "critical/high/medium/low",
                    "business_impact": "business impact description",
                    "evaluation_weight": 0.0,
                    "source_section": "source section in document"
                }}
            ]
        }}
        
        CRITICAL: Extract ALL requirements, not just obvious ones. Look for:
        - Explicit "must have" or "shall" requirements
        - Implicit needs mentioned in background/purpose
        - Technical specifications and constraints
        - Process and methodology requirements
        - Performance and quality expectations
        - Compliance and regulatory requirements
        - User experience and interface requirements
        - Security and data protection needs
        - Scalability and future-proofing requirements
        - Training and change management needs

        Return ONLY the JSON object with no additional text or formatting.
        """
        
        messages = self._create_messages(prompt)
        response = self.llm.invoke(messages)
        
        try:
            # Clean and validate response
            response_text = response.content.strip()
            if not response_text:
                print("Empty response from LLM, using fallback")
                return self._fallback_extraction(rfp_path, full_text)
            
            # Try to extract JSON from response
            json_text = response_text
            
            # Remove markdown code blocks if present
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
            data = json.loads(json_text)
            
            # Validate required fields
            if "rfp_meta" not in data or "requirements" not in data:
                print("Missing required fields in JSON response, using fallback")
                return self._fallback_extraction(rfp_path, full_text)
            
            # Create RFPMeta with enhanced structure
            rfp_meta_data = data["rfp_meta"]
            
            # Handle presentation details
            presentation_details = None
            if rfp_meta_data.get("presentation_details"):
                presentation_details = PresentationDetails(**rfp_meta_data["presentation_details"])
            
            # Handle timeline items
            timeline_items = []
            for item in rfp_meta_data.get("timeline", []):
                timeline_items.append(TimelineItem(**item))
            
            # Handle evaluation criteria
            evaluation_criteria = []
            for criterion in rfp_meta_data.get("evaluation_criteria", []):
                evaluation_criteria.append(EvaluationCriteria(**criterion))
            
            # Handle contact info
            contact_info = []
            for contact in rfp_meta_data.get("contact_info", []):
                contact_info.append(ContactInfo(**contact))
            
            rfp_meta = RFPMeta(
                title=rfp_meta_data.get("title", ""),
                version=rfp_meta_data.get("version", "1.0"),
                deadline_iso=rfp_meta_data.get("deadline_iso", ""),
                purpose=rfp_meta_data.get("purpose", ""),
                organization=rfp_meta_data.get("organization", ""),
                project_description=rfp_meta_data.get("project_description", ""),
                budget_indication=rfp_meta_data.get("budget_indication", ""),
                contract_duration=rfp_meta_data.get("contract_duration", ""),
                presentation_details=presentation_details,
                timeline=timeline_items,
                evaluation_criteria=evaluation_criteria,
                contact_info=contact_info,
                submission_requirements=rfp_meta_data.get("submission_requirements", []),
                special_conditions=rfp_meta_data.get("special_conditions", [])
            )
            
            requirements = [Requirement(**req) for req in data["requirements"]]
            return rfp_meta, requirements
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response content: {response.content[:200]}...")
            print("Using enhanced fallback extraction with LLM analysis...")
            return self._fallback_extraction(rfp_path, full_text)
        except (KeyError, ValueError) as e:
            print(f"Failed to extract structured requirements: {e}")
            print("Using enhanced fallback extraction with LLM analysis...")
            return self._fallback_extraction(rfp_path, full_text)
        except Exception as e:
            print(f"Unexpected error during RFP extraction: {e}")
            print("Using enhanced fallback extraction...")
            return self._fallback_extraction(rfp_path, full_text)

    def _fallback_extraction(self, rfp_path: Path, text: str) -> tuple[RFPMeta, List[Requirement]]:
        """Enhanced fallback extraction with LLM analysis for better accuracy."""
        print("Using enhanced fallback extraction with LLM analysis...")
        
        # Use LLM to extract basic RFP information more accurately
        basic_info_prompt = f"""
        Analyze this RFP document and extract basic information.
        
        Document content (first 1500 characters):
        {text[:1500]}
        
        Extract the following information if available:
        1. RFP title or document title
        2. Organization/company name requesting the RFP
        3. Main purpose or goal of the RFP
        4. Any deadlines or important dates mentioned
        5. Key requirements or needs mentioned
        
        Provide a brief, factual summary of each item found.
        If information is not clearly available, indicate "Not specified in document".
        """
        
        try:
            messages = self._create_messages(basic_info_prompt)
            response = self.llm.invoke(messages)
            llm_analysis = response.content.strip()
        except Exception as e:
            print(f"LLM analysis failed, using regex fallback: {e}")
            llm_analysis = ""
        
        # Extract title from document or use filename
        title = rfp_path.stem
        if "title" in text.lower():
            title_match = re.search(r"title[:\s]+([^\n\r]+)", text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
        
        # Extract deadline if present
        deadline = "2025-12-31T23:59:59"  # Updated default year
        deadline_patterns = [
            r"deadline[:\s]+([^\n\r]+)",
            r"due[:\s]+([^\n\r]+)",
            r"submission[:\s]+([^\n\r]+)",
            r"(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})",  # Date patterns
            r"(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})"
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline = match.group(1).strip()
                break
        
        # Extract organization name with more patterns
        organization = ""
        org_patterns = [
            r"([A-Z][a-z]+\s+[A-Z][A-Z])\s+has\s+been",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+seeking",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+requires",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+invit",
            r"Kind\s+Regards\s*\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        for pattern in org_patterns:
            match = re.search(pattern, text)
            if match:
                organization = match.group(1).strip()
                break
        
        # Extract purpose/background with more flexibility
        purpose = ""
        purpose_patterns = [
            r"Purpose\s+of\s+this\s+RFP[:\s]+([^.]+\.)",
            r"Background[:\s]+([^.]+\.)",
            r"Our\s+goal\s+is\s+to\s+([^.]+\.)",
            r"We\s+are\s+seeking\s+([^.]+\.)",
            r"This\s+RFP\s+is\s+for\s+([^.]+\.)"
        ]
        for pattern in purpose_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                purpose = match.group(1).strip()
                break
        
        # Enhanced RFP metadata with new fields
        rfp_meta = RFPMeta(
            title=title,
            version="1.0",
            deadline_iso=deadline,
            purpose=purpose,
            organization=organization,
            project_description="",
            budget_indication="",
            contract_duration="",
            presentation_details=None,
            timeline=[],
            evaluation_criteria=[],
            contact_info=[],
            submission_requirements=[],
            special_conditions=[]
        )
        
        # Enhanced requirement extraction using LLM analysis + patterns
        requirements = []
        
        # First, try LLM-based requirement extraction
        if llm_analysis:
            req_extraction_prompt = f"""
            Analyze this RFP document and extract key requirements.
            
            Document content (sample):
            {text[:2000]}
            
            LLM Analysis Context:
            {llm_analysis}
            
            Identify and list specific requirements mentioned in the document.
            Look for:
            - System capabilities needed
            - Integration requirements
            - User access requirements
            - Technical specifications
            - Service requirements
            - Performance requirements
            
            For each requirement found, provide:
            - The requirement text
            - Whether it seems critical, high, medium, or low priority
            - What category it fits (integration, features, users, support, etc.)
            
            Be specific and factual. Only extract requirements that are clearly stated.
            """
            
            try:
                req_messages = self._create_messages(req_extraction_prompt)
                req_response = self.llm.invoke(req_messages)
                llm_requirements = req_response.content.strip()
                
                # Parse LLM response for requirements (simple text parsing)
                req_lines = llm_requirements.split('\n')
                req_id = 1
                
                for line in req_lines:
                    line = line.strip()
                    if line and len(line) > 20 and any(word in line.lower() for word in ['requirement', 'must', 'should', 'need', 'require']):
                        # Extract requirement text
                        req_text = line
                        if ':' in line:
                            req_text = line.split(':', 1)[1].strip()
                        
                        if len(req_text) > 15 and len(req_text) < 300:
                            category = self._categorize_requirement(req_text)
                            priority = self._determine_priority(req_text)
                            
                            requirements.append(Requirement(
                                id=f"REQ-{req_id:03d}",
                                text=req_text,
                                category=category,
                                priority=priority,
                                business_impact="Extracted from LLM analysis",
                                evaluation_weight=0.0,
                                source_section="LLM-enhanced extraction"
                            ))
                            req_id += 1
                            if req_id > 20:
                                break
                        
            except Exception as e:
                print(f"LLM requirement extraction failed: {e}")
        
        # Fallback to regex patterns if LLM didn't find enough requirements
        if len(requirements) < 3:
            print("Using regex patterns for additional requirement extraction...")
            req_patterns = [
                r"REQ-\d+[:\s]+([^.]+)",
                r"requirement[s]?\s+\d+[:\s]+([^.]+)",
                r"must\s+(?:be\s+able\s+to\s+)?([^.]+)",
                r"shall\s+([^.]+)",
                r"should\s+([^.]+)",
                r"the\s+solution\s+must\s+([^.]+)",
                r"the\s+system\s+shall\s+([^.]+)",
                r"we\s+require[:\s]+([^.]+)",
                r"capabilities[:\s]+([^.]+)",
                r"integration\s+with\s+([^.]+)",
                r"\d+\s+super\s+user\s+accounts",
                r"\d+\s+additional\s+users",
                r"AI-driven\s+([^.]+)",
                r"web-based\s+([^.]+)"
            ]
            
            req_id = len(requirements) + 1
            for pattern in req_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    req_text = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
                    if len(req_text) > 10 and len(req_text) < 300:
                        # Check if we already have this requirement
                        if not any(req_text.lower() in existing.text.lower() for existing in requirements):
                            category = self._categorize_requirement(req_text)
                            priority = self._determine_priority(req_text)
                            
                            requirements.append(Requirement(
                                id=f"REQ-{req_id:03d}",
                                text=req_text,
                                category=category,
                                priority=priority,
                                business_impact="Extracted from regex patterns",
                                evaluation_weight=0.0,
                                source_section="Regex pattern extraction"
                            ))
                            req_id += 1
                            if req_id > 25:
                                break
                if req_id > 25:
                    break
        
        return rfp_meta, requirements
    
    def _categorize_requirement(self, text: str) -> RequirementCategory:
        """Categorize requirement based on keywords with enhanced categories."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["integration", "api", "connect", "interface", "teams", "sharepoint", "salesforce"]):
            return RequirementCategory.INTEGRATION
        elif any(word in text_lower for word in ["support", "helpdesk", "service", "maintenance", "training"]):
            return RequirementCategory.SUPPORT
        elif any(word in text_lower for word in ["cost", "price", "roi", "budget", "savings", "return on investment"]):
            return RequirementCategory.ROI
        elif any(word in text_lower for word in ["license", "licensing", "permit", "agreement", "user accounts"]):
            return RequirementCategory.LICENSING
        elif any(word in text_lower for word in ["timeline", "schedule", "deadline", "time", "duration", "implementation"]):
            return RequirementCategory.TIMELINE
        elif any(word in text_lower for word in ["presentation", "present", "demo", "demonstrate"]):
            return RequirementCategory.PRESENTATION
        elif any(word in text_lower for word in ["evaluation", "assess", "scoring", "criteria", "judge"]):
            return RequirementCategory.EVALUATION
        elif any(word in text_lower for word in ["implement", "deploy", "rollout", "go-live"]):
            return RequirementCategory.IMPLEMENTATION
        elif any(word in text_lower for word in ["users", "accounts", "permissions", "access", "super user"]):
            return RequirementCategory.USERS
        elif any(word in text_lower for word in ["capability", "feature", "function", "ai-driven", "web-based"]):
            return RequirementCategory.CAPABILITIES
        else:
            return RequirementCategory.FEATURES

    def _determine_priority(self, text: str) -> str:
        """Determine priority level based on text content."""
        text_lower = text.lower()
        
        # Critical priority indicators
        if any(word in text_lower for word in ["must", "shall", "required", "mandatory", "critical", "essential"]):
            return "critical"
        # High priority indicators  
        elif any(word in text_lower for word in ["should", "important", "key", "significant", "major"]):
            return "high"
        # Low priority indicators
        elif any(word in text_lower for word in ["nice to have", "optional", "preferred", "desired", "could"]):
            return "low"
        else:
            return "medium"

    def _generate_rfp_specific_search_queries(self, company_name: str, rfp_meta: RFPMeta, requirements: List[Requirement]) -> List[str]:
        """Generate targeted search queries based on RFP context and requirements."""
        
        # Prepare RFP context for LLM
        rfp_context = f"""
        RFP Title: {rfp_meta.title}
        Organization: {rfp_meta.organization}
        Purpose: {rfp_meta.purpose}
        Project Description: {rfp_meta.project_description}
        Industry Context: {rfp_meta.organization} sector
        """
        
        # Prepare key requirements summary
        req_categories = {}
        for req in requirements[:10]:  # Focus on top 10 requirements
            category = req.category.value
            if category not in req_categories:
                req_categories[category] = []
            req_categories[category].append(req.text[:100])  # Truncate for context
        
        requirements_summary = "\n".join([
            f"- {category}: {'; '.join(reqs[:2])}"  # Max 2 examples per category
            for category, reqs in req_categories.items()
        ])
        
        # Generate targeted search queries using LLM
        query_generation_prompt = f"""
        You are a bid research specialist. Generate highly targeted search queries to research {company_name} 
        specifically for responding to this RFP. The queries should find information that directly supports 
        bid preparation and demonstrates the company's capability to meet the RFP requirements.
        
        RFP Context:
        {rfp_context}
        
        Key Requirements by Category:
        {requirements_summary}
        
        Generate 8-12 specific search queries that will find the most valuable information for this bid.
        Focus on:
        1. Company capabilities that directly match RFP requirements
        2. Relevant case studies and project experience
        3. Industry-specific expertise related to the requesting organization
        4. Technology and solutions mentioned in the RFP
        5. Partnership and integration capabilities
        6. Compliance and certifications relevant to the RFP
        7. Company size, stability, and track record in this domain
        8. Competitive advantages for this specific opportunity
        
        Return ONLY a JSON array of search query strings:
        [
            "specific search query 1",
            "specific search query 2",
            ...
        ]
        
        Make queries specific to this RFP context, not generic company research.
        Include relevant technical terms, industry keywords, and requirement-specific phrases.
        
        Examples of good RFP-specific queries:
        - "{company_name} [specific technology from RFP] implementation case study"
        - "{company_name} [industry sector] digital transformation projects"
        - "{company_name} integration with [specific systems mentioned in RFP]"
        """
        
        try:
            messages = self._create_messages(query_generation_prompt)
            response = self.llm.invoke(messages)
            
            # Parse the JSON response
            response_text = response.content.strip()
            
            # Clean JSON from markdown if present
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end > start:
                    response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end > start:
                    response_text = response_text[start:end].strip()
            
            queries = json.loads(response_text)
            
            # Validate and limit queries
            if isinstance(queries, list) and len(queries) > 0:
                # Limit to reasonable number and ensure they're strings
                valid_queries = [str(q) for q in queries if isinstance(q, str) and len(q.strip()) > 10][:3]
                
                if len(valid_queries) >= 3:
                    print(f"Generated {len(valid_queries)} RFP-specific search queries")
                    return valid_queries
            
            print("LLM query generation returned invalid format, using fallback")
            
        except (json.JSONDecodeError, KeyError, ValueError, Exception) as e:
            print(f"Failed to generate LLM queries: {e}, using enhanced fallback")
        
        # Enhanced fallback queries with RFP context
        return self._generate_fallback_queries(company_name, rfp_meta, requirements)
    
    def _generate_fallback_queries(self, company_name: str, rfp_meta: RFPMeta, requirements: List[Requirement]) -> List[str]:
        """Generate enhanced fallback queries using RFP context."""
        
        # Extract key terms from RFP
        rfp_keywords = []
        if rfp_meta.purpose:
            rfp_keywords.extend(rfp_meta.purpose.lower().split()[:3])
        if rfp_meta.project_description:
            rfp_keywords.extend(rfp_meta.project_description.lower().split()[:3])
        
        # Get top requirement categories
        req_categories = list(set(req.category.value for req in requirements[:3]))
        
        # Get technology/integration terms from requirements
        tech_terms = []
        for req in requirements:
            req_lower = req.text.lower()
            if any(tech in req_lower for tech in ['api', 'integration', 'system', 'platform', 'software']):
                # Extract potential tech terms
                words = req.text.split()[:10]
                tech_terms.extend([w for w in words if len(w) > 4 and w.lower() not in ['system', 'software', 'platform']])
        
        # Build targeted fallback queries
        fallback_queries = [
            # Core capability queries with RFP context
            f"{company_name} {rfp_meta.organization} sector experience projects",
            f"{company_name} capabilities {' '.join(req_categories[:3])}",
            
            # Technology and integration focused
            f"{company_name} integration solutions {' '.join(tech_terms[:3])}",
            f"{company_name} technology platform {rfp_meta.organization} industry",
            
            # Experience and case studies
            f"{company_name} case studies {rfp_meta.organization} sector",
            f"{company_name} implementation projects similar to {rfp_meta.title[:30]}",
            
            # Specific requirement categories
            f"{company_name} {req_categories[0] if req_categories else 'features'} expertise",
            f"{company_name} support services {rfp_meta.organization} industry",
            
            # Company profile with RFP context
            f"{company_name} company profile {' '.join(rfp_keywords[:3])}",
            f"{company_name} partnerships certifications {rfp_meta.organization} sector",
            
            # Competitive positioning
            f"{company_name} competitive advantages {' '.join(req_categories[:2])}",
            f"{company_name} market position {rfp_meta.organization} industry"
        ]
        
        # Clean and validate queries
        cleaned_queries = []
        for query in fallback_queries:
            # Remove extra spaces and ensure reasonable length
            clean_query = ' '.join(query.split())
            if len(clean_query) > 15 and len(clean_query) < 150:
                cleaned_queries.append(clean_query)
        
        print(f"Generated {len(cleaned_queries)} enhanced fallback queries with RFP context")
        return cleaned_queries[:10]  # Limit to 10 queries

    def _research_company(self, company_name: str, rfp_meta: RFPMeta, requirements: List[Requirement]) -> CompanyProfile:
        """Research comprehensive company information using RFP-specific, LLM-generated search queries."""
        # Generate RFP-specific search queries using LLM
        queries = self._generate_rfp_specific_search_queries(company_name, rfp_meta, requirements)
        
        # Store queries for unified document generation
        self._last_queries_used = queries.copy()
        
        all_results = []
        for query in queries:
            results = self.search_tool.search(query, num_results=5)
            all_results.extend(results)
        
        # Extract information from search results
        context = "\n".join([
            f"Title: {r.title}\nURL: {r.url}\nSnippet: {r.snippet}\n"
            for r in all_results[:20]  # Increased for more comprehensive data
        ])
        
        prompt = f"""
        Based on the search results, create a comprehensive company profile for {company_name}.
        Extract as much detailed information as possible for bid preparation.
        
        Search results:
        {context}
        
        Analyze the search results and provide information in a flexible JSON format.
        Be flexible with data types and handle mixed formats gracefully.
        
        Return JSON with available information:
        {{
            "name": "{company_name}",
            "overview": "detailed company description and business focus",
            "hq": "headquarters location",
            "sites": ["list", "of", "office", "locations"],
            "industry": "primary industry sector",
            "size": "company size description in text format (employees, revenue, etc.)",
            "leadership": ["key", "leadership", "personnel"],
            "financial_info": "financial information as descriptive text",
            "certifications": ["certifications", "and", "accreditations"],
            "technology_stack": ["technology", "platforms", "and", "tools"],
            "service_areas": ["primary", "service", "offerings"],
            "market_position": "competitive positioning and advantages",
            "recent_projects": ["recent", "relevant", "projects"],
            "partnerships": ["strategic", "partnerships", "and", "alliances"],
            "additional_info": "any other relevant information found"
        }}
        
        IMPORTANT: 
        - Use descriptive text for complex data like financial info and company size
        - If information is not available, use empty strings or empty arrays
        - Do not fabricate data - only use what's found in search results
        - Be flexible with data formats and handle edge cases gracefully
        """
        
        messages = self._create_messages(prompt)
        response = self.llm.invoke(messages)
        
        try:
            # Clean and parse response
            response_text = response.content.strip()
            json_text = response_text
            
            # Remove markdown code blocks if present
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
            
            data = json.loads(json_text)
            return CompanyProfile(**data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse company profile JSON: {e}")
            print("Using LLM-based flexible analysis...")
            
            # Use LLM to analyze the context directly without strict JSON
            flexible_prompt = f"""
            Analyze the search results for {company_name} and extract key information.
            Focus on practical information useful for bid preparation.
            
            Search results:
            {context[:2000]}  # Limit context for token efficiency
            
            Provide a brief analysis covering:
            1. Company overview and industry
            2. Size and scale information  
            3. Key capabilities and services
            4. Technology or partnerships mentioned
            5. Any other relevant details
            
            Keep the response concise and factual.
            """
            
            try:
                flexible_messages = self._create_messages(flexible_prompt)
                flexible_response = self.llm.invoke(flexible_messages)
                analysis = flexible_response.content.strip()
            except Exception:
                analysis = f"Limited information available for {company_name} from search results."
            
            # Create flexible profile with LLM analysis
            return CompanyProfile(
                name=company_name,
                overview=analysis[:500] if analysis else f"Company profile for {company_name}",
                hq="To be determined from additional research",
                sites=[],
                industry="To be determined",
                size="Information not available in current search results",
                leadership=[],
                financial_info="Financial information not available in current search results",
                certifications=[],
                technology_stack=[],
                service_areas=[],
                market_position="Market position to be determined from additional research",
                recent_projects=[],
                partnerships=[],
                additional_info=analysis if analysis else ""
            )

    def _generate_evidence_queries(self, requirement: Requirement, company_profile: CompanyProfile) -> List[str]:
        """Generate targeted search queries to find evidence for a specific requirement."""
        
        # Extract key terms from the requirement text
        req_words = requirement.text.lower().split()
        key_terms = [word for word in req_words if len(word) > 4 and word not in ['must', 'shall', 'should', 'will', 'need', 'require', 'system']][:4]
        
        # Build targeted queries based on requirement category and content
        base_queries = []
        
        if requirement.category == RequirementCategory.INTEGRATION:
            base_queries = [
                f"{company_profile.name} integration {' '.join(key_terms[:2])} experience",
                f"{company_profile.name} API connectivity {' '.join(key_terms[:2])}",
                f"{company_profile.name} system integration case study {key_terms[0] if key_terms else 'platform'}",
                f"{company_profile.name} integration capabilities {requirement.category.value}"
            ]
        elif requirement.category == RequirementCategory.FEATURES:
            base_queries = [
                f"{company_profile.name} features {' '.join(key_terms[:3])}",
                f"{company_profile.name} functionality {' '.join(key_terms[:2])} capabilities",
                f"{company_profile.name} product features {key_terms[0] if key_terms else 'system'}",
                f"{company_profile.name} solution capabilities {requirement.text[:30]}"
            ]
        elif requirement.category == RequirementCategory.SUPPORT:
            base_queries = [
                f"{company_profile.name} support services {' '.join(key_terms[:2])}",
                f"{company_profile.name} customer support {requirement.category.value}",
                f"{company_profile.name} maintenance services {key_terms[0] if key_terms else 'support'}",
                f"{company_profile.name} service level agreement SLA"
            ]
        elif requirement.category == RequirementCategory.USERS:
            base_queries = [
                f"{company_profile.name} user management {' '.join(key_terms[:2])}",
                f"{company_profile.name} user accounts permissions {key_terms[0] if key_terms else 'access'}",
                f"{company_profile.name} user access control system",
                f"{company_profile.name} user administration capabilities"
            ]
        elif requirement.category == RequirementCategory.CAPABILITIES:
            base_queries = [
                f"{company_profile.name} capabilities {' '.join(key_terms[:3])}",
                f"{company_profile.name} technology capabilities {' '.join(key_terms[:2])}",
                f"{company_profile.name} platform capabilities {key_terms[0] if key_terms else 'system'}",
                f"{company_profile.name} solution capabilities demonstration"
            ]
        else:
            # Generic queries for other categories
            base_queries = [
                f"{company_profile.name} {requirement.category.value} {' '.join(key_terms[:2])}",
                f"{company_profile.name} {' '.join(key_terms[:3])} experience",
                f"{company_profile.name} case study {requirement.category.value}",
                f"{company_profile.name} expertise {' '.join(key_terms[:2])}"
            ]
        
        # Add priority-based queries for critical requirements
        if requirement.priority == "critical":
            base_queries.extend([
                f"{company_profile.name} proven track record {' '.join(key_terms[:2])}",
                f"{company_profile.name} success stories {requirement.category.value}"
            ])
        
        # Clean and validate queries
        cleaned_queries = []
        for query in base_queries:
            clean_query = ' '.join(query.split())  # Remove extra spaces
            if len(clean_query) > 20 and len(clean_query) < 120:  # Reasonable length
                cleaned_queries.append(clean_query)
        
        return cleaned_queries[:4]  # Limit to 4 queries per requirement

    def _gather_evidence(self, requirements: List[Requirement], company_profile: CompanyProfile) -> List[Evidence]:
        """Gather evidence for requirements using targeted, requirement-specific queries."""
        evidence = []
        
        for req in requirements[:2]:  # Increased limit for more comprehensive evidence
            # Create highly targeted search queries for this specific requirement
            queries = self._generate_evidence_queries(req, company_profile)
            
            for query in queries:
                results = self.search_tool.search(query, num_results=3)
                
                for result in results:
                    # Score relevance
                    confidence = self._calculate_confidence(result, req, company_profile)
                    
                    if confidence > 0.3:  # Threshold for inclusion
                        evidence.append(Evidence(
                            source_url=result.url,
                            snippet=result.snippet,
                            confidence=confidence,
                            tags=[req.category.value, "search-result"]
                        ))
        
        return evidence

    def _calculate_confidence(self, search_result, requirement: Requirement, company_profile: CompanyProfile) -> float:
        """Calculate confidence score for evidence."""
        score = 0.0
        
        # URL credibility
        if company_profile.name.lower().replace(" ", "") in search_result.url.lower():
            score += 0.3  # Official company source
        elif any(domain in search_result.url for domain in [".gov", ".edu", ".org"]):
            score += 0.2  # Credible domain
        
        # Content relevance
        snippet_lower = search_result.snippet.lower()
        req_words = requirement.text.lower().split()
        
        word_matches = sum(1 for word in req_words if word in snippet_lower)
        if word_matches > 0:
            score += min(0.4, word_matches / len(req_words) * 0.4)
        
        # Company name presence
        if company_profile.name.lower() in snippet_lower:
            score += 0.2
        
        return min(1.0, score)

    def _create_insights(self, requirements: List[Requirement], evidence: List[Evidence]) -> List[MappedInsight]:
        """Create mapped insights connecting requirements to evidence."""
        insights = []
        
        for req in requirements:
            relevant_evidence = []
            
            # Find relevant evidence for this requirement
            for j, ev in enumerate(evidence):
                if req.category.value in ev.tags or any(
                    word in ev.snippet.lower() 
                    for word in req.text.lower().split()[:3]  # First 3 words
                ):
                    relevant_evidence.append(j)
            
            if relevant_evidence:
                # Calculate overall confidence
                evidence_confidences = [evidence[j].confidence for j in relevant_evidence]
                avg_confidence = sum(evidence_confidences) / len(evidence_confidences)
                
                insights.append(MappedInsight(
                    requirement_id=req.id,
                    rationale=f"Evidence found supporting {req.category.value} requirement",
                    supporting_evidence_idx=relevant_evidence,
                    confidence=avg_confidence
                ))
        
        return insights

    def process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ResearchFindings:
        """Process RFP and company research."""
        rfp_path = Path(input_data["rfp_path"])
        company_name = input_data["company_name"]
        
        # Extract RFP requirements
        rfp_meta, requirements = self._extract_rfp_requirements(rfp_path)
        
        # Research company using RFP-specific queries
        company_profile = self._research_company(company_name, rfp_meta, requirements)
        
        # Gather evidence
        evidence = self._gather_evidence(requirements, company_profile)
        
        # Create insights
        mapped_insights = self._create_insights(requirements, evidence)
        
        return ResearchFindings(
            rfp_meta=rfp_meta,
            extracted_requirements=requirements,
            company_profile=company_profile,
            evidence=evidence,
            mapped_insights=mapped_insights
        )
