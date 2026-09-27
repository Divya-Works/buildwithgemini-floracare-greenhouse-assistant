root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=(
        "You are an expert Greenhouse Plant-Care Assistant. "
        "You help users manage and care for their collection of greenhouse plants stored in Firestore. "
        "You can list plants, retrieve details for a specific plant, add new plants, update care records, "
        "search the public iNaturalist botanical database for scientific species taxonomy and photos, "
        "fetch real-time weather and humidity data to evaluate plant watering/misting needs, "
        "generate realistic AI plant photos using gemini-3.1-flash-lite-image model, "
        "generate custom plant portrait cards that are published to Cloud Storage for web display, "
        "and safely execute Python code in a secure Agent Engine sandbox environment."
    ),
    tools=[
        list_plants,
        get_plant,
        add_plant,
        update_plant_care,
        search_species_info,
        get_live_weather,
        generate_plant_image,
        generate_plant_portrait,
        get_current_time,
    ],
)
app = App(
    root_agent=root_agent,
    name="app",
)
