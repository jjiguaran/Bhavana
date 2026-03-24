#!/usr/bin/env python3
"""
Script to update meditations.json when new audio files are added
Configured for Cloudflare R2 storage
"""

import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cloudflare R2 configuration from environment
R2_BUCKET_URL = os.getenv("R2_BUCKET_URL")
USE_CLOUDFLARE_R2 = True  # Set to False to use local files

def scan_audio_files(data_dir="public/data"):
    """Scan for meditation audio files and extract metadata"""
    meditations = []
    audio_path = Path(data_dir)
    
    # Pattern to match meditation files
    pattern_music = re.compile(r"meditacion_kokoro_(\d+)_(\w+)_con_musica\.wav")
    pattern_mute = re.compile(r"meditacion_kokoro_(\d+)_(\w+)_mute\.wav")
    
    for file_path in audio_path.glob("*.wav"):
        if file_path.name.startswith("meditacion_kokoro_test"):
            continue
            
        # Try music pattern first
        match = pattern_music.match(file_path.name)
        if match:
            minutes, level = match.groups()
            music = True
        else:
            match = pattern_mute.match(file_path.name)
            if match:
                minutes, level = match.groups()
                music = False
            else:
                continue
        
        # Use Cloudflare R2 URL if enabled, otherwise local path
        if USE_CLOUDFLARE_R2:
            file_url = f"{R2_BUCKET_URL}/{file_path.name}"
        else:
            file_url = f"/data/{file_path.name}"
        
        meditations.append({
            "minutes": int(minutes),
            "level": level,
            "music": music,
            "filename": file_path.name,
            "url": file_url,
            "display_name": f"{minutes}min - {level.title()} - {'Con Música' if music else 'Sin Música'}"
        })
    
    return sorted(meditations, key=lambda x: (x["minutes"], x["level"], x["music"]))

def update_json_file():
    """Update meditations.json file with current audio files"""
    meditations = scan_audio_files()
    
    json_path = Path("public/data/meditations.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(meditations, f, indent=2, ensure_ascii=False)
    
    storage_type = "Cloudflare R2" if USE_CLOUDFLARE_R2 else "Local"
    print(f"Updated {json_path} with {len(meditations)} meditations ({storage_type}):")
    for med in meditations:
        print(f"  - {med['display_name']}")

if __name__ == "__main__":
    update_json_file()
