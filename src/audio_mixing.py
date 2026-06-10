"""
Script to batch-generate meditation audio variations by mixing background sounds
(binaural solfeggio or nature sounds) into existing silence meditations.

The workflow:
1. Read meditations/meditations_repo_log.json from R2
2. Find all silence entries that don't yet have a counterpart for the chosen mode
3. For each missing meditation, download the silence audio, mix with the chosen
   background, and upload to meditations/{mode}/
4. Update the meditations log with new entries

Usage:
    python src/audio_mixing.py --mode binaural
    python src/audio_mixing.py --mode nature
    
    Optional arguments:
    --mode              'binaural' or 'nature' (default: binaural)
    --solfeggio-key     R2 key for the solfeggio background (default: sounds/solfeggio-mix-285-528-852-hz.mp3)
    --nature-key        R2 key for the nature background (default: sounds/soundreality-stream-nature-445380.mp3)
    --gong-key          R2 key for the gong sound (default: sounds/freesound_community-gong-79191.mp3)
    --background-volume Volume level for background (0.0-1.0, default: 0.05)
    --fade-duration     Fade in/out duration in seconds (default: 3.0)
"""

import os
import json
import io
import argparse
import re
import math
import numpy as np
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
from pydub import AudioSegment

# Load environment variables from .env file
load_dotenv()


def connect_to_r2():
    """Create S3 client for Cloudflare R2 using environment variables"""
    return boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name='auto'
    )


def download_from_r2(r2_client, bucket_name, file_key, local_path="/tmp/"):
    """Download a file from R2 to local storage
    
    Returns:
        str: Local file path on success, or None if the file doesn't exist or download fails.
    """
    filename = file_key.split('/')[-1]
    local_file_path = f"{local_path}{filename}"
    print(f"  Downloading {file_key}...")
    try:
        r2_client.download_file(Bucket=bucket_name, Key=file_key, Filename=local_file_path)
        print(f"  ✅ Saved to {local_file_path}")
        return local_file_path
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == '404' or 'Not Found' in str(e):
            print(f"  ⚠️ File not found in R2: {file_key}")
        else:
            print(f"  ❌ Error downloading {file_key}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Error downloading {file_key}: {e}")
        return None


def upload_bytes_to_r2(r2_client, bucket_name, data_bytes, r2_key):
    """Upload bytes to R2 directly (no local file)."""
    print(f"  Uploading to {r2_key}...")
    r2_client.put_object(Bucket=bucket_name, Key=r2_key, Body=data_bytes)
    print(f"  ✅ Uploaded: {r2_key}")


def read_json_from_r2(r2_client, bucket_name, file_key):
    """Read JSON file from R2"""
    try:
        response = r2_client.get_object(Bucket=bucket_name, Key=file_key)
        json_content = response['Body'].read().decode('utf-8')
        return json.loads(json_content)
    except Exception as e:
        print(f"  ❌ Error reading JSON from R2: {e}")
        return None


def read_json_or_default(r2_client, bucket_name, file_key, default_structure):
    """Read JSON from R2, returning default structure if file doesn't exist."""
    data = read_json_from_r2(r2_client, bucket_name, file_key)
    if data is None:
        return default_structure
    return data


def upload_json_to_r2(r2_client, bucket_name, file_key, data):
    """Upload a dictionary as JSON to R2"""
    try:
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        r2_client.put_object(Bucket=bucket_name, Key=file_key, Body=json_bytes)
        print(f"  ✅ Updated log: {file_key}")
        return True
    except Exception as e:
        print(f"  ❌ Error uploading JSON to R2: {e}")
        return False


def build_audio_key(entry, subdirectory="silence"):
    """Build the R2 key for a meditation audio file from a log entry.
    
    E.g. duration='5 min', level='principiante', variation=1 
         → 'meditations/silence/5_principiante_1.opus'
    
    Args:
        entry: dict with 'duration', 'level', 'variation' keys
        subdirectory: 'silence', 'binaural', or 'nature'
    """
    duration_str = entry.get('duration', '')
    match = re.match(r'(\d+)', duration_str)
    minutes = match.group(1) if match else '0'
    level = entry.get('level', 'unknown')
    variation = entry.get('variation', 1)
    return f"meditations/{subdirectory}/{minutes}_{level}_{variation}.opus"


def mix_solfeggio_with_meditation(r2, bucket_name, meditation_key, solfeggio_key, gong_key,
                                   background_volume=0.05, fade_duration=3.0, target_sr=44100):
    """Download audio files, mix solfeggio background into meditation, return mixed AudioSegment.
    
    The solfeggio background plays only in the middle section between the opening/closing gongs.
    
    Args:
        r2: R2 client
        bucket_name: R2 bucket name
        meditation_key: R2 key for the silence meditation audio
        solfeggio_key: R2 key for the solfeggio background
        gong_key: R2 key for the gong sound
        background_volume: volume level for background (0.0-1.0)
        fade_duration: fade in/out duration in seconds
        target_sr: target sample rate
        
    Returns:
        AudioSegment with mixed audio, or None on error
    """
    print("\n📥 Downloading audio files from R2...")
    
    meditation_path = download_from_r2(r2, bucket_name, meditation_key)
    if meditation_path is None:
        print(f"  ❌ Cannot proceed: meditation file not found ({meditation_key})")
        return None

    solfeggio_path = download_from_r2(r2, bucket_name, solfeggio_key)
    if solfeggio_path is None:
        print(f"  ❌ Cannot proceed: solfeggio file not found ({solfeggio_key})")
        return None

    gong_path = download_from_r2(r2, bucket_name, gong_key)
    if gong_path is None:
        print(f"  ❌ Cannot proceed: gong file not found ({gong_key})")
        return None

    # ── Load audio files ────────────────────────────────────────────────
    print("\n🔊 Loading audio files...")
    meditation = AudioSegment.from_file(meditation_path).set_frame_rate(target_sr).set_channels(2)
    solfeggio = AudioSegment.from_file(solfeggio_path).set_frame_rate(target_sr).set_channels(2)
    gong = AudioSegment.from_file(gong_path).set_frame_rate(target_sr).set_channels(2)

    # ── Compute durations ──────────────────────────────────────────────
    gong_duration_ms = len(gong)
    gong_duration_s = gong_duration_ms / 1000.0
    meditation_duration_ms = len(meditation)
    meditation_duration_s = meditation_duration_ms / 1000.0
    solfeggio_duration_s = len(solfeggio) / 1000.0

    print(f"\n📊 Durations:")
    print(f"  Gong sound:          {gong_duration_s:.2f} s")
    print(f"  Original meditation: {meditation_duration_s:.2f} s")
    print(f"  Solfeggio track:     {solfeggio_duration_s:.2f} s")

    # Validate that the meditation is long enough to contain two gongs
    if meditation_duration_ms <= 2 * gong_duration_ms:
        print(f"  ❌ Meditation ({meditation_duration_s:.1f}s) is shorter than "
              f"2× gong duration ({2 * gong_duration_s:.1f}s). Skipping.")
        return None

    # The background should play during the middle section only
    background_duration_ms = meditation_duration_ms - 2 * gong_duration_ms
    background_duration_s = background_duration_ms / 1000.0
    print(f"  Background section: {background_duration_s:.2f} s "
          f"(meditation minus 2× gong)")

    # ── Prepare the background track ────────────────────────────────────
    print("\n🎛️  Preparing solfeggio background...")

    # Loop or trim the solfeggio to match the exact background duration
    if len(solfeggio) >= background_duration_ms:
        background = solfeggio[:background_duration_ms]
        print(f"  Trimmed solfeggio to {background_duration_s:.1f}s")
    else:
        repeats = int(np.ceil(background_duration_ms / len(solfeggio)))
        background = solfeggio * repeats
        background = background[:background_duration_ms]
        print(f"  Looped solfeggio {repeats}x to fill {background_duration_s:.1f}s")

    # Apply fade in and fade out to avoid abrupt transitions
    fade_ms = int(fade_duration * 1000)
    if fade_ms > 0:
        background = background.fade_in(fade_ms).fade_out(fade_ms)
        print(f"  Applied {fade_duration}s fade in/out")

    # Reduce background volume relative to the original meditation
    if background_volume < 1.0:
        gain_db = 20 * math.log10(background_volume)
        background = background.apply_gain(gain_db)
        print(f"  Background volume adjusted to {background_volume:.0%} "
              f"(gain: {gain_db:+.1f} dB)")

    # ── Position the background ─────────────────────────────────────────
    print("\n🔄 Mixing audio tracks...")

    # Create leading and trailing silence for the gong sections
    silence_before = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)
    silence_after = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)

    # Build the full background track with silence where gongs play
    full_background = silence_before + background + silence_after

    # Ensure the background track matches the meditation duration exactly
    if len(full_background) > meditation_duration_ms:
        full_background = full_background[:meditation_duration_ms]
    elif len(full_background) < meditation_duration_ms:
        pad_ms = meditation_duration_ms - len(full_background)
        full_background = full_background + AudioSegment.silent(duration=pad_ms, frame_rate=target_sr)

    # Mix: overlay the background onto the original meditation
    mixed_audio = meditation.overlay(full_background)
    
    return mixed_audio


def mix_nature_with_meditation(r2, bucket_name, meditation_key, nature_key, gong_key,
                                background_volume=0.05, fade_duration=3.0, target_sr=44100):
    """Download audio files, mix nature background into meditation, return mixed AudioSegment.
    
    The nature background plays only in the middle section between the opening/closing gongs,
    respecting the same gong structure as the binaural version. The gong audio is already
    part of the original silence meditation, so only its duration is used for gating.
    
    Args:
        r2: R2 client
        bucket_name: R2 bucket name
        meditation_key: R2 key for the silence meditation audio
        nature_key: R2 key for the nature background sound
        gong_key: R2 key for the gong sound (used only for duration measurement)
        background_volume: volume level for background (0.0-1.0)
        fade_duration: fade in/out duration in seconds
        target_sr: target sample rate
        
    Returns:
        AudioSegment with mixed audio, or None on error
    """
    print("\n📥 Downloading audio files from R2...")
    
    meditation_path = download_from_r2(r2, bucket_name, meditation_key)
    if meditation_path is None:
        print(f"  ❌ Cannot proceed: meditation file not found ({meditation_key})")
        return None

    nature_path = download_from_r2(r2, bucket_name, nature_key)
    if nature_path is None:
        print(f"  ❌ Cannot proceed: nature file not found ({nature_key})")
        return None

    gong_path = download_from_r2(r2, bucket_name, gong_key)
    if gong_path is None:
        print(f"  ❌ Cannot proceed: gong file not found ({gong_key})")
        return None

    # ── Load audio files ────────────────────────────────────────────────
    print("\n🔊 Loading audio files...")
    meditation = AudioSegment.from_file(meditation_path).set_frame_rate(target_sr).set_channels(2)
    nature = AudioSegment.from_file(nature_path).set_frame_rate(target_sr).set_channels(2)
    gong = AudioSegment.from_file(gong_path).set_frame_rate(target_sr).set_channels(2)

    # ── Compute durations ──────────────────────────────────────────────
    gong_duration_ms = len(gong)
    gong_duration_s = gong_duration_ms / 1000.0
    meditation_duration_ms = len(meditation)
    meditation_duration_s = meditation_duration_ms / 1000.0
    nature_duration_s = len(nature) / 1000.0

    print(f"\n📊 Durations:")
    print(f"  Gong sound:          {gong_duration_s:.2f} s")
    print(f"  Original meditation: {meditation_duration_s:.2f} s")
    print(f"  Nature track:        {nature_duration_s:.2f} s")

    # Validate that the meditation is long enough to contain two gongs
    if meditation_duration_ms <= 2 * gong_duration_ms:
        print(f"  ❌ Meditation ({meditation_duration_s:.1f}s) is shorter than "
              f"2× gong duration ({2 * gong_duration_s:.1f}s). Skipping.")
        return None

    # The background should play during the middle section only
    background_duration_ms = meditation_duration_ms - 2 * gong_duration_ms
    background_duration_s = background_duration_ms / 1000.0
    print(f"  Background section: {background_duration_s:.2f} s "
          f"(meditation minus 2× gong)")

    # ── Prepare the background track ────────────────────────────────────
    print("\n🎛️  Preparing nature background...")

    # Loop or trim the nature track to match the exact background duration
    if len(nature) >= background_duration_ms:
        background = nature[:background_duration_ms]
        print(f"  Trimmed nature track to {background_duration_s:.1f}s")
    else:
        repeats = int(np.ceil(background_duration_ms / len(nature)))
        background = nature * repeats
        background = background[:background_duration_ms]
        print(f"  Looped nature track {repeats}x to fill {background_duration_s:.1f}s")

    # Apply fade in and fade out to avoid abrupt transitions
    fade_ms = int(fade_duration * 1000)
    if fade_ms > 0:
        background = background.fade_in(fade_ms).fade_out(fade_ms)
        print(f"  Applied {fade_duration}s fade in/out")

    # Reduce background volume relative to the original meditation
    if background_volume < 1.0:
        gain_db = 20 * math.log10(background_volume)
        background = background.apply_gain(gain_db)
        print(f"  Background volume adjusted to {background_volume:.0%} "
              f"(gain: {gain_db:+.1f} dB)")

    # ── Position the background ─────────────────────────────────────────
    print("\n🔄 Mixing audio tracks...")

    # Create leading and trailing silence for the gong sections
    silence_before = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)
    silence_after = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)

    # Build the full background track with silence where gongs play
    full_background = silence_before + background + silence_after

    # Ensure the background track matches the meditation duration exactly
    if len(full_background) > meditation_duration_ms:
        full_background = full_background[:meditation_duration_ms]
    elif len(full_background) < meditation_duration_ms:
        pad_ms = meditation_duration_ms - len(full_background)
        full_background = full_background + AudioSegment.silent(duration=pad_ms, frame_rate=target_sr)

    # Mix: overlay the background onto the original meditation
    mixed_audio = meditation.overlay(full_background)
    
    return mixed_audio


