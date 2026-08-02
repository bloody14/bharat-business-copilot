import json
import logging
import time
from typing import Any
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError

from app.domain.copilot.provider import CopilotProvider, Message, ToolCallRequest
from app.domain.copilot.schemas import ChatResponse, ToolResult
from app.domain.copilot import tools as business_tools

logger = logging.getLogger(__name__)

# Pydantic schemas for the strictly allowed tools
class LookupProductArgs(BaseModel):
    query: str

class ProductMovementsArgs(BaseModel):
    product_sku: str
    limit: int = 5

class EmptyArgs(BaseModel):
    pass

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
    }
]

# Explicit mapping of allowed tool names to their execution functions and schemas
ALLOWED_TOOLS = {
    "get_inventory_summary": (EmptyArgs, lambda args, db, org_id: business_tools.get_inventory_summary(db, org_id)),
    "lookup_product": (LookupProductArgs, lambda args, db, org_id: business_tools.lookup_product(db, org_id, args.query)),
    "get_low_stock_products": (EmptyArgs, lambda args, db, org_id: business_tools.get_low_stock_products(db, org_id)),
    "get_recent_movements": (EmptyArgs, lambda args, db, org_id: business_tools.get_recent_movements(db, org_id)),
    "get_product_movements": (ProductMovementsArgs, lambda args, db, org_id: business_tools.get_product_movements(db, org_id, args.product_sku, args.limit)),
}

SYSTEM_PROMPT = """You are the AI Business Copilot for Bharat Business Copilot — a smart assistant for Indian MSME and small business owners.

You have read-only access to the business's inventory database through tools.

Response style:
- Lead with a **short summary** (1–2 lines).
- Show important numbers prominently.
- Use ₹ for monetary values.
- Use bullet points or numbered lists for product details.
- Flag warnings or action items clearly (e.g., "⚠️ Low Stock" or "🔴 Out of Stock").
- Keep answers concise and scannable — these are busy shop owners.
- Use Indian business terms naturally: Godown, Stock Inward, MRP, GST, SKU, Reorder Level.

Rules:
1. Ground ALL answers in tool results. Never invent numbers.
2. Always call the relevant tool FIRST, then answer based on the result.
3. If a product is not found, say so clearly.
4. You are strictly read-only. Do NOT suggest you can modify stock, create products, or perform write actions.
5. If asked something outside your scope, say so politely.
6. Keep your text ULTRA-CONCISE. Output ONLY the necessary facts, avoid conversational filler.
7. Make multiple independent tool calls simultaneously in parallel whenever possible to save time.
"""


class CopilotService:
    def __init__(self, provider: CopilotProvider, db: Session, organization_id: str):
        self.provider = provider
        self.db = db
        self.organization_id = organization_id

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
            # Execute with injected db and organization_id (Tenant Isolation)
            result = func(validated_args, self.db, self.organization_id)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.exception(f"Error executing tool {tool_call.name}")
            return json.dumps({"error": "An internal error occurred while executing the tool."})

    def _timing_log(self, timing: dict) -> None:
        logger.info(f"COPILOT_TIMING: {json.dumps(timing, indent=2)}")

    def handle_chat(self, user_message: str) -> ChatResponse:
        start_time_total = time.time()
        timing = {
            "total_s": 0.0,
            "gemini_calls": [],
            "tool_calls": [],
            "iterations": 0,
            "retries": 0,
        }

        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=user_message)
        ]
        
        tools_used = []
        max_iterations = 5
        
        response_obj = None

        for iteration in range(max_iterations):
            timing["iterations"] += 1
            try:
                prompt_chars = sum(len(str(m.content)) for m in messages if m.content)
                gen_start = time.time()
                response = self.provider.generate(messages, tools=COPILOT_TOOLS_SCHEMA)
                gen_duration = time.time() - gen_start
                timing["gemini_calls"].append({
                    "iteration": iteration + 1,
                    "duration_s": gen_duration,
                    "prompt_chars": prompt_chars
                })
            except Exception as e:
                logger.error(f"Provider error: {e}")
                timing["retries"] += 1
                error_msg = str(e).lower()
                if "timeout" in error_msg or "deadline" in error_msg or "timed out" in error_msg:
                    answer = "The request took too long. Please try again with a simpler question."
                else:
                    answer = "I'm having trouble connecting to my AI brain right now. Please try again later."
                
                # Safe application error
                response_obj = ChatResponse(
                    answer=answer,
                    tools_used=tools_used
                )
                break
            
            if response.tool_calls:
                # Add the model's tool calls to the message history so it knows what it asked
                # Note: We simulate this by appending a blank assistant message, then the tool results
                # as a 'user' message with role='tool' for Gemini compatibility in our abstraction.
                for tc in response.tool_calls:
                    tools_used.append(tc.name)
                    tool_start = time.time()
                    tool_result_str = self._execute_tool(tc)
                    tool_duration = time.time() - tool_start
                    timing["tool_calls"].append({
                        "name": tc.name,
                        "duration_s": tool_duration,
                        "result_chars": len(tool_result_str)
                    })
                    messages.append(Message(role="tool", content=tool_result_str, tool_call_id=tc.name))
                continue
            
            # If no tool calls, it's the final text answer
            if response.text:
                response_obj = ChatResponse(answer=response.text, tools_used=tools_used)
                break
            
            # Fallback if somehow both are empty
            response_obj = ChatResponse(answer="I couldn't process that request.", tools_used=tools_used)
            break

        if not response_obj:
            response_obj = ChatResponse(
                answer="I had to stop thinking because the request was too complex (max tool calls reached).",
                tools_used=tools_used
            )

        timing["total_s"] = time.time() - start_time_total
        self._timing_log(timing)
        response_obj.timing = timing
        return response_obj
