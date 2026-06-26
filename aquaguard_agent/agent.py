import os
import sys
import re
import json
import datetime
from zoneinfo import ZoneInfo
from typing import Any

from google.adk.workflow import Workflow, START
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.apps import App, ResumabilityConfig
from google.genai import types
from pydantic import BaseModel, Field

from aquaguard_agent.config import config

# Setup Gemini model
gemini_model = Gemini(model=config.model)

# Setup MCP Toolset to launch the local mcp_server.py
mcp_server_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[mcp_server_path],
        )
    )
)

# 1. Pydantic models for structured outputs
class ReportAnalysis(BaseModel):
    description: str = Field(description="Summary of the reported water issue.")
    severity: str = Field(description="Severity rating ('Low', 'Medium', or 'High') based on standard standards.")
    contaminant: str = Field(description="Identified contaminant or issue (e.g. Lead, Turbidity, Chlorine, Mud, etc.).")
    location: str = Field(description="Extracted location of the incident.")

class ActionPlan(BaseModel):
    status: str = Field(description="Overall status of the action plan.")
    mitigation_steps: list[str] = Field(description="List of specific safety and mitigation steps for the community.")
    hotspot_logged: bool = Field(description="Whether the hotspot was successfully logged.")
    volunteers_alerted: bool = Field(description="Whether volunteers were alerted or registered.")

# 2. Specialized sub-agents
report_analyzer = LlmAgent(
    name="report_analyzer",
    model=gemini_model,
    mode="single_turn",
    instruction="""You are a professional Water Quality Report Analyzer.
Analyze the user's water issue report:
1. Use the get_water_standards tool to check standard safety thresholds if specific measurements or parameters are provided in the report.
2. Identify any contaminants or issues mentioned.
3. Extract the location of the report.
4. Classify the severity of the report as 'Low', 'Medium', or 'High' based on the contaminants.
5. Return a structured ReportAnalysis output.""",
    output_schema=ReportAnalysis,
    tools=[mcp_toolset],
)

action_planner = LlmAgent(
    name="action_planner",
    model=gemini_model,
    mode="single_turn",
    instruction="""You are a professional Community Action and Mitigation Planner.
Based on the water contamination analysis (location, contaminant, severity):
1. Log the hotspot to the community map using the log_hotspot tool.
2. If volunteers are needed or requested, use the register_volunteer tool or outline volunteer actions.
3. Formulate clear, actionable mitigation steps (e.g., boil water advisories, filter installation steps, contacting local water board).
4. Return a structured ActionPlan output.""",
    output_schema=ActionPlan,
    tools=[mcp_toolset],
)

# 3. Workflow nodes
def security_checkpoint(ctx: Context, node_input: Any) -> Event:
    user_text = ""
    if hasattr(node_input, "parts") and node_input.parts:
        user_text = "".join([part.text for part in node_input.parts if hasattr(part, "text") and part.text])
    elif isinstance(node_input, str):
        user_text = node_input
    elif isinstance(node_input, dict):
        user_text = node_input.get("text", "")
        
    # Check for prompt injection
    injection_keywords = ["ignore", "override", "system prompt", "developer mode", "jailbreak", "instruction"]
    has_injection = any(kw in user_text.lower() for kw in injection_keywords)
    
    # Scrub PII (Email & Phone)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    
    scrubbed_text = re.sub(email_pattern, "[REDACTED_EMAIL]", user_text)
    scrubbed_text = re.sub(phone_pattern, "[REDACTED_PHONE]", scrubbed_text)
    
    is_empty = len(scrubbed_text.strip()) == 0
    
    audit_event = {
        "timestamp": datetime.datetime.now(ZoneInfo("UTC")).isoformat(),
        "input_length": len(user_text),
        "has_injection": has_injection,
        "pii_detected": user_text != scrubbed_text,
        "is_empty": is_empty
    }
    
    if has_injection or is_empty:
        audit_event["severity"] = "CRITICAL"
        audit_event["status"] = "BLOCKED"
        print(json.dumps(audit_event), file=sys.stderr)
        
        block_msg = "Security block: Input contains potential prompt injection or is empty."
        return Event(
            output=block_msg,
            route="blocked",
            content=types.Content(role="model", parts=[types.Part.from_text(text=block_msg)])
        )
        
    audit_event["severity"] = "INFO"
    audit_event["status"] = "SECURED"
    print(json.dumps(audit_event), file=sys.stderr)
    
    return Event(
        output=scrubbed_text,
        route="secured",
        state={"scrubbed_input": scrubbed_text}
    )

async def human_approval(ctx: Context, node_input: Any):
    severity = node_input.get("severity", "Low")
    contaminant = node_input.get("contaminant", "Unknown")
    location = node_input.get("location", "Unknown")
    
    if severity == "High":
        if not ctx.resume_inputs or "admin_decision" not in ctx.resume_inputs:
            yield RequestInput(
                interrupt_id="admin_decision",
                message=f"✋ HIGH SEVERITY ALERT: {contaminant} contamination reported at {location}. Type 'approve' to proceed, or 'reject' to cancel."
            )
            return
            
        decision = ctx.resume_inputs["admin_decision"]
        if decision.lower() == "approve":
            audit_log = {
                "event": "HUMAN_APPROVAL_GRANTED",
                "location": location,
                "contaminant": contaminant,
                "timestamp": datetime.datetime.now(ZoneInfo("UTC")).isoformat()
            }
            print(json.dumps(audit_log), file=sys.stderr)
            yield Event(output=node_input, route="approved")
        else:
            audit_log = {
                "event": "HUMAN_APPROVAL_REJECTED",
                "location": location,
                "contaminant": contaminant,
                "timestamp": datetime.datetime.now(ZoneInfo("UTC")).isoformat()
            }
            print(json.dumps(audit_log), file=sys.stderr)
            yield Event(output="Report rejected by Administrator.", route="rejected")
    else:
        yield Event(output=node_input, route="approved")

def final_output(ctx: Context, node_input: Any):
    if isinstance(node_input, dict):
        output_str = json.dumps(node_input, indent=2)
    else:
        output_str = str(node_input)
        
    yield Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=output_str)])
    )
    yield Event(output=node_input)

# 4. Build the workflow graph
root_agent = Workflow(
    name="aquaguard_workflow",
    edges=[
        (START, security_checkpoint),
        
        (security_checkpoint, {
            "secured": report_analyzer,
            "blocked": final_output
        }),
        
        (report_analyzer, human_approval),
        
        (human_approval, {
            "approved": action_planner,
            "rejected": final_output
        }),
        
        (action_planner, final_output),
    ],
    description="AquaGuard community water reporting workflow"
)

# 5. Define App with ResumabilityConfig for HITL support
app = App(
    name="aquaguard_agent",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True)
)
