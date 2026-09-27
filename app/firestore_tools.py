"""
Firestore and Image Generation tool integration for FloraCare Greenhouse Assistant.
"""

import os
import json
import uuid
import base64
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from google import genai
from google.genai import types
from google.cloud import firestore, storage
from google.adk.tools import ToolContext

# IMPORTANT: Hardcoded Project ID and Bucket Name strings for Agent Platform compatibility
PROJECT_ID = "qwiklabs-gcp-02-7f80011d972c"
COLLECTION_NAME = "greenhouse_plants"
BUCKET_NAME = "floracare-greenhouse-assets-027f80"


def _get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_plants() -> List[Dict[str, Any]]:
    """
    List all plants currently tracked in the FloraCare Greenhouse collection.
    
    Returns:
        List of dictionaries containing plant summary information.
    """
    db = _get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()
    plants = []
    for doc in docs:
        data = doc.to_dict()
        plants.append({
            "plant_id": doc.id,
            "common_name": data.get("common_name", "Unknown"),
            "scientific_name": data.get("scientific_name", ""),
            "species": data.get("species", ""),
            "zone": data.get("zone", ""),
            "health_status": data.get("health_status", "Healthy"),
            "last_watered": data.get("last_watered", ""),
            "watering_frequency_days": data.get("watering_frequency_days", 7)
        })
    return plants