def main():
    parser = argparse.ArgumentParser(
        description='Batch-generate meditation variations (binaural or nature) by mixing '
                    'background sounds into all silence meditations that lack the target version.'
    )
    parser.add_argument(
        '--mode', type=str, choices=['binaural', 'nature'], default='binaural',
        help='Generation mode: "binaural" mixes solfeggio between gongs, '
             '"nature" mixes nature sounds throughout (default: binaural)'
    )
    parser.add_argument(
        '--solfeggio-key', type=str,
        default='sounds/solfeggio-mix-285-528-852-hz.mp3',
        help='R2 key for the solfeggio background sound (default: sounds/solfeggio-mix-285-528-852-hz.mp3)'
    )
    parser.add_argument(
        '--nature-key', type=str,
        default='sounds/soundreality-stream-nature-445380.mp3',
        help='R2 key for the nature background sound (default: sounds/soundreality-stream-nature-445380.mp3)'
    )
    parser.add_argument(
        '--gong-key', type=str,
        default='sounds/freesound_community-gong-79191.mp3',
        help='R2 key for the gong sound file (default: sounds/freesound_community-gong-79191.mp3)'
    )
    parser.add_argument(
        '--background-volume', type=float,
        help='Volume level for the background relative to original (0.0-1.0). '
             'Defaults to 0.05 for binaural, 0.025 for nature.'
    )
    parser.add_argument(
        '--fade-duration', type=float, default=3.0,
        help='Fade in/out duration for the background in seconds (default: 3.0)'
    )
    parser.add_argument(
        '--target-subdirectory', type=str,
        help='Override the target subdirectory (defaults to the mode name, e.g. "binaural" or "nature")'
    )
    args = parser.parse_args()

    mode = args.mode
    target_subdirectory = args.target_subdirectory if args.target_subdirectory else mode

    # Set background volume default based on mode (nature at half of binaural)
    if args.background_volume is not None:
        background_volume = args.background_volume
    else:
        background_volume = 0.05 if mode == 'binaural' else 0.025

    MODE_LABELS = {
        'binaural': ('binaural', '🎵 Batch Binaural Meditation Generator'),
        'nature': ('nature', '🌿 Batch Nature Background Meditation Generator'),
    }

    music_label, title = MODE_LABELS[mode]

    print("=" * 60)
    print(title)
    print("=" * 60)

    # ── Validate credentials ────────────────────────────────────────────
    required_env_vars = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME']
    missing = [v for v in required_env_vars if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please ensure they are defined in your .env file."
        )

    bucket_name = os.getenv('R2_BUCKET_NAME')

    # ── Connect to R2 ──────────────────────────────────────────────────
    print("\n🔗 Connecting to Cloudflare R2...")
    r2 = connect_to_r2()
    # Verify connection
    r2.head_bucket(Bucket=bucket_name)
    print("✅ Connection successful")

    # ── Read the meditations log ────────────────────────────────────────
    print("\n📋 Reading meditations repo log from R2...")
    meditations_log = read_json_or_default(
        r2, bucket_name,
        "meditations/meditations_repo_log.json",
        {"meditations": []}
    )
    all_entries = meditations_log.get("meditations", [])
    print(f"   Found {len(all_entries)} meditation entrie(s) in the log.")

    # ── Separate silence entries from target-mode entries ───────────────
    silence_entries = [e for e in all_entries if e.get('music') == 'silence']
    target_entries = [e for e in all_entries if e.get('music') == music_label]

    print(f"\n   Silence meditations:    {len(silence_entries)}")
    print(f"   {music_label.capitalize()} meditations:   {len(target_entries)}")

    # Build a set of (duration, level, variation) tuples already in the target mode
    target_set = set()
    for e in target_entries:
        target_set.add((
            e.get('duration'),
            e.get('level'),
            e.get('variation')
        ))

    # ── Find silence entries that need a target-mode version ────────────
    missing = []
    for entry in silence_entries:
        key = (entry.get('duration'), entry.get('level'), entry.get('variation'))
        if key not in target_set:
            missing.append(entry)

    print(f"\n🎯 Found {len(missing)} meditation(s) that need {mode} versions:")

    if not missing:
        print(f"\n✅ All silence meditations already have a {mode} version. Nothing to do.")
        return

    for m in missing:
        silence_key = build_audio_key(m, "silence")
        target_key = build_audio_key(m, target_subdirectory)
        print(f"   - {m.get('duration')} | {m.get('level')} | variation {m.get('variation')}")
        print(f"     📥 {silence_key}")
        print(f"     📤 {target_key}")

    # ── Process each missing meditation ─────────────────────────────────
    target_sr = 44100
    success_count = 0

    for i, entry in enumerate(missing, 1):
        duration_str = entry.get('duration', '')
        level = entry.get('level', 'unknown')
        variation = entry.get('variation', 1)

        silence_key = build_audio_key(entry, "silence")
        target_key = build_audio_key(entry, target_subdirectory)

        print(f"\n{'='*60}")
        print(f"[{i}/{len(missing)}] Generating {mode}: {duration_str} | {level} | variation {variation}")
        print(f"   Source: {silence_key}")
        print(f"   Target: {target_key}")

        # ── Mix background into meditation ──────────────────────────────
        if mode == 'binaural':
            mixed_audio = mix_solfeggio_with_meditation(
                r2, bucket_name,
                meditation_key=silence_key,
                solfeggio_key=args.solfeggio_key,
                gong_key=args.gong_key,
                background_volume=background_volume,
                fade_duration=args.fade_duration,
                target_sr=target_sr
            )
        else:  # mode == 'nature'
            mixed_audio = mix_nature_with_meditation(
                r2, bucket_name,
                meditation_key=silence_key,
                nature_key=args.nature_key,
                gong_key=args.gong_key,
                background_volume=background_volume,
                fade_duration=args.fade_duration,
                target_sr=target_sr
            )

        if mixed_audio is None:
            print(f"   ⚠️ Skipping {silence_key} due to processing error.")
            continue

        # ── Export to memory and upload to R2 ───────────────────────────
        print("\n💾 Exporting mixed audio to memory...")
        buf = io.BytesIO()
        mixed_audio.export(buf, format="opus")
        opus_bytes = buf.getvalue()
        buf.close()

        mixed_duration_s = len(mixed_audio) / 1000.0
        print(f"  ⏱️  Mixed audio duration: {mixed_duration_s:.2f} s")

        print("\n☁️  Uploading to Cloudflare R2...")
        upload_bytes_to_r2(r2, bucket_name, opus_bytes, target_key)

        # ── Update meditations log ──────────────────────────────────────
        new_entry = {
            "duration": duration_str,
            "level": level,
            "variation": variation,
            "model": entry.get('model', 'unknown'),
            "date_generated": date.today().strftime("%Y-%m-%d"),
            "music": music_label
        }
        meditations_log["meditations"].append(new_entry)
        upload_json_to_r2(
            r2, bucket_name,
            "meditations/meditations_repo_log.json",
            meditations_log
        )
        print(f"   🎉 Complete: {target_key}")
        success_count += 1

    # ── Update local copy of the log ────────────────────────────────────
    local_log_path = Path(__file__).resolve().parent.parent / "web-ui" / "public" / "meditations_repo_log.json"
    try:
        with open(local_log_path, 'w', encoding='utf-8') as f:
            json.dump(meditations_log, f, indent=2, ensure_ascii=False)
        print(f"\n  ✅ Local log updated: {local_log_path}")
    except Exception as e:
        print(f"\n  ⚠️ Could not update local log at {local_log_path}: {e}")

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"✅ Batch complete! Generated {success_count} new {mode} meditation(s).")
    print("=" * 60)


if __name__ == "__main__":
    main()