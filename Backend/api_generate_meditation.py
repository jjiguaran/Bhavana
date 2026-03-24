from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from generate_meditation import generate_meditation
from fastapi.middleware.cors import CORSMiddleware
from provide_meditation import get_available_combinations, find_meditation_file, get_meditation_stats

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MeditationRequest(BaseModel):
    minutes: int
    nivel: str
    musica: bool
    path_binaural: str

@app.post("/generate")
def generate_meditation_endpoint(req: MeditationRequest):
    output_path = generate_meditation(
        req.minutes,
        req.nivel,
        req.musica,
        req.path_binaural
    )
    # Return the generated audio file
    return FileResponse(output_path, media_type="audio/wav", filename=output_path.split("/")[-1])

@app.get("/available-meditations")
def get_available_meditations_endpoint():
    """Get all available meditation combinations for the UI"""
    return {
        "success": True,
        "data": get_available_combinations()
    }

@app.get("/meditation-stats")
def get_meditation_stats_endpoint():
    """Get statistics about available meditations"""
    return {
        "success": True,
        "data": get_meditation_stats()
    }

@app.post("/get-meditation")
def get_existing_meditation_endpoint(req: MeditationRequest):
    """Get an existing meditation file if available, otherwise generate new one"""
    existing_file = find_meditation_file(req.minutes, req.nivel, req.musica)
    
    if existing_file:
        # Return existing file
        return FileResponse(existing_file, media_type="audio/wav", filename=existing_file.split("/")[-1])
    else:
        # Generate new meditation (existing logic)
        output_path = generate_meditation(
            req.minutes,
            req.nivel,
            req.musica,
            req.path_binaural
        )
        return FileResponse(output_path, media_type="audio/wav", filename=output_path.split("/")[-1])