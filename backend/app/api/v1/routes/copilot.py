import logging
import uuid
import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import Principal, get_principal
from app.core.config import get_settings
from app.domain.copilot.schemas import ChatRequest, ChatResponse, ActionExecuteResponse
from app.domain.copilot.provider import GoogleGenAIProvider, OpenRouterProvider
from app.domain.copilot.service import CopilotService
from app.domain.copilot.models import CopilotActionProposal
from app.domain.inventory.service import post_movement
from app.domain.inventory.models import MovementType
from app.api.v1.routes.inventory import require_inventory_write

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
        
        fallback_provider = None
        if settings.openrouter_api_key:
            fallback_provider = OpenRouterProvider(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model
            )
            
        service = CopilotService(
            provider=provider,
            db=db,
            principal=principal,
            fallback_provider=fallback_provider
        )
        
        response = service.handle_chat(request.message)
        
        # Persist any generated action proposals (even if generation encountered a fallback error)
        db.commit()
        return response
        
    except Exception as e:
        logger.exception("Unexpected error in copilot_chat endpoint.")
        raise HTTPException(500, "An internal error occurred while processing your request.")

@router.post("/actions/{action_id}/execute", response_model=ActionExecuteResponse)
def execute_action(
    action_id: uuid.UUID,
    principal: Principal = Depends(require_inventory_write),
    db: Session = Depends(get_db)
):
    proposal = db.scalar(
        select(CopilotActionProposal)
        .where(
            CopilotActionProposal.id == action_id,
            CopilotActionProposal.organization_id == principal.organization_id,
            CopilotActionProposal.created_by == principal.user_id
        )
        .with_for_update()
    )

    if not proposal:
        raise HTTPException(404, "Action proposal not found or unauthorized.")
        
    if proposal.status != "pending":
        raise HTTPException(400, f"Action proposal cannot be executed. Status is '{proposal.status}'.")
        
    if proposal.expires_at < datetime.datetime.now(datetime.timezone.utc):
        proposal.status = "expired"
        db.commit()
        raise HTTPException(400, "Action proposal has expired.")

    p = proposal.payload
    product_id = uuid.UUID(p["product_id"])
    location_id = uuid.UUID(p["location_id"])
    quantity = Decimal(str(p["quantity"]))
    notes = p.get("notes")

    # The proposal table is the primary Copilot audit record, but we can still 
    # tie the StockMovement back to the proposal id if we want. The user said 
    # "The proposal table itself may serve as the primary Copilot audit record... 
    # Do not overwrite or misuse an existing business-reference field merely for AI provenance"
    # So we will NOT pass proposal.id as reference_id, we will leave reference_id=None 
    # (except for transfers which naturally use it to link in/out).
    
    try:
        if proposal.action_type == "receipt":
            post_movement(product_id, location_id, quantity, notes, MovementType.receipt, principal, db)
        elif proposal.action_type == "adjustment":
            post_movement(product_id, location_id, quantity, notes, MovementType.adjustment, principal, db)
        elif proposal.action_type == "transfer":
            dest_loc = uuid.UUID(p["destination_location_id"])
            if location_id == dest_loc:
                raise HTTPException(422, "Transfer locations must differ")
            ref = uuid.uuid4()
            post_movement(product_id, location_id, quantity, notes, MovementType.transfer_out, principal, db, -1, ref)
            post_movement(product_id, dest_loc, quantity, notes, MovementType.transfer_in, principal, db, 1, ref)
        else:
            raise HTTPException(400, "Unknown action type.")
            
        proposal.status = "executed"
        db.commit()
        
        return ActionExecuteResponse(status="success", message="Action executed successfully.")
        
    except HTTPException:
        # Re-raise known HTTP exceptions (like negative stock)
        db.rollback()
        raise
    except Exception as e:
        logger.exception("Error executing copilot action.")
        db.rollback()
        raise HTTPException(500, "Failed to execute action.")

@router.post("/actions/{action_id}/cancel", response_model=ActionExecuteResponse)
def cancel_action(
    action_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db)
):
    proposal = db.scalar(
        select(CopilotActionProposal)
        .where(
            CopilotActionProposal.id == action_id,
            CopilotActionProposal.organization_id == principal.organization_id,
            CopilotActionProposal.created_by == principal.user_id
        )
        .with_for_update()
    )

    if not proposal:
        raise HTTPException(404, "Action proposal not found or unauthorized.")
        
    if proposal.status != "pending":
        raise HTTPException(400, f"Action proposal cannot be cancelled. Status is '{proposal.status}'.")
        
    proposal.status = "cancelled"
    db.commit()
    
    return ActionExecuteResponse(status="success", message="Action cancelled.")
