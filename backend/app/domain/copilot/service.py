import json
import logging
import time
import uuid
from typing import Any
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError

from app.core.auth import Principal
from app.domain.copilot.provider import CopilotProvider, Message, ToolCallRequest
from app.domain.copilot.schemas import ChatResponse, ToolResult, ActionProposalOutput
from app.domain.copilot import tools as business_tools
from app.domain.copilot.models import CopilotConversationMessage
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Global state for circuit breaker
_GEMINI_COOLDOWN_UNTIL = 0.0

# Pydantic schemas for the strictly allowed tools
class LookupProductArgs(BaseModel):
    query: str

class ProductMovementsArgs(BaseModel):
    product_sku: str
    limit: int = 5

class EmptyArgs(BaseModel):
    pass

class PrepareReceiptArgs(BaseModel):
    product_query: str
    location_query: str
    quantity: float

class PrepareAdjustmentArgs(BaseModel):
    product_query: str
    location_query: str
    quantity: float

class PrepareTransferArgs(BaseModel):
    product_query: str
    source_location_query: str
    destination_location_query: str
    quantity: float

# Strictly defined tool schemas exposed to the LLM (NO org_id)
COPILOT_TOOLS_SCHEMA = [
    {
        "name": "get_inventory_summary",
        "description": "Returns a high-level summary of the inventory including total items, stock quantity, low-stock, and out-of-stock counts.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "lookup_product",
        "description": "Searches products by name or SKU and returns their details and current stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Product name or SKU to search for"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_low_stock_products",
        "description": "Returns products that are at or below their reorder level.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_recent_movements",
        "description": "Returns the most recent stock movements (receipts, adjustments, transfers) across all products.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_product_movements",
        "description": "Returns the movement history for a specific product SKU.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_sku": {"type": "string", "description": "The SKU of the product to look up"},
            },
            "required": ["product_sku"]
        }
    },
    {
        "name": "prepare_stock_receipt",
        "description": "Prepares a stock receipt (inward) action for user confirmation. Use this to add stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_query": {"type": "string", "description": "Product name or SKU"},
                "location_query": {"type": "string", "description": "Location name"},
                "quantity": {"type": "number", "description": "Amount to receive"}
            },
            "required": ["product_query", "location_query", "quantity"]
        }
    },
    {
        "name": "prepare_stock_adjustment",
        "description": "Prepares a stock adjustment action for user confirmation. Use this to adjust stock (positive or negative).",
        "parameters": {
            "type": "object",
            "properties": {
                "product_query": {"type": "string", "description": "Product name or SKU"},
                "location_query": {"type": "string", "description": "Location name"},
                "quantity": {"type": "number", "description": "Adjustment amount (positive or negative)"}
            },
            "required": ["product_query", "location_query", "quantity"]
        }
    },
    {
        "name": "prepare_stock_transfer",
        "description": "Prepares a stock transfer action for user confirmation. Use this to move stock between locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_query": {"type": "string", "description": "Product name or SKU"},
                "source_location_query": {"type": "string", "description": "Source location name"},
                "destination_location_query": {"type": "string", "description": "Destination location name"},
                "quantity": {"type": "number", "description": "Amount to transfer"}
            },
            "required": ["product_query", "source_location_query", "destination_location_query", "quantity"]
        }
    }
]

# Explicit mapping of allowed tool names to their execution functions and schemas
ALLOWED_TOOLS = {
    "get_inventory_summary": (EmptyArgs, lambda args, db, principal: business_tools.get_inventory_summary(db, principal.organization_id)),
    "lookup_product": (LookupProductArgs, lambda args, db, principal: business_tools.lookup_product(db, principal.organization_id, args.query)),
    "get_low_stock_products": (EmptyArgs, lambda args, db, principal: business_tools.get_low_stock_products(db, principal.organization_id)),
    "get_recent_movements": (EmptyArgs, lambda args, db, principal: business_tools.get_recent_movements(db, principal.organization_id)),
    "get_product_movements": (ProductMovementsArgs, lambda args, db, principal: business_tools.get_product_movements(db, principal.organization_id, args.product_sku, args.limit)),
    "prepare_stock_receipt": (PrepareReceiptArgs, lambda args, db, principal: business_tools.prepare_stock_receipt(db, principal, args.product_query, args.location_query, args.quantity)),
    "prepare_stock_adjustment": (PrepareAdjustmentArgs, lambda args, db, principal: business_tools.prepare_stock_adjustment(db, principal, args.product_query, args.location_query, args.quantity)),
    "prepare_stock_transfer": (PrepareTransferArgs, lambda args, db, principal: business_tools.prepare_stock_transfer(db, principal, args.product_query, args.source_location_query, args.destination_location_query, args.quantity)),
}

