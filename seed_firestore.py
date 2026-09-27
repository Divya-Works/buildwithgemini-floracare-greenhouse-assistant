import datetime
from google.cloud import firestore

# Hardcoded GCP Project ID (crucial for Agent Platform deployment compatibility)
PROJECT_ID = "qwiklabs-gcp-02-7f80011d972c"

INITIAL_PLANTS = [
    {
        "plant_id": "monstera-deliciosa",
        "common_name": "Swiss Cheese Plant",
        "scientific_name": "Monstera deliciosa",
        "species": "Araceae",
        "zone": "Zone A - Tropical Bay",
        "health_status": "Healthy",
        "ideal_temperature_range": "18-28°C",
        "ideal_humidity_range": "60-80%",
        "watering_frequency_days": 7,
        "last_watered": "2026-09-21",
        "care_notes": "Loves high humidity and a moss pole for climbing support."
    },
    {
        "plant_id": "snake-plant",
        "common_name": "Sansevieria Laurentii",
        "scientific_name": "Dracaena trifasciata",
        "species": "Asparagaceae",
        "zone": "Zone B - Arid Section",
        "health_status": "Healthy",
        "ideal_temperature_range": "15-30°C",
        "ideal_humidity_range": "30-50%",
        "watering_frequency_days": 14,
        "last_watered": "2026-09-15",
        "care_notes": "Drought tolerant; allow soil to dry completely between waterings."
    },
    {
        "plant_id": "peace-lily",
        "common_name": "Spathiphyllum Bloom",
        "scientific_name": "Spathiphyllum wallisii",
        "species": "Araceae",
        "zone": "Zone C - Shade Bay",
        "health_status": "Needs Attention",
        "ideal_temperature_range": "18-26°C",
        "ideal_humidity_range": "50-70%",
        "watering_frequency_days": 5,
        "last_watered": "2026-09-24",
        "care_notes": "Leaves droop visibly when thirsty. Keep soil consistently moist."
    },
    {
        "plant_id": "fiddle-leaf-fig",
        "common_name": "Fiddle Leaf Fig",
        "scientific_name": "Ficus lyrata",
        "species": "Moraceae",
        "zone": "Zone A - Bright Sun Corridor",
        "health_status": "Healthy",
        "ideal_temperature_range": "18-25°C",
        "ideal_humidity_range": "50-65%",
        "watering_frequency_days": 8,
        "last_watered": "2026-09-20",
        "care_notes": "Sensitive to cold drafts and sudden changes in position."
    },
    {
        "plant_id": "golden-pothos",
        "common_name": "Golden Pothos Vine",
        "scientific_name": "Epipremnum aureum",
        "species": "Araceae",
        "zone": "Zone D - Propagation Bench",
        "health_status": "Healthy",
        "ideal_temperature_range": "15-28°C",
        "ideal_humidity_range": "40-70%",
        "watering_frequency_days": 7,
        "last_watered": "2026-09-22",
        "care_notes": "Fast growing trailing vine; easy to propagate in water cuttings."
    }
]

def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    
    for collection_name in ["greenhouse_plants", "plants"]:
        plants_ref = db.collection(collection_name)
        for plant in INITIAL_PLANTS:
            plant_doc = dict(plant)
            plants_ref.document(plant_doc["plant_id"]).set(plant_doc)
            print(f"✓ Seeded [{collection_name}] {plant_doc['common_name']} ({plant_doc['plant_id']})")
            
    print("Firestore database successfully seeded!")

if __name__ == "__main__":
    seed_database()
