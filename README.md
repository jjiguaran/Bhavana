# Bhavana

A meditation app that generates meditation scripts and audio using AI. All generated files are stored in Cloudflare R2.

## Project Structure

### Meditation Script Generation
- **`src/generate_scripts.py`** — Generates meditation scripts using an AI model. These scripts are the textual content of the meditations.

### Meditation Audio Generation
- **`notebooks/generate_audio.ipynb`** — Jupyter notebook that generates the spoken meditation audio from the scripts using text-to-speech.

### Audio Mixing (Background Sounds)
- **`src/audio_mixing.py`** — Adds ambient background sounds (e.g., nature, rain, white noise) to the generated meditation audio, producing the final mixed meditation audio files.

### Frontend
- **`web-ui/`** — A React-based static website that serves as the frontend of the meditation app. Users can browse and play the generated meditations.

### Storage
- All generated files (meditation scripts, audio files, and mixed audio) are saved to **Cloudflare R2** object storage.

## Tech Stack
- **Backend:** Python (script generation, audio mixing)
- **Frontend:** React (static site in `web-ui/`)
- **Storage:** Cloudflare R2
- **AI Models:** Ollama (for script generation), Text-to-Speech (for audio generation)