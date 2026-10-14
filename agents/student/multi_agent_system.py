"""
AI Job Scout - Multi-Agent System
==================================================
Complete autonomous agents with WORKING SCRAPERS + Demo Mode
Refactored for Recrutia

All 7 Agents:
1. CVAnalyzerAgent - Deep CV understanding
2. JobAnalyzerAgent - Extract requirements & structure
3. MatcherAgent - Semantic matching & scoring (with keyword fallback)
4. CVOptimizerAgent - Tailor CV for specific job
5. WriterAgent - Cover letters & messages
6. AIScraperAgent - Smart multi-source scraping
7. CoordinatorAgent - Orchestrates the entire flow
"""

import os
import time
import json
import logging
import requests
import re
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

# --- CONFIGURATION ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import tools
try:
    from .tools.job_scraper import ImprovedJobScraper
except ImportError:
    try:
        from job_scraper import ImprovedJobScraper
    except ImportError:
        class ImprovedJobScraper:
            def scrape_all_sources(self, *args, **kwargs): return []

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from agents.core.base_agent import BaseAgent

# --- 1. CV ANALYZER AGENT ---

class CVAnalyzerAgent(BaseAgent):
    """Agent 1: Analyze CV content"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "CV Analyzer"

    def analyze_cv(self, cv_text: str) -> Dict:
        """Analyze CV and extract insights"""
        system_prompt = """You are a senior HR Tech Analyst with 15+ years of experience screening candidates across tech, finance, and consulting.

Your task: Deeply analyze this CV/resume to extract structured insights. The CV may be in French or English — handle both.

Analysis criteria:
- **Profile Type**: Classify as "Junior" (<2yr exp or student/intern), "Mid" (2-5yr), "Senior" (5-10yr), or "Exec" (10yr+ or C-level/VP)
- **Primary Role**: The single most accurate job title for this person right now (e.g., "Machine Learning Engineer", not just "Engineer")
- **Technical Skills**: Extract ALL technical skills mentioned (languages, frameworks, tools, platforms). Be exhaustive — include skills inferred from project descriptions
- **Soft Skills**: Leadership, communication, teamwork, etc. Only include if clearly evidenced
- **Experience Years**: Total professional experience (internships count as 0.5yr each). Return integer
- **Strengths**: 3-5 unique differentiators that make this candidate stand out
- **Recommended Roles**: 3-5 job titles this person could realistically apply to, ordered by relevance
- **Education Level**: Highest degree completed

Return ONLY a valid JSON object:
{
    "profile_type": "Junior|Mid|Senior|Exec",
    "primary_role": "string",
    "technical_skills": ["skill1", "skill2", ...],
    "soft_skills": ["skill1", "skill2"],
    "experience_years": integer,
    "strengths": ["strength1", "strength2", "strength3"],
    "recommended_roles": ["role1", "role2", "role3"],
    "education_level": "Bac|BSc|MSc|PhD|MBA|None"
}

IMPORTANT: Output raw JSON only. No markdown, no explanation, no preamble."""
        
        response = self._call_llm(f"Analyze this CV thoroughly:\n\n{cv_text[:4000]}", system_prompt)
        return self._parse_json_response(response)

# --- 2. JOB ANALYZER AGENT ---

class JobAnalyzerAgent(BaseAgent):
    """Agent 2: Analyze job postings"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "Job Analyzer"

    def analyze_job(self, job_title: str, job_description: str, company: str = "Unknown") -> Dict:
        """Analyze job posting — uses simplified prompt for HuggingFace models."""
        if self.use_huggingface:
            return self._analyze_job_simple(job_title, job_description, company)
        return self._analyze_job_full(job_title, job_description, company)

    def _analyze_job_simple(self, job_title: str, job_description: str, company: str) -> Dict:
        """Simplified job analysis for HuggingFace models."""
        prompt = f"""Extract requirements from this job posting.
        
        Job: {job_title} at {company}
        
        Description:
        {job_description[:1500]}
        
        Return ONLY valid JSON:
        {{
            "required_skills": ["list", "of", "skills"],
            "experience_level": "Junior/Mid/Senior/Lead",
            "role_focus": "Frontend/Backend/Fullstack/Data/AI/etc"
        }}"""
        
        try:
            response = self._call_llm(prompt)
            result = self._parse_json_response(response)
            if result:
                return result
        except Exception:
            pass
        return {"required_skills": [], "experience_level": "Unknown", "role_focus": "Unknown"}

    def _analyze_job_full(self, job_title: str, job_description: str, company: str) -> Dict:
        """Full job analysis for Mistral/Gemini models."""
        system_prompt = """You are a Technical Recruiter with deep expertise in parsing job postings.

Your task: Analyze this job posting and extract structured requirements.

Guidelines:
- **Required vs Preferred**: Only mark skills as "required" if the posting uses words like "must have", "required", "essential". Everything else is "preferred"
- **Experience Level**: Infer from context. "0-2yr" = Entry/Junior, "2-5yr" = Mid, "5+yr" = Senior, "Lead/Principal" = Senior+
- **Role Focus**: Be specific (e.g., "Backend/ML" not just "Backend")
- **Red Flags**: Identify concerning patterns

Return ONLY valid JSON:
{
    "required_skills": ["skill1", "skill2"],
    "preferred_skills": ["skill1", "skill2"],
    "experience_level": "Entry|Junior|Mid|Senior|Lead",
    "role_focus": "string",
    "key_responsibilities": ["responsibility1", "responsibility2"],
    "red_flags": ["flag1"] or [],
    "salary_range": "string or Unknown"
}

Output raw JSON only."""
        
        prompt = f"Job: {job_title} at {company}\n\nDescription:\n{job_description[:3000]}"
        try:
            response = self._call_llm(prompt, system_prompt)
            result = self._parse_json_response(response)
            if result:
                return result
        except Exception:
            pass
        return {"required_skills": [], "experience_level": "Unknown", "role_focus": "Unknown"}

