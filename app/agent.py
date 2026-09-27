# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import datetime
from zoneinfo import ZoneInfo

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.genai import types
from vertexai.agent_engines import AdkApp

from app.a2ui_utils import a2ui_callback
from app.firestore_tools import (
    list_plants,
    get_plant_details,
    add_or_update_plant,
    log_plant_watering,
    calculate_fertilizer_dosage,
    lookup_botanical_taxonomy,
    generate_plant_image,
    generate_plant_video,
)

PROJECT_ID = "qwiklabs-gcp-02-7f80011d972c"
LOCATION = "us-east1"
MEMORY_BANK_ID = "6705778481294213120"

# Load Agent Engine resource ID from deployment_metadata.json
REMOTE_AGENT_RUNTIME_ID = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{MEMORY_BANK_ID}"
metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            REMOTE_AGENT_RUNTIME_ID = meta.get("remote_agent_runtime_id", REMOTE_AGENT_RUNTIME_ID)
            MEMORY_BANK_ID = REMOTE_AGENT_RUNTIME_ID.split("/")[-1]
    except Exception:
        pass

# Initialize Agent Engine Sandbox Code Executor
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=REMOTE_AGENT_RUNTIME_ID
)


# WRITE: Callback after turn completion to extract and persist cross-session facts to Memory Bank immediately
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        session = callback_context._invocation_context.session
        if session and session.events:
            await callback_context.add_events_to_memory(
                events=session.events,
                custom_metadata={"wait_for_completion": True},
            )
    except Exception as e:
        try:
            await callback_context.add_session_to_memory()
        except Exception:
            pass
    return None


# Memory Bank Service Builder for deployed container
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


def get_weather(query: str) -> str:
    """Simulates getting weather information.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 24°C (75°F) and sunny inside the greenhouse."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a location.

    Args:
        query: The name of the city/location to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        tz_identifier = "UTC"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Build A2UI System Prompt using A2uiSchemaManager version 0.8
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_prompt = schema_manager.generate_system_prompt(
    role_description=(
        "You are FloraCare, an expert greenhouse and plant care assistant. "
        "You help greenhouse staff and plant enthusiasts manage plant inventory, track watering schedules, "
        "calculate fertilizer dilutions, look up real botanical taxonomy data, generate plant images, "
        "and provide personalized plant care advice."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

memory_instructions = (
    "\n\n### MEMORY, ALLERGY & LOCATION INSTRUCTIONS:\n"
    "1. You have access to cross-session memory via Memory Bank (`PreloadMemoryTool`).\n"
    "2. USER ALLERGIES & SENSITIVITIES: Pay special attention to any allergies, skin sensitivities, "
    "latex intolerances, pollen reactions, or chemical/pesticide sensitivities disclosed by the user.\n"
    "3. USER LOCATIONS, REGIONS & ZONES: Pay special attention to any user location, city, state, country, "
    "growing region, USDA hardiness zone (e.g. 'Zone 9b', 'Pacific Northwest', 'Austin, TX') disclosed by the user.\n"
    "4. When the user mentions an allergy or location/region, acknowledge it and ensure it is remembered across sessions.\n"
    "5. ALWAYS check recalled user memories for location/region and allergy information before offering plant care advice, "
    "watering frequencies, outdoor hardiness guidance, or species recommendations."
)

full_instruction = a2ui_prompt + memory_instructions


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=full_instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_plants,
        get_plant_details,
        add_or_update_plant,
        log_plant_watering,
        calculate_fertilizer_dosage,
        lookup_botanical_taxonomy,
        generate_plant_image,
        generate_plant_video,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

adk_app = AdkApp(
    app=app,
    memory_service_builder=memory_bank_service_builder,
)