def get_plant_details(plant_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific plant in the greenhouse by plant_id.
    
    Args:
        plant_id: Unique identifier of the plant (e.g. 'monstera-deliciosa-01')
        
    Returns:
        Dictionary with complete plant details or an error message if not found.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(plant_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Plant with ID '{plant_id}' was not found in the greenhouse database."}
    
    data = doc.to_dict()
    data["plant_id"] = doc.id
    return data


def add_or_update_plant(
    plant_id: str,
    common_name: str,
    scientific_name: str,
    species: str,
    zone: str,
    health_status: str = "Healthy",
    ideal_temperature_range: str = "18-28°C",
    ideal_humidity_range: str = "50-70%",
    watering_frequency_days: int = 7,
    care_notes: str = ""
) -> Dict[str, Any]:
    """
    Add a new plant or update details for an existing plant in the greenhouse inventory.
    
    Args:
        plant_id: Unique identifier for the plant document (e.g., 'fiddle-leaf-fig-01').
        common_name: Common name of the plant (e.g., 'Fiddle-Leaf Fig').
        scientific_name: Scientific name (e.g., 'Ficus lyrata').
        species: Botanical species or cultivar.
        zone: Greenhouse location or zone (e.g., 'Zone A - Tropical Bay').
        health_status: Health condition ('Healthy', 'Needs Attention', 'Critical').
        ideal_temperature_range: Preferred temperature range.
        ideal_humidity_range: Preferred humidity percentage.
        watering_frequency_days: Ideal interval between waterings in days.
        care_notes: Special care instructions or observation notes.
        
    Returns:
        Dictionary confirming the saved plant record.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(plant_id)
    
    existing = doc_ref.get()
    plant_data = {
        "common_name": common_name,
        "scientific_name": scientific_name,
        "species": species,
        "zone": zone,
        "health_status": health_status,
        "ideal_temperature_range": ideal_temperature_range,
        "ideal_humidity_range": ideal_humidity_range,
        "watering_frequency_days": watering_frequency_days,
        "care_notes": care_notes,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if not existing.exists:
        plant_data["created_at"] = datetime.now(timezone.utc).isoformat()
        plant_data["last_watered"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
    doc_ref.set(plant_data, merge=True)
    
    return {
        "status": "success",
        "message": f"Plant '{common_name}' ({plant_id}) was successfully saved to Firestore.",
        "plant_id": plant_id
    }


def log_plant_watering(plant_id: str, watered_by: str = "Greenhouse Staff") -> Dict[str, Any]:
    """
    Log a watering event for a plant, updating its 'last_watered' timestamp.
    
    Args:
        plant_id: Unique identifier of the plant document.
        watered_by: Name or role of the person/system watering the plant.
        
    Returns:
        Confirmation dictionary with updated watering timestamp.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(plant_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return {"error": f"Plant '{plant_id}' does not exist in inventory."}
        
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc_ref.update({
        "last_watered": today_str,
        "last_watered_by": watered_by,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "success",
        "plant_id": plant_id,
        "message": f"Successfully logged watering for plant '{plant_id}' on {today_str}.",
        "last_watered": today_str
    }


def calculate_fertilizer_dosage(
    water_volume_liters: float,
    recommended_ratio_ml_per_liter: float = 5.0,
    plant_stage: str = "vegetative"
) -> Dict[str, Any]:
    """
    Calculate liquid fertilizer concentrate needed based on water volume and growth stage.
    
    Args:
        water_volume_liters: Volume of water batch to prepare in liters.
        recommended_ratio_ml_per_liter: Standard concentrate dosage ratio in mL per Liter (default 5.0 mL/L).
        plant_stage: Plant growth stage ('seedling', 'vegetative', 'flowering', 'dormant').
        
    Returns:
        Dictionary with required fertilizer concentrate volume in mL and mixing instructions.
    """
    stage_multipliers = {
        "seedling": 0.25,
        "vegetative": 1.0,
        "flowering": 1.25,
        "dormant": 0.0
    }
    
    multiplier = stage_multipliers.get(plant_stage.lower().strip(), 1.0)
    fertilizer_ml = round(water_volume_liters * recommended_ratio_ml_per_liter * multiplier, 2)
    
    return {
        "water_volume_liters": water_volume_liters,
        "plant_stage": plant_stage,
        "fertilizer_required_ml": fertilizer_ml,
        "strength_percentage": round(multiplier * 100, 1),
        "instructions": (
            f"Mix {fertilizer_ml} mL of liquid fertilizer concentrate into "
            f"{water_volume_liters} L of clean water for plants in the {plant_stage} stage."
        )
    }


def lookup_botanical_taxonomy(plant_name: str) -> Dict[str, Any]:
    """
    Query real botanical taxonomy (family, genus, scientific classification) for a plant species using the free GBIF Public API.
    
    Args:
        plant_name: Common or scientific plant name to look up (e.g., 'Monstera deliciosa', 'Ficus lyrata', 'Spathiphyllum').
        
    Returns:
        Dictionary containing real scientific classification, family, order, genus, and match confidence.
    """
    api_key = os.environ.get("GBIF_API_KEY") or os.environ.get("PLANT_API_KEY", "")
    
    encoded_query = urllib.parse.quote(plant_name.strip())
    url = f"https://api.gbif.org/v1/species/match?name={encoded_query}"
    
    headers = {"User-Agent": "FloraCareGreenhouseAssistant/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        if data.get("matchType") == "NONE":
            return {"error": f"No botanical taxonomy matches found for '{plant_name}'."}
            
        return {
            "query": plant_name,
            "scientific_name": data.get("scientificName", data.get("canonicalName", plant_name)),
            "canonical_name": data.get("canonicalName", plant_name),
            "family": data.get("family", "Unknown"),
            "genus": data.get("genus", "Unknown"),
            "order": data.get("order", "Unknown"),
            "kingdom": data.get("kingdom", "Plantae"),
            "match_confidence": data.get("confidence", 0),
            "taxonomic_status": data.get("status", "ACCEPTED")
        }
    except Exception as exc:
        return {"error": f"Failed to fetch botanical taxonomy data: {str(exc)}"}


async def generate_plant_image(
    prompt: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Generate a high-quality visual image for a greenhouse plant or potting arrangement.
    Saves the image as a session artifact and uploads it directly to the public Cloud Storage bucket.
    
    Args:
        prompt: Detailed description of the plant or arrangement to generate (e.g. 'A lush Monstera deliciosa in a ceramic pot').
        tool_context: ADK ToolContext instance injected automatically by the framework.
        
    Returns:
        Dictionary containing the public HTTPS image URL, artifact filename, and status.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    
    # Generate image using gemini-3.1-flash-lite-image model in global region
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"High quality botanical photo for greenhouse catalog: {prompt}"
    )
    
    image_bytes = None
    mime_type = "image/jpeg"
    
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break
                
    if not image_bytes:
        return {"error": "Failed to generate plant image from the model."}
        
    ext = "jpg" if "jpeg" in mime_type else "png"
    filename = f"plant_{uuid.uuid4().hex[:8]}.{ext}"
    
    # Action (1): Save image as session artifact using tool_context.save_artifact
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    artifact_version = await tool_context.save_artifact(filename=filename, artifact=artifact_part)
    
    # Action (2): Upload image bytes directly to public GCS bucket (no local disk files)
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)
    
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    
    return {
        "status": "success",
        "prompt": prompt,
        "image_url": public_url,
        "artifact_filename": filename,
        "artifact_version": artifact_version,
        "message": f"Successfully generated plant image, saved artifact '{filename}', and uploaded to public GCS bucket."
    }


async def generate_plant_video(
    prompt: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Generate a short video clip for a greenhouse plant, watering technique, or botanical growth timelapse using Google Omni model.
    Saves the video as a session artifact and uploads it directly to the public Cloud Storage bucket.
    
    Args:
        prompt: Detailed description of the plant video to generate (e.g. 'Short timelapse video of a Monstera leaf unfurling').
        tool_context: ADK ToolContext instance injected automatically by the framework.
        
    Returns:
        Dictionary containing the public HTTPS video URL, artifact filename, and status.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short high-quality botanical video for greenhouse catalog: {prompt}"
    )
    
    if not interaction.output_video or not interaction.output_video.data:
        return {"error": "Failed to generate video from the Omni model."}
        
    video_data = interaction.output_video.data
    if isinstance(video_data, str):
        video_bytes = base64.b64decode(video_data)
    else:
        video_bytes = video_data
        
    mime_type = getattr(interaction.output_video, "mime_type", None) or "video/mp4"
    filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
    
    # Action (1): Save video as session artifact using tool_context.save_artifact
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    artifact_version = await tool_context.save_artifact(filename=filename, artifact=artifact_part)
    
    # Action (2): Upload video bytes directly to public GCS bucket (no local disk files)
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)
    
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    
    return {
        "status": "success",
        "prompt": prompt,
        "video_url": public_url,
        "artifact_filename": filename,
        "artifact_version": artifact_version,
        "message": f"Successfully generated plant video, saved artifact '{filename}', and uploaded to public GCS bucket."
    }