# --- 3. MATCHER AGENT (with integrated keyword fallback) ---

class MatcherAgent(BaseAgent):
    """Agent 3: Match CV to jobs — LLM matching with keyword fallback"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "Matcher"

    def calculate_match(self, cv_analysis: Dict, job_analysis: Dict, job_title: str) -> Dict:
        """Calculate match score — tries LLM first, falls back to keyword matching."""
        try:
            if self.use_huggingface:
                result = self._match_llm_simple(cv_analysis, job_analysis, job_title)
            else:
                result = self._match_llm_full(cv_analysis, job_analysis, job_title)
            
            # If LLM returned empty or zero score, use keyword fallback
            if not result or result.get('overall_match_score', 0) == 0:
                logger.warning(f"LLM returned 0 match for '{job_title}'. Using keyword fallback.")
                raise ValueError("Zero match or empty result")
            
            return result

        except Exception as e:
            logger.info(f"Using keyword fallback for '{job_title}': {e}")
            return self._keyword_fallback(cv_analysis, job_analysis, job_title)

    def _match_llm_simple(self, cv_analysis: Dict, job_analysis: Dict, job_title: str) -> Dict:
        """Simple LLM matching for HuggingFace models."""
        c_skills = ", ".join(cv_analysis.get('technical_skills', [])[:10])
        j_skills = ", ".join(job_analysis.get('required_skills', [])[:10])
        
        prompt = f"""Act as a Recruiter. Rate the match between Candidate and Job (0-100).
        
        CANDIDATE:
        Role: {cv_analysis.get('primary_role', 'Unknown')}
        Skills: {c_skills}
        Experience: {cv_analysis.get('experience_years', 0)} years
        
        JOB:
        Title: {job_title}
        Requirements: {j_skills}
        Level: {job_analysis.get('experience_level', 'Unknown')}
        
        Return ONLY valid JSON:
        {{
            "overall_match_score": 75,
            "matching_skills": ["skill1", "skill2"],
            "missing_skills": ["skill3"],
            "recommendation": "Good Match",
            "priority": "Consider"
        }}"""
        
        response = self._call_llm(prompt)
        return self._parse_json_response(response)

    def _match_llm_full(self, cv_analysis: Dict, job_analysis: Dict, job_title: str) -> Dict:
        """Full LLM matching for Mistral/Gemini."""
        system_prompt = """You are a Talent Matching Engine. Produce accurate, consistent match scores.

SCORING RUBRIC:
1. **Technical Skills Match (40%)**: % of REQUIRED skills the candidate has
2. **Experience Level Fit (25%)**: Seniority alignment
3. **Role Alignment (20%)**: Role relevance
4. **Education & Extras (15%)**: Education, certs, domain knowledge

RECOMMENDATION THRESHOLDS:
- 80-100: "Strong Match" → priority: "Must Apply"
- 60-79: "Good Match" → priority: "Consider"
- 40-59: "Potential" → priority: "Consider"
- 0-39: "Weak Match" → priority: "Pass"

Return ONLY valid JSON:
{
    "overall_match_score": integer (0-100),
    "matching_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "recommendation": "Strong Match|Good Match|Potential|Weak Match",
    "application_tips": ["tip 1", "tip 2"],
    "priority": "Must Apply|Consider|Pass"
}

Be STRICT and CONSISTENT."""
        
        prompt = f"""CANDIDATE PROFILE:
- Primary Role: {cv_analysis.get('primary_role', 'Unknown')}
- Experience: {cv_analysis.get('experience_years', 0)} years ({cv_analysis.get('profile_type', 'Unknown')} level)
- Technical Skills: {', '.join(cv_analysis.get('technical_skills', []))}
- Soft Skills: {', '.join(cv_analysis.get('soft_skills', []))}
- Education: {cv_analysis.get('education_level', 'Unknown')}
- Strengths: {', '.join(cv_analysis.get('strengths', []))}

JOB REQUIREMENTS ({job_title}):
- Required Skills: {', '.join(job_analysis.get('required_skills', []))}
- Preferred Skills: {', '.join(job_analysis.get('preferred_skills', []))}
- Experience Level: {job_analysis.get('experience_level', 'Unknown')}
- Role Focus: {job_analysis.get('role_focus', 'Unknown')}
- Key Responsibilities: {', '.join(job_analysis.get('key_responsibilities', []))}

Score this match using the rubric."""
        
        response = self._call_llm(prompt, system_prompt)
        return self._parse_json_response(response)

    def _keyword_fallback(self, cv_analysis: Dict, job_analysis: Dict, job_title: str) -> Dict:
        """Keyword-based fallback when LLM matching fails."""
        # Extract skill sets
        cv_skills = set()
        for skill in cv_analysis.get('technical_skills', []):
            cv_skills.add(skill.lower().strip())
        for skill in cv_analysis.get('soft_skills', []):
            cv_skills.add(skill.lower().strip())
        for strength in cv_analysis.get('strengths', []):
            cv_skills.add(strength.lower().strip())

        job_reqs = set()
        for req in job_analysis.get('required_skills', []):
            job_reqs.add(req.lower().strip())
        for req in job_analysis.get('preferred_skills', []):
            job_reqs.add(req.lower().strip())

        if not job_reqs:
            # No structured requirements — score based on skill count
            match_count = len(cv_skills)
            score = min(20 + (match_count * 10), 90)
            matching_skills = list(cv_skills)[:5]
            missing_skills = []
        else:
            matching_skills = list(cv_skills.intersection(job_reqs))
            missing_skills = list(job_reqs.difference(cv_skills))
            total_reqs = len(job_reqs)
            match_count = len(matching_skills)

            if total_reqs > 0:
                base_score = (match_count / total_reqs) * 100
            else:
                base_score = 50

            # Boost if role matches title
            role = cv_analysis.get('primary_role', '').lower()
            if role and role in job_title.lower():
                base_score += 15

            score = min(round(base_score), 100)

        # Priority thresholds
        if score >= 80:
            priority, rec = "Must Apply", "Strong Match"
        elif score >= 60:
            priority, rec = "Strong Match", "Good Match"
        elif score >= 40:
            priority, rec = "Consider", "Potential Match"
        else:
            priority, rec = "Pass", "Low Match"

        return {
            "overall_match_score": score,
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "recommendation": rec,
            "application_tips": [
                "Highlight matching skills in your CV summary",
                "Mention your experience level in the cover letter",
            ],
            "priority": priority,
        }

# --- 4. CV OPTIMIZER AGENT ---

class CVOptimizerAgent(BaseAgent):
    """Agent 4: Optimize CV for jobs"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "CV Optimizer"

    def optimize_cv(self, cv_text: str, job_title: str, job_description: str) -> str:
        """Tailor CV for specific job"""
        system_prompt = """You are a Professional Resume Writer specializing in ATS-optimized resumes for the tech industry.

Your task: Rewrite the candidate's CV to maximize their chances for the target job.

RULES:
1. **Never fabricate** experience, skills, or qualifications. Only rephrase and emphasize what exists
2. **ATS Keywords**: Mirror exact keywords from the job description
3. **Quantify impact**: Turn vague statements into measurable results
4. **Relevance ordering**: Put the most job-relevant skills and experience first
5. **Language**: Write in the same language as the original CV

OUTPUT FORMAT (Markdown):

## Professional Summary
[3-4 sentences positioning the candidate for this specific role]

## Key Skills
[Bullet list of 8-12 skills, prioritized by relevance to the job]

## Relevant Experience
[2-3 most relevant experiences with quantified achievements]

## Education
[Degrees and certifications]"""
        
        prompt = f"""TARGET JOB: {job_title}

JOB DESCRIPTION:
{job_description[:1500]}

ORIGINAL CV:
{cv_text[:3000]}

Rewrite and optimize this CV for the target job."""
        
        return self._call_llm(prompt, system_prompt)

