import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import Principal, get_principal
from app.core.config import get_settings
from app.domain.copilot.schemas import ChatRequest, ChatResponse
from app.domain.copilot.provider import GoogleGenAIProvider
from app.domain.copilot.service import CopilotService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def copilot_chat(
    request: ChatRequest,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    settings = Depends(get_settings)
):
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY is not configured.")
        raise HTTPException(503, "AI Copilot is not configured.")
        
    try:
        provider = GoogleGenAIProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model
        )
        service = CopilotService(
            provider=provider,
            db=db,
            organization_id=principal.organization_id
        )
        
        return service.handle_chat(request.message)
    except Exception as e:
        logger.exception("Unexpected error in copilot_chat endpoint.")
        raise HTTPException(500, "An internal error occurred while processing your request.")