SYSTEM_PROMPT = """You are the AI Business Copilot for Bharat Business Copilot — a smart assistant for Indian MSME and small business owners.

You have access to the business's inventory database through tools.

Language & Style:
- Support English, Hindi, Hinglish, Roman Hindi, and Devanagari seamlessly.
- Recognize Indian business vocabulary naturally (e.g., maal, stock, packet, piece/pcs, godown, dukaan/shop, bhej do, mangao, aaya, bacha, kharab, damage, ghata do, badha do, transfer, receive).
- Respond in the SAME language and style as the user. If they use Hinglish (e.g. "Tata tea kitna bacha h?"), reply in natural Hinglish (e.g. "Main Shop mein Tata Tea Gold ke 45 packets available hain."). If they use Hindi (Devanagari), reply in Hindi.
- Keep answers ultra-concise and scannable. Show important numbers prominently. Use ₹ for monetary values.

Rules:
1. Ground ALL answers in tool results. Never invent numbers.
2. Always call the relevant tool FIRST, then answer based on the result.
3. If a product is not found, say so clearly.
4. If the user asks you to modify stock (receive, adjust, transfer), call the appropriate `prepare_stock_*` tool. 
5. IMPORTANT: If an action (like a transfer or receipt) is requested but MISSING required fields (product, location, quantity), do NOT guess them or start a new intent. Instead, ask ONLY for the missing field in the user's language (e.g., "Kaunsa product bhejna hai?", "Kitni quantity?"). Wait for their reply in the next turn before calling the tool.
6. Once you call a prepare tool successfully, simply tell the user you have prepared the action and they need to confirm it. Do NOT claim you performed the action yourself.
7. Make multiple independent tool calls simultaneously in parallel whenever possible to save time.
"""