# --- 5. WRITER AGENT ---

class WriterAgent(BaseAgent):
    """Agent 5: Write application materials"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "Writer"

    def write_cover_letter(self, cv_analysis: Dict, job_title: str, company: str, job_description: str) -> str:
        """Generate cover letter"""
        system_prompt = f"""You are a Career Coach who writes compelling, personalized cover letters.

GUIDELINES:
1. **Opening hook**: Start with something specific about {company}. NO generic "I am writing to apply for…"
2. **Value proposition**: Connect relevant experiences to job needs using STAR method
3. **Authenticity**: Conversational but professional. Avoid buzzwords
4. **Closing**: Express genuine interest and suggest a next step
5. **Length**: 250-350 words maximum
6. **Language**: Match the language of the job description

Do NOT use placeholder brackets. Use actual values provided."""
        
        prompt = f"""Write a cover letter for this application:

ROLE: {job_title} at {company}

CANDIDATE:
- Current Role: {cv_analysis.get('primary_role', 'Professional')}
- Key Skills: {', '.join(cv_analysis.get('technical_skills', [])[:8])}
- Experience: {cv_analysis.get('experience_years', 0)} years
- Strengths: {', '.join(cv_analysis.get('strengths', []))}
- Education: {cv_analysis.get('education_level', 'Unknown')}

JOB DESCRIPTION:
{job_description[:1500]}

Write the cover letter now."""
        
        return self._call_llm(prompt, system_prompt)

    def write_linkedin_message(self, cv_analysis: Dict, job_title: str, company: str) -> str:
        """Generate LinkedIn connection request"""
        system_prompt = """You are a networking expert. Write a LinkedIn connection request message.

RULES:
- Maximum 280 characters (LinkedIn limit)
- Be specific: mention the exact role and one relevant skill/experience
- Sound human, not robotic
- Include a soft call to action
- Output ONLY the message text"""
        
        prompt = f"""Write a LinkedIn message to a recruiter at {company} about the {job_title} role.
I am a {cv_analysis.get('primary_role', 'professional')} with {cv_analysis.get('experience_years', 0)} years of experience.
My top skills: {', '.join(cv_analysis.get('technical_skills', [])[:3])}."""
        return self._call_llm(prompt, system_prompt)

# --- 6. SCRAPER AGENT (Using Tools) ---

class AIScraperAgent(BaseAgent):
    """Agent 6: Web scraping with CV-aware keyword search"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "Scraper"
        self.tool = ImprovedJobScraper()

    def generate_profile_demo_jobs(self, cv_analysis: Dict) -> List[Dict]:
        """Use AI to generate realistic demo jobs matching the user's actual profile"""
        skills = ", ".join(cv_analysis.get("technical_skills", [])[:5])
        role = cv_analysis.get("primary_role", "Developer")
        
        system_prompt = f"""Generate 5 realistic job postings for a {role} with skills: {skills}.
        Return a JSON list of objects with keys: title, company, location, description, url, source.
        Make them sound authentic."""
        
        response = self._call_llm(f"Generate 5 jobs for {role}", system_prompt)
        jobs = self._parse_json_response(response)
        
        if isinstance(jobs, list):
            for j in jobs:
                j['source'] = 'Demo (AI)'
                j['url'] = '#'
            return jobs
        return self.get_generic_demo_jobs()

    def get_generic_demo_jobs(self) -> List[Dict]:
        """Fallback generic demo jobs"""
        return [
            {
                "title": "Senior Python Developer",
                "company": "TechCorp AI",
                "location": "Remote",
                "description": "We are looking for an expert in Python, Django, and AI agents. Nice to have: React experience.",
                "url": "#",
                "source": "Demo"
            },
            {
                "title": "Full Stack Engineer",
                "company": "StartupX",
                "location": "Paris, France",
                "description": "Join our fast-paced team building the future of recruitment. Stack: Next.js, FastAPI, PostgreSQL.",
                "url": "#",
                "source": "Demo"
            }
        ]

# --- 7. COORDINATOR AGENT ---

