"""
Call Analysis routes for LeadGen Pro
Handles AI-powered call transcription, analysis, and coaching (Gong-like features)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import os
import logging
import asyncio
import tempfile
import json

from core.database import db
from core.security import User, get_current_user

# Try to import AI libraries
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

router = APIRouter(prefix="/call-analysis", tags=["Call Analysis"])


# ==================== MODELS ====================

class CallTranscript(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    lead_id: Optional[str] = None
    agent_id: str
    transcript_text: str
    duration_seconds: int = 0
    speaker_segments: List[Dict[str, Any]] = []  # [{speaker: "agent/customer", start: 0, end: 10, text: "..."}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    transcript_id: str
    lead_id: Optional[str] = None
    agent_id: str
    
    # Quality Scores (0-100)
    overall_score: int = 0
    rapport_score: int = 0
    discovery_score: int = 0
    objection_handling_score: int = 0
    closing_score: int = 0
    
    # Extracted Insights
    summary: str = ""
    key_points: List[str] = []
    action_items: List[str] = []
    objections_raised: List[Dict[str, str]] = []  # [{objection: "...", response: "...", handled_well: bool}]
    customer_sentiment: str = "neutral"  # positive, neutral, negative
    customer_pain_points: List[str] = []
    competitor_mentions: List[str] = []
    next_steps: List[str] = []
    
    # Talk Metrics
    agent_talk_ratio: float = 0.5  # 0-1, percentage of time agent talked
    longest_monologue_seconds: int = 0
    question_count: int = 0
    filler_word_count: int = 0
    
    # Coaching
    coaching_tips: List[str] = []
    strengths: List[str] = []
    areas_for_improvement: List[str] = []
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TranscribeRequest(BaseModel):
    call_id: str
    audio_url: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

async def transcribe_audio_with_whisper(audio_path: str) -> dict:
    """Transcribe audio using OpenAI Whisper via Emergent"""
    if not EMERGENT_LLM_KEY:
        return {"error": "Transcription service not configured", "text": ""}
    
    try:
        # Use emergent integrations for Whisper
        from emergentintegrations.llm.openai_whisper import transcribe_audio
        
        result = await transcribe_audio(
            api_key=EMERGENT_LLM_KEY,
            audio_file_path=audio_path,
            response_format="verbose_json"
        )
        
        return {
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "duration": result.get("duration", 0)
        }
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return {"error": str(e), "text": ""}


async def analyze_call_with_ai(transcript: str, call_context: dict = None) -> dict:
    """Analyze call transcript using AI"""
    if not EMERGENT_LLM_KEY or not LlmChat:
        return {"error": "AI analysis not configured"}
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"call-analysis-{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert sales call analyst. Analyze sales calls to provide actionable insights, 
            identify strengths and weaknesses, and coach sales reps to improve their performance.
            Be specific, constructive, and focus on actionable feedback."""
        ).with_model("openai", "gpt-4o")
        
        context_str = ""
        if call_context:
            context_str = f"""
Call Context:
- Lead: {call_context.get('lead_name', 'Unknown')}
- Company: {call_context.get('company', 'Unknown')}
- Stage: {call_context.get('stage', 'Unknown')}
- Call Duration: {call_context.get('duration', 0)} seconds
"""
        
        prompt = f"""Analyze this sales call transcript and provide a comprehensive analysis.

{context_str}

TRANSCRIPT:
{transcript[:15000]}  # Limit transcript length

Provide your analysis in this exact JSON format:
{{
    "summary": "2-3 sentence summary of the call",
    "overall_score": 75,  // 0-100 score
    "rapport_score": 80,  // How well did they build rapport?
    "discovery_score": 70,  // How well did they uncover needs?
    "objection_handling_score": 75,  // How well did they handle objections?
    "closing_score": 65,  // How strong was the close/next steps?
    "customer_sentiment": "positive",  // positive/neutral/negative
    "key_points": ["point 1", "point 2"],
    "action_items": ["Follow up on X", "Send proposal"],
    "objections_raised": [
        {{"objection": "Too expensive", "response": "Agent's response...", "handled_well": true}}
    ],
    "customer_pain_points": ["pain point 1", "pain point 2"],
    "competitor_mentions": ["Competitor A"],
    "next_steps": ["Schedule demo", "Send pricing"],
    "agent_talk_ratio": 0.55,  // Ideal is 0.4-0.5 (customer should talk more)
    "question_count": 8,  // Number of discovery questions asked
    "coaching_tips": ["Specific tip 1", "Specific tip 2"],
    "strengths": ["What went well 1", "What went well 2"],
    "areas_for_improvement": ["Area 1", "Area 2"]
}}

Return ONLY the JSON, no other text."""

        response = await chat.send_message(UserMessage(text=prompt))
        
        # Parse response
        response_text = response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        analysis = json.loads(response_text.strip())
        return analysis
        
    except Exception as e:
        logging.error(f"AI analysis error: {e}")
        return {"error": str(e)}


