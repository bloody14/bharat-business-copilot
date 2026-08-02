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
            max_output_tokens=300,
            thinking_config=types.ThinkingConfig(thinking_budget=10)
        )
        if gemini_tools:
            config.tools = gemini_tools
            
        contents = self._convert_messages(chat_msgs)
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        
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