class CopilotService:
    def __init__(self, provider: CopilotProvider, db: Session, principal: Principal, fallback_provider: CopilotProvider | None = None):
        self.provider = provider
        self.db = db
        self.principal = principal
        self.fallback_provider = fallback_provider
        self.action_proposals = []

    def _execute_tool(self, tool_call: ToolCallRequest) -> str:
        """Safely executes an approved tool, validates arguments, and injects organization context."""
        if tool_call.name not in ALLOWED_TOOLS:
            logger.warning(f"Model attempted to call unknown or unapproved tool: {tool_call.name}")
            return json.dumps({"error": f"Tool '{tool_call.name}' is not allowed or unknown."})
        
        schema_cls, func = ALLOWED_TOOLS[tool_call.name]
        
        try:
            # Validate model-supplied arguments using Pydantic
            validated_args = schema_cls(**tool_call.arguments)
        except ValidationError as e:
            logger.warning(f"Invalid arguments supplied for tool {tool_call.name}: {e}")
            return json.dumps({"error": "Invalid arguments provided to tool."})

        try:
            # Execute with injected db and principal (Tenant Isolation)
            result = func(validated_args, self.db, self.principal)
            
            # Catch action proposals seamlessly
            if isinstance(result, dict) and result.get("_is_action_proposal"):
                proposal_data = result["proposal"]
                self.action_proposals.append(ActionProposalOutput(**proposal_data))
                return json.dumps({
                    "status": "success", 
                    "message": "Action prepared successfully. Do not output text describing the payload. Just tell the user you have set it up and they should click the Confirm button."
                })
            
            return json.dumps(result, default=str)
        except Exception as e:
            logger.exception(f"Error executing tool {tool_call.name}")
            return json.dumps({"error": "An internal error occurred while executing the tool."})

    def _timing_log(self, timing: dict) -> None:
        logger.info(f"COPILOT_TIMING: {json.dumps(timing, indent=2)}")

    def handle_chat(self, user_message: str) -> ChatResponse:
        global _GEMINI_COOLDOWN_UNTIL
        
        start_time_total = time.time()
        timing = {
            "total_s": 0.0,
            "gemini_calls": [],
            "tool_calls": [],
            "iterations": 0,
            "retries": 0,
        }

        from app.core.config import get_settings
        settings = get_settings()
        
        # 1. Fetch conversation history (bounded to Tenant and User)
        history_records = self.db.scalars(
            select(CopilotConversationMessage)
            .where(
                CopilotConversationMessage.organization_id == self.principal.organization_id,
                CopilotConversationMessage.user_id == self.principal.user_id
            )
            .order_by(CopilotConversationMessage.created_at.desc())
            .limit(settings.copilot_history_limit)
        ).all()
        
        # Reverse to get chronological order
        history_records = list(reversed(history_records))
        
        messages = [Message(role="system", content=SYSTEM_PROMPT)]
        for r in history_records:
            messages.append(Message(role=r.role, content=r.content or "", tool_call_id=r.tool_call_id))
            
        messages.append(Message(role="user", content=user_message))
        
        # To persist at the end of the request
        new_messages_to_save = [CopilotConversationMessage(
            organization_id=self.principal.organization_id,
            user_id=self.principal.user_id,
            role="user",
            content=user_message
        )]
        
        tools_used = []
        max_iterations = 5
        
        response_obj = None

        for iteration in range(max_iterations):
            timing["iterations"] += 1
            
            # Determine which provider to use
            current_provider = self.provider
            provider_name = "gemini"
            
            # Circuit Breaker Check
            if self.fallback_provider and time.time() < _GEMINI_COOLDOWN_UNTIL:
                current_provider = self.fallback_provider
                provider_name = "openrouter"
                logger.info("provider=gemini circuit_breaker=open using openrouter")
            
            try:
                prompt_chars = sum(len(str(m.content)) for m in messages if m.content)
                gen_start = time.time()
                response = current_provider.generate(messages, tools=COPILOT_TOOLS_SCHEMA)
                gen_duration = time.time() - gen_start
                timing["gemini_calls"].append({
                    "iteration": iteration + 1,
                    "duration_s": gen_duration,
                    "prompt_chars": prompt_chars,
                    "provider": provider_name
                })
            except Exception as e:
                from app.domain.copilot.provider import ProviderQuotaExceededError, ProviderTimeoutError, ProviderAvailabilityError
                logger.error(f"Provider error: {e}")
                timing["retries"] += 1
                
                # Check for fallback conditions if we tried Gemini
                if provider_name == "gemini" and self.fallback_provider and isinstance(e, (ProviderQuotaExceededError, ProviderTimeoutError, ProviderAvailabilityError)):
                    fallback_reason = "quota_exhausted" if isinstance(e, ProviderQuotaExceededError) else "timeout" if isinstance(e, ProviderTimeoutError) else "availability_error"
                    logger.warning(f"provider=gemini fallback_reason={fallback_reason} message=\"Falling back to OpenRouter\"")
                    
                    if fallback_reason == "quota_exhausted":
                        _GEMINI_COOLDOWN_UNTIL = time.time() + settings.gemini_cooldown_seconds
                        logger.warning(f"provider=gemini circuit_breaker=tripped duration={settings.gemini_cooldown_seconds}s")
                    
                    current_provider = self.fallback_provider
                    provider_name = "openrouter"
                    
                    try:
                        # Retry with fallback provider
                        gen_start = time.time()
                        response = current_provider.generate(messages, tools=COPILOT_TOOLS_SCHEMA)
                        gen_duration = time.time() - gen_start
                        timing["gemini_calls"].append({
                            "iteration": iteration + 1,
                            "duration_s": gen_duration,
                            "prompt_chars": prompt_chars,
                            "provider": provider_name
                        })
                    except Exception as fallback_e:
                        logger.error(f"Fallback provider error: {fallback_e}")
                        response_obj = ChatResponse(
                            answer="I'm having trouble connecting to my AI brain right now. Please try again later.",
                            tools_used=tools_used,
                            action_proposals=self.action_proposals
                        )
                        break
                else:
                    error_msg = str(e).lower()
                    if "timeout" in error_msg or "deadline" in error_msg or "timed out" in error_msg or isinstance(e, ProviderTimeoutError):
                        answer = "The request took too long. Please try again with a simpler question."
                    else:
                        answer = "I'm having trouble connecting to my AI brain right now. Please try again later."
                    
                    # Safe application error
                    response_obj = ChatResponse(
                        answer=answer,
                        tools_used=tools_used,
                        action_proposals=self.action_proposals
                    )
                    break
            
            if response.tool_calls:
                for tc in response.tool_calls:
                    tools_used.append(tc.name)
                    
                    # Record the model's tool call in memory
                    tc_id = str(uuid.uuid4()) # naive ID for tracking
                    new_messages_to_save.append(CopilotConversationMessage(
                        organization_id=self.principal.organization_id,
                        user_id=self.principal.user_id,
                        role="assistant",
                        content=None,
                        tool_call_id=tc.name
                    ))
                    
                    tool_start = time.time()
                    tool_result_str = self._execute_tool(tc)
                    tool_duration = time.time() - tool_start
                    timing["tool_calls"].append({
                        "name": tc.name,
                        "duration_s": tool_duration,
                        "result_chars": len(tool_result_str)
                    })
                    messages.append(Message(role="tool", content=tool_result_str, tool_call_id=tc.name))
                    
                    # Save the tool response
                    new_messages_to_save.append(CopilotConversationMessage(
                        organization_id=self.principal.organization_id,
                        user_id=self.principal.user_id,
                        role="tool",
                        content=tool_result_str,
                        tool_call_id=tc.name
                    ))
                continue
            
            if response.text:
                new_messages_to_save.append(CopilotConversationMessage(
                    organization_id=self.principal.organization_id,
                    user_id=self.principal.user_id,
                    role="assistant",
                    content=response.text
                ))
                response_obj = ChatResponse(
                    answer=response.text, 
                    tools_used=tools_used,
                    action_proposals=self.action_proposals
                )
                break
            
            response_obj = ChatResponse(
                answer="I couldn't process that request.", 
                tools_used=tools_used,
                action_proposals=self.action_proposals
            )
            break

        if not response_obj:
            response_obj = ChatResponse(
                answer="I had to stop thinking because the request was too complex (max tool calls reached).",
                tools_used=tools_used,
                action_proposals=self.action_proposals
            )

        # Persist conversation
        self.db.add_all(new_messages_to_save)

        timing["total_s"] = time.time() - start_time_total
        self._timing_log(timing)
        response_obj.timing = timing
        return response_obj