# ==================== TRANSCRIPTION ENDPOINTS ====================

@router.post("/transcribe")
async def transcribe_call(
    call_id: str,
    audio_file: UploadFile = File(None),
    audio_url: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """Transcribe a call recording using AI"""
    # Get call details
    call = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Check if already transcribed
    existing = await db.call_transcripts.find_one({"call_id": call_id}, {"_id": 0})
    if existing:
        return {"message": "Call already transcribed", "transcript_id": existing["id"]}
    
    # Get audio source
    audio_source = audio_url or call.get("recording_url")
    
    if not audio_source and not audio_file:
        raise HTTPException(status_code=400, detail="No audio source provided. Upload a file or provide recording URL.")
    
    try:
        transcript_text = ""
        duration = 0
        segments = []
        
        if audio_file:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                content = await audio_file.read()
                tmp.write(content)
                tmp_path = tmp.name
            
            # Transcribe
            result = await transcribe_audio_with_whisper(tmp_path)
            transcript_text = result.get("text", "")
            duration = result.get("duration", 0)
            segments = result.get("segments", [])
            
            # Clean up
            os.unlink(tmp_path)
        else:
            # For URL-based transcription, we'd need to download first
            # For now, return placeholder
            transcript_text = f"[Transcription from URL pending: {audio_source}]"
        
        # Create transcript record
        transcript = CallTranscript(
            call_id=call_id,
            lead_id=call.get("lead_id"),
            agent_id=call.get("agent_id", current_user.id),
            transcript_text=transcript_text,
            duration_seconds=int(duration),
            speaker_segments=segments
        )
        
        transcript_doc = transcript.model_dump()
        transcript_doc["created_at"] = transcript_doc["created_at"].isoformat()
        await db.call_transcripts.insert_one(transcript_doc)
        
        # Update call record
        await db.call_logs.update_one(
            {"id": call_id},
            {"$set": {"has_transcript": True, "transcript_id": transcript.id}}
        )
        
        return {
            "success": True,
            "transcript_id": transcript.id,
            "transcript_preview": transcript_text[:500] + "..." if len(transcript_text) > 500 else transcript_text,
            "duration_seconds": int(duration)
        }
        
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.get("/transcript/{call_id}")
async def get_call_transcript(call_id: str, current_user: User = Depends(get_current_user)):
    """Get transcript for a call"""
    transcript = await db.call_transcripts.find_one({"call_id": call_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


# ==================== ANALYSIS ENDPOINTS ====================

@router.post("/analyze/{call_id}")
async def analyze_call(
    call_id: str,
    force_reanalyze: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Analyze a call using AI - extracts insights, scores quality, provides coaching"""
    # Check for existing analysis
    if not force_reanalyze:
        existing = await db.call_analyses.find_one({"call_id": call_id}, {"_id": 0})
        if existing:
            return {"message": "Analysis already exists", "analysis": existing}
    
    # Get transcript
    transcript = await db.call_transcripts.find_one({"call_id": call_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=400, detail="Call must be transcribed before analysis. Call /transcribe first.")
    
    # Get call and lead context
    call = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    lead = None
    if call and call.get("lead_id"):
        lead = await db.leads.find_one({"id": call["lead_id"]}, {"_id": 0})
    
    context = {
        "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}" if lead else "Unknown",
        "company": lead.get("company", "Unknown") if lead else "Unknown",
        "stage": lead.get("stage", "Unknown") if lead else "Unknown",
        "duration": transcript.get("duration_seconds", 0)
    }
    
    # Run AI analysis
    analysis_result = await analyze_call_with_ai(transcript["transcript_text"], context)
    
    if "error" in analysis_result:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {analysis_result['error']}")
    
    # Create analysis record
    analysis = CallAnalysis(
        call_id=call_id,
        transcript_id=transcript["id"],
        lead_id=transcript.get("lead_id"),
        agent_id=transcript.get("agent_id"),
        overall_score=analysis_result.get("overall_score", 0),
        rapport_score=analysis_result.get("rapport_score", 0),
        discovery_score=analysis_result.get("discovery_score", 0),
        objection_handling_score=analysis_result.get("objection_handling_score", 0),
        closing_score=analysis_result.get("closing_score", 0),
        summary=analysis_result.get("summary", ""),
        key_points=analysis_result.get("key_points", []),
        action_items=analysis_result.get("action_items", []),
        objections_raised=analysis_result.get("objections_raised", []),
        customer_sentiment=analysis_result.get("customer_sentiment", "neutral"),
        customer_pain_points=analysis_result.get("customer_pain_points", []),
        competitor_mentions=analysis_result.get("competitor_mentions", []),
        next_steps=analysis_result.get("next_steps", []),
        agent_talk_ratio=analysis_result.get("agent_talk_ratio", 0.5),
        question_count=analysis_result.get("question_count", 0),
        coaching_tips=analysis_result.get("coaching_tips", []),
        strengths=analysis_result.get("strengths", []),
        areas_for_improvement=analysis_result.get("areas_for_improvement", [])
    )
    
    # Save analysis
    analysis_doc = analysis.model_dump()
    analysis_doc["created_at"] = analysis_doc["created_at"].isoformat()
    
    # Upsert to handle reanalysis
    await db.call_analyses.update_one(
        {"call_id": call_id},
        {"$set": analysis_doc},
        upsert=True
    )
    
    # Update call record
    await db.call_logs.update_one(
        {"id": call_id},
        {"$set": {
            "has_analysis": True,
            "analysis_id": analysis.id,
            "call_score": analysis.overall_score
        }}
    )
    
    # Create action items as tasks if enabled
    if analysis.action_items:
        for item in analysis.action_items[:3]:  # Max 3 auto-created tasks
            task_doc = {
                "id": str(uuid.uuid4()),
                "title": item,
                "description": f"Auto-generated from call analysis",
                "type": "follow_up",
                "lead_id": analysis.lead_id,
                "assigned_to": analysis.agent_id,
                "due_date": (datetime.now(timezone.utc).replace(hour=17, minute=0)).isoformat(),
                "priority": "high",
                "completed": False,
                "source": "call_analysis",
                "call_id": call_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.tasks.insert_one(task_doc)
    
    return {
        "success": True,
        "analysis": analysis_doc,
        "tasks_created": len(analysis.action_items[:3]) if analysis.action_items else 0
    }


@router.get("/analysis/{call_id}")
async def get_call_analysis(call_id: str, current_user: User = Depends(get_current_user)):
    """Get analysis for a call"""
    analysis = await db.call_analyses.find_one({"call_id": call_id}, {"_id": 0})
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found. Run /analyze first.")
    return analysis


@router.get("/agent/{agent_id}/stats")
async def get_agent_call_stats(
    agent_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get call performance stats for an agent"""
    # Get all analyses for this agent
    analyses = await db.call_analyses.find(
        {"agent_id": agent_id},
        {"_id": 0}
    ).to_list(500)
    
    if not analyses:
        return {
            "agent_id": agent_id,
            "total_analyzed_calls": 0,
            "message": "No analyzed calls found"
        }
    
    # Calculate averages
    total = len(analyses)
    avg_overall = sum(a.get("overall_score", 0) for a in analyses) / total
    avg_rapport = sum(a.get("rapport_score", 0) for a in analyses) / total
    avg_discovery = sum(a.get("discovery_score", 0) for a in analyses) / total
    avg_objection = sum(a.get("objection_handling_score", 0) for a in analyses) / total
    avg_closing = sum(a.get("closing_score", 0) for a in analyses) / total
    avg_talk_ratio = sum(a.get("agent_talk_ratio", 0.5) for a in analyses) / total
    
    # Get common strengths and areas for improvement
    all_strengths = []
    all_improvements = []
    for a in analyses:
        all_strengths.extend(a.get("strengths", []))
        all_improvements.extend(a.get("areas_for_improvement", []))
    
    # Count occurrences
    from collections import Counter
    top_strengths = [item for item, count in Counter(all_strengths).most_common(5)]
    top_improvements = [item for item, count in Counter(all_improvements).most_common(5)]
    
    # Score distribution
    score_ranges = {"excellent": 0, "good": 0, "average": 0, "needs_work": 0}
    for a in analyses:
        score = a.get("overall_score", 0)
        if score >= 85:
            score_ranges["excellent"] += 1
        elif score >= 70:
            score_ranges["good"] += 1
        elif score >= 55:
            score_ranges["average"] += 1
        else:
            score_ranges["needs_work"] += 1
    
    return {
        "agent_id": agent_id,
        "total_analyzed_calls": total,
        "average_scores": {
            "overall": round(avg_overall, 1),
            "rapport": round(avg_rapport, 1),
            "discovery": round(avg_discovery, 1),
            "objection_handling": round(avg_objection, 1),
            "closing": round(avg_closing, 1)
        },
        "talk_ratio": {
            "average": round(avg_talk_ratio, 2),
            "ideal_range": "0.40-0.50",
            "status": "good" if 0.35 <= avg_talk_ratio <= 0.55 else "needs_adjustment"
        },
        "score_distribution": score_ranges,
        "top_strengths": top_strengths,
        "areas_for_improvement": top_improvements,
        "coaching_focus": top_improvements[0] if top_improvements else "Keep up the good work!"
    }


@router.get("/leaderboard")
async def get_call_leaderboard(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Get team leaderboard based on call scores"""
    # Aggregate scores by agent
    pipeline = [
        {"$group": {
            "_id": "$agent_id",
            "avg_score": {"$avg": "$overall_score"},
            "total_calls": {"$sum": 1},
            "avg_discovery": {"$avg": "$discovery_score"},
            "avg_closing": {"$avg": "$closing_score"}
        }},
        {"$sort": {"avg_score": -1}},
        {"$limit": limit}
    ]
    
    results = await db.call_analyses.aggregate(pipeline).to_list(limit)
    
    # Enrich with user names
    leaderboard = []
    for i, result in enumerate(results, 1):
        user = await db.users.find_one({"id": result["_id"]}, {"_id": 0, "full_name": 1})
        leaderboard.append({
            "rank": i,
            "agent_id": result["_id"],
            "agent_name": user.get("full_name", "Unknown") if user else "Unknown",
            "avg_score": round(result["avg_score"], 1),
            "total_calls": result["total_calls"],
            "avg_discovery": round(result.get("avg_discovery", 0), 1),
            "avg_closing": round(result.get("avg_closing", 0), 1)
        })
    
    return {"leaderboard": leaderboard}


# Export
__all__ = ['router', 'CallTranscript', 'CallAnalysis', 'analyze_call_with_ai']