class CoordinatorAgent(BaseAgent):
    """Agent 7: Coordinate all other agents"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral-small-latest", use_huggingface: bool = False, use_mistral: bool = True):
        super().__init__(api_key, model, use_huggingface, use_mistral)
        self.name = "Coordinator"
        
        # Initialize sub-agents
        self.cv_agent = CVAnalyzerAgent(api_key, model, use_huggingface, use_mistral)
        self.job_agent = JobAnalyzerAgent(api_key, model, use_huggingface, use_mistral)
        self.matcher = MatcherAgent(api_key, model, use_huggingface, use_mistral)
        self.optimizer = CVOptimizerAgent(api_key, model, use_huggingface, use_mistral)
        self.writer = WriterAgent(api_key, model, use_huggingface, use_mistral)
        self.scraper = AIScraperAgent(api_key, model, use_huggingface, use_mistral)

    def run_full_pipeline(self, cv_text: str, job_data: Dict) -> Dict:
        """Run complete pipeline for one job"""
        # 1. Analyze Job
        job_analysis = self.job_agent.analyze_job(
            job_data['title'],
            job_data['description'],
            job_data['company']
        )
        
        # 2. Optimize CV
        optimized_cv = self.optimizer.optimize_cv(
            cv_text,
            job_data['title'],
            job_data['description']
        )
        
        # 3. Analyze CV
        cv_analysis = self.cv_agent.analyze_cv(cv_text)
        
        # 4. Write Cover Letter
        cl = self.writer.write_cover_letter(
            cv_analysis,
            job_data['title'],
            job_data['company'],
            job_data['description']
        )
        
        # 5. Write LinkedIn Message
        li_msg = self.writer.write_linkedin_message(
            cv_analysis,
            job_data['title'],
            job_data['company']
        )
        
        return {
            "job_analysis": job_analysis,
            "optimized_cv": optimized_cv,
            "cover_letter": cl,
            "linkedin_message": li_msg
        }

    def intelligent_job_search(self, cv_text: str, jobs_per_site: int = 5, use_demo: bool = False, 
                             user_location: str = "", selected_sources: List[str] = None, 
                             include_remote: bool = True, progress_callback=None, 
                             cached_cv_analysis: Dict = None) -> List[Dict]:
        """Search multiple sites using CV-derived keywords and analyze jobs"""
        
        def update_progress(text, pct):
            if progress_callback:
                progress_callback(text, pct)
        
        logger.info("Starting Intelligent Job Search...")
        update_progress("🧠 Agent 1: Analyzing CV...", 10)
        
        # 1. Analyze CV
        if cached_cv_analysis:
            cv_analysis = cached_cv_analysis
        else:
            cv_analysis = self.cv_agent.analyze_cv(cv_text)
        
        # 2. Extract Keywords
        keywords = cv_analysis.get('technical_skills', [])[:3]
        role = cv_analysis.get('primary_role')
        if role:
            keywords.insert(0, role)
        
        update_progress(f"🔍 Agent 6: Scraping jobs for {keywords}...", 30)
        
        # 3. Scrape Jobs
        if use_demo:
             update_progress("🎬 Demo Mode: Generating realistic jobs...", 40)
             raw_jobs = self.scraper.generate_profile_demo_jobs(cv_analysis)
        else:
             raw_jobs = self.scraper.tool.scrape_all_sources(
                 keywords,
                 max_jobs=jobs_per_site,
                 location=user_location,
                 selected_sources=selected_sources,
                 include_remote=include_remote,
             )

        if not raw_jobs:
            logger.warning("No jobs found")
            return []
            
        update_progress(f"✨ Found {len(raw_jobs)} jobs. Agents 2 & 3: Analyzing & Matching...", 50)
        
        # 4. Match & Analyze each job
        analyzed_jobs = []
        total = len(raw_jobs)
        
        for i, job in enumerate(raw_jobs):
            # Analyze
            job_analysis = self.job_agent.analyze_job(
                job.get('title', ''), 
                job.get('description', ''),
                job.get('company', '')
            )
            
            # Match
            match_result = self.matcher.calculate_match(
                cv_analysis,
                job_analysis,
                job.get('title', '')
            )
            
            # Enrich job object
            job['ai_analysis'] = {
                'job_details': job_analysis,
                'match_result': match_result
            }
            job['ai_match_score'] = match_result.get('overall_match_score', 0)
            job['ai_priority'] = match_result.get('priority', 'Unknown')
            
            analyzed_jobs.append(job)
            update_progress(f"✅ Processed {i+1}/{total}: {job['title']}", 50 + int((i+1)/total * 40))
            
        return analyzed_jobs
