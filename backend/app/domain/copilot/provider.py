import abc
from typing import Any
import json
from pydantic import BaseModel
from google import genai
from google.genai import types

class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any]

class ProviderResponse(BaseModel):
    text: str | None = None
    tool_calls: list[ToolCallRequest] = []

class Message(BaseModel):
    role: str
    content: str
    tool_call_id: str | None = None

class CopilotProvider(abc.ABC):
    @abc.abstractmethod
    def generate(self, messages: list[Message], tools: list[dict[str, Any]]) -> ProviderResponse:
        pass

class GoogleGenAIProvider(CopilotProvider):
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=15000))
        self.model = model

    def _convert_tools(self, tools_schema: list[dict[str, Any]]) -> list[types.Tool]:
        """Convert standard JSON schema tools to Gemini API Tool objects."""
        func_decls = []
        for t in tools_schema:
            props = {}
            for prop_name, prop_details in t["parameters"]["properties"].items():
                props[prop_name] = types.Schema(
                    type=types.Type.STRING if prop_details["type"] == "string" else types.Type.INTEGER,
                    description=prop_details.get("description", "")
                )
            
            func_decls.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=props,
                        required=t["parameters"].get("required", [])
                    ) if props else None
                )
            )
        
        return [types.Tool(function_declarations=func_decls)]

    def _convert_messages(self, messages: list[Message]) -> list[types.Content]:
        contents = []
        for m in messages:
            if m.role == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m.content)]))
            elif m.role == "assistant":
                if m.tool_call_id:
                    # Not perfectly supported out of box in simpler format, but for our usage pattern,
                    # we only send the last few turns or just the system/user context.
                    # We will rely on simple content passing.
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m.content)]))
                else:
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m.content)]))
            elif m.role == "system":
                # System prompt will be passed to generate_content config directly, 
                # but if passed in messages, append as user (for simplicity if not using system instruction)
                # Actually, best to handle system separately.
                pass
            elif m.role == "tool":
                # passing tool response
                # We format it as a function response part
                parts = [
                    types.Part.from_function_response(
                        name=m.tool_call_id or "tool",
                        response={"result": json.loads(m.content)}
                    )
                ]
                contents.append(types.Content(role="user", parts=parts))
                
        return contents

    def generate(self, messages: list[Message], tools: list[dict[str, Any]]) -> ProviderResponse:
        system_msg = next((m.content for m in messages if m.role == "system"), None)
        chat_msgs = [m for m in messages if m.role != "system"]
        
        gemini_tools = self._convert_tools(tools) if tools else None
        
        config = types.GenerateContentConfig(
            temperature=0.0,
            system_instruction=system_msg,
            max_output_tokens=300
        )
        if gemini_tools:
            config.tools = gemini_tools
            
        contents = self._convert_messages(chat_msgs)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg or "exhausted" in err_msg or "resource_exhausted" in err_msg:
                raise ProviderQuotaExceededError(f"Gemini quota exceeded: {e}")
            elif "timeout" in err_msg or "deadline" in err_msg:
                raise ProviderTimeoutError(f"Gemini timeout: {e}")
            elif "500" in err_msg or "503" in err_msg or "unavailable" in err_msg:
                raise ProviderAvailabilityError(f"Gemini unavailable: {e}")
            raise ProviderAPIError(f"Gemini API Error: {e}")
        
        # Parse the response
        text = ""
        tool_calls = []
        if response.parts:
            for part in response.parts:
                if part.text:
                    text += part.text
                if part.function_call:
                    args = {}
                    if part.function_call.args:
                        # part.function_call.args is a dict
                        args = part.function_call.args
                    tool_calls.append(ToolCallRequest(
                        name=part.function_call.name,
                        arguments=args
                    ))
                    
        return ProviderResponse(text=text if text else None, tool_calls=tool_calls)

class MockProvider(CopilotProvider):
    def __init__(self, responses: list[ProviderResponse]):
        self.responses = responses
        self.call_count = 0

    def generate(self, messages: list[Message], tools: list[dict[str, Any]]) -> ProviderResponse:
        if self.call_count < len(self.responses):
            res = self.responses[self.call_count]
            self.call_count += 1
            return res
        return ProviderResponse(text="Mock response depleted")

import urllib.request
import urllib.error
import urllib.parse
import json as std_json

class ProviderAPIError(Exception):
    """Exception raised when an API provider returns an error."""
    pass

class ProviderQuotaExceededError(ProviderAPIError):
    """Exception raised specifically for 429 or quota errors."""
    pass

class ProviderTimeoutError(ProviderAPIError):
    """Exception raised specifically for timeouts."""
    pass

class ProviderAvailabilityError(ProviderAPIError):
    """Exception raised specifically for 5xx temporary availability errors."""
    pass


class OpenRouterProvider(CopilotProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def _convert_tools(self, tools_schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
        openai_tools = []
        for t in tools_schema:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
            })
        return openai_tools

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        openai_msgs = []
        for m in messages:
            if m.role == "user":
                openai_msgs.append({"role": "user", "content": m.content})
            elif m.role == "system":
                openai_msgs.append({"role": "system", "content": m.content})
            elif m.role == "assistant":
                # We format assistant correctly with or without tool calls
                if m.tool_call_id:
                    # OpenRouter/OpenAI expects a tool_calls array if the assistant made a tool call
                    openai_msgs.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": m.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": m.tool_call_id,  # Our naive system used name as ID
                                "arguments": "{}" # Not strict for context, but required format
                            }
                        }]
                    })
                else:
                    openai_msgs.append({"role": "assistant", "content": m.content})
            elif m.role == "tool":
                openai_msgs.append({
                    "role": "tool",
                    "tool_call_id": m.tool_call_id,
                    "name": m.tool_call_id,
                    "content": m.content
                })
        return openai_msgs

    def generate(self, messages: list[Message], tools: list[dict[str, Any]]) -> ProviderResponse:
        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": 0.0,
            "max_tokens": 300
        }
        if tools:
            payload["tools"] = self._convert_tools(tools)
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Bharat Business Copilot",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(self.url, data=std_json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15.0) as response:
                result = std_json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise ProviderQuotaExceededError(f"OpenRouter quota/rate limit exceeded: {e.reason}")
            elif 500 <= e.code < 600:
                raise ProviderAvailabilityError(f"OpenRouter server error {e.code}: {e.reason}")
            raise ProviderAPIError(f"OpenRouter API error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise ProviderTimeoutError("OpenRouter request timed out.")
            raise ProviderAPIError(f"OpenRouter connection error: {e.reason}")
        except TimeoutError:
            raise ProviderTimeoutError("OpenRouter request timed out.")

        choice = result["choices"][0]
        message = choice["message"]
        
        text = message.get("content")
        tool_calls = []
        
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc["function"]
                tool_calls.append(ToolCallRequest(
                    name=func["name"],
                    arguments=std_json.loads(func["arguments"]) if func.get("arguments") else {}
                ))
                
        return ProviderResponse(text=text if text else None, tool_calls=tool_calls)
