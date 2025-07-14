from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from generate_meditation import generate_meditation
from fastapi.middleware.cors import CORSMiddleware

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