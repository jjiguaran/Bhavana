import os
import re
from typing import List, Dict, Set, Tuple
from pathlib import Path

def get_available_meditations(audio_dir: str = "../data/audio") -> List[Dict[str, any]]:
    """
    Scan the audio directory and return all available meditation combinations.
    
    Returns:
        List of dictionaries containing meditation parameters and file paths
    """
    meditations = []
    audio_path = Path(audio_dir)
    
    if not audio_path.exists():
        print(f"Audio directory not found: {audio_dir}")
        return meditations
    
    # Pattern to match meditation files: meditacion_kokoro_{minutes}_{level}_{music_type}.wav
    pattern = re.compile(r"meditacion_kokoro_(\d+)_(\w+)_con_musica\.wav")
    pattern_mute = re.compile(r"meditacion_kokoro_(\d+)_(\w+)_mute\.wav")
    
    for file_path in audio_path.glob("*.wav"):
        match = pattern.match(file_path.name)
        if match:
            minutes, level = match.groups()
            music_type = "con_musica"
            
            meditations.append({
                "minutes": int(minutes),
                "level": level,
                "music": True,
                "music_type": music_type,
                "filename": file_path.name,
                "filepath": str(file_path)
            })
            continue
            
        match_mute = pattern_mute.match(file_path.name)
        if match_mute:
            minutes, level = match_mute.groups()
            music_type = "mute"
            
            meditations.append({
                "minutes": int(minutes),
                "level": level,
                "music": False,
                "music_type": music_type,
                "filename": file_path.name,
                "filepath": str(file_path)
            })
    
    return sorted(meditations, key=lambda x: (x["minutes"], x["level"], x["music"]))

def get_unique_combinations(audio_dir: str = "../data/audio") -> Dict[str, Set]:
    """
    Get unique values for each parameter from available meditations.
    
    Returns:
        Dictionary with sets of unique values for minutes, levels, and music options
    """
    meditations = get_available_meditations(audio_dir)
    
    combinations = {
        "minutes": set(),
        "levels": set(),
        "music_options": set()
    }
    
    for meditation in meditations:
        combinations["minutes"].add(meditation["minutes"])
        combinations["levels"].add(meditation["level"])
        combinations["music_options"].add(meditation["music"])
    
    return combinations

def get_available_combinations(audio_dir: str = "../data/audio") -> List[Dict[str, any]]:
    """
    Get all unique combinations of parameters that have audio files available.
    This is what the UI should use to show available options.
    
    Returns:
        List of unique parameter combinations
    """
    meditations = get_available_meditations(audio_dir)
    
    # Create unique combinations
    seen = set()
    combinations = []
    
    for meditation in meditations:
        key = (meditation["minutes"], meditation["level"], meditation["music"])
        if key not in seen:
            seen.add(key)
            combinations.append({
                "minutes": meditation["minutes"],
                "level": meditation["level"],
                "music": meditation["music"],
                "display_name": f"{meditation['minutes']}min - {meditation['level'].title()} - {'Con Música' if meditation['music'] else 'Sin Música'}"
            })
    
    return sorted(combinations, key=lambda x: (x["minutes"], x["level"], x["music"]))

def find_meditation_file(minutes: int, level: str, music: bool, audio_dir: str = "../data/audio") -> str:
    """
    Find the audio file path for a specific meditation combination.
    
    Args:
        minutes: Duration in minutes
        level: Meditation level (principiante, intermedio, avanzado)
        music: Whether to include music
        audio_dir: Directory containing audio files
    
    Returns:
        Full path to the audio file, or None if not found
    """
    music_type = "con_musica" if music else "mute"
    expected_filename = f"meditacion_kokoro_{minutes}_{level}_{music_type}.wav"
    
    audio_path = Path(audio_dir) / expected_filename
    return str(audio_path) if audio_path.exists() else None

def get_meditation_stats(audio_dir: str = "../data/audio") -> Dict[str, any]:
    """
    Get statistics about available meditations.
    
    Returns:
        Dictionary with meditation statistics
    """
    meditations = get_available_meditations(audio_dir)
    combinations = get_unique_combinations(audio_dir)
    
    return {
        "total_files": len(meditations),
        "unique_combinations": len(get_available_combinations(audio_dir)),
        "available_minutes": sorted(list(combinations["minutes"])),
        "available_levels": sorted(list(combinations["levels"])),
        "available_music_options": sorted(list(combinations["music_options"]))
    }

# Example usage and testing
if __name__ == "__main__":
    print("Available meditations:")
    for meditation in get_available_meditations():
        print(f"  {meditation}")
    
    print("\nUnique combinations:")
    for combo in get_available_combinations():
        print(f"  {combo}")
    
    print("\nStatistics:")
    stats = get_meditation_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")