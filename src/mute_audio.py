#!/usr/bin/env python3
"""
Script to generate unguided meditation audio files — gong + [middle section] + gong,
without any voice instructions.

The script generates three modes:
  - silence:  gong + comfort noise + gong
  - binaural: gong + solfeggio background + gong
  - nature:   gong + nature background + gong

All files are stored in the same directory, distinguished by mode in the filename:
  meditations/mute/5_silence.opus
  meditations/mute/5_binaural.opus
  meditations/mute/5_nature.opus
  ...

Workflow:
  1. Read meditations/meditations_repo_log.json from R2
  2. For each mode, check which durations already exist (guided=False + matching music)
  3. For each missing duration, download the gong (and background if needed),
     generate the audio, upload it, and update the log

Usage:
    # Generate all modes
    python src/mute_audio.py

    # Generate only specific modes
    python src/mute_audio.py --modes silence,binaural

    # Preview
    python src/mute_audio.py --dry-run

    # Custom durations
    python src/mute_audio.py --durations 5,10,15
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


# ── Constants ──────────────────────────────────────────────────────────────────
SILENCE_COMFORT_NOISE_LEVEL = 0.00005  # microscopic Gaussian noise floor
TARGET_SR = 44100                     # output sample rate
TARGET_CHANNELS = 2                   # stereo output

DEFAULT_DURATIONS_MINUTES = [5, 10, 15, 20, 30, 45, 60]

# All files go to meditations/mute/ regardless of background type
OUTPUT_SUBDIRECTORY = "mute"

# Mode configuration: (background_r2_key, default_volume, music_label)
MODE_CONFIG = {
    "silence": {
        "background_key": None,
        "background_volume": None,
        "music_label": "silence",
    },
    "binaural": {
        "background_key": "sounds/solfeggio-mix-285-528-852-hz.mp3",
        "background_volume": 0.05,
        "music_label": "binaural",
    },
    "nature": {
        "background_key": "sounds/soundreality-stream-nature-445380.mp3",
        "background_volume": 0.025,
        "music_label": "nature",
    },
}


# ── R2 Helpers ─────────────────────────────────────────────────────────────────
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
    """Download a file from R2 to local storage.

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
    try:
        r2_client.put_object(Bucket=bucket_name, Key=r2_key, Body=data_bytes)
        print(f"  ✅ Uploaded: {r2_key}")
        return True
    except Exception as e:
        print(f"  ❌ Error uploading {r2_key}: {e}")
        return False


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
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        r2_client.put_object(Bucket=bucket_name, Key=file_key, Body=json_bytes)
        print(f"  ✅ Updated log: {file_key}")
        return True
    except Exception as e:
        print(f"  ❌ Error uploading JSON to R2: {e}")
        return False


# ── Audio Generation ───────────────────────────────────────────────────────────
def generate_mute_audio(
    gong_path,
    target_duration_seconds,
    target_sr=TARGET_SR,
    channels=TARGET_CHANNELS,
    background_path=None,
    background_volume=0.05,
    fade_duration=3.0,
):
    """Generate a mute meditation audio: gong + [middle section] + gong.

    The middle section is either comfort noise (if no background) or a background
    track (solfeggio/nature) looped/trimmed to fit, with volume adjustment.

    Args:
        gong_path: Local path to the gong sound file.
        target_duration_seconds: Total desired duration of the output audio in seconds.
        target_sr: Sample rate for the output.
        channels: Number of channels (1 or 2) for the output.
        background_path: Local path to a background audio file, or None for comfort noise.
        background_volume: Volume level for the background (0.0-1.0).
        fade_duration: Fade in/out duration for the background in seconds.

    Returns:
        AudioSegment containing the mute meditation, or None on error.
    """
    print(f"\n🔊 Loading gong sound from {gong_path}...")
    gong = AudioSegment.from_file(gong_path).set_frame_rate(target_sr).set_channels(channels)

    gong_duration_ms = len(gong)
    gong_duration_s = gong_duration_ms / 1000.0
    target_duration_ms = int(target_duration_seconds * 1000)

    print(f"  Gong duration:   {gong_duration_s:.2f} s")
    print(f"  Target duration: {target_duration_seconds:.0f} s")

    # Validate that the target duration is long enough to contain two gongs
    if target_duration_ms <= 2 * gong_duration_ms:
        print(f"  ❌ Target duration ({target_duration_seconds:.1f}s) is shorter than "
              f"2 × gong duration ({2 * gong_duration_s:.1f}s).")
        return None

    # Middle section duration
    middle_duration_ms = target_duration_ms - 2 * gong_duration_ms
    middle_duration_s = middle_duration_ms / 1000.0

    if background_path is not None:
        # ── Generate background-based middle section ────────────────────
        print(f"\n🎛️  Loading background from {background_path}...")
        background = AudioSegment.from_file(background_path).set_frame_rate(target_sr).set_channels(channels)

        background_duration_s = len(background) / 1000.0
        print(f"  Background track: {background_duration_s:.2f} s")
        print(f"  Middle section:   {middle_duration_s:.2f} s (background)")

        # Loop or trim the background to match the exact middle duration
        if len(background) >= middle_duration_ms:
            middle = background[:middle_duration_ms]
            print(f"  Trimmed background to {middle_duration_s:.1f}s")
        else:
            repeats = int(np.ceil(middle_duration_ms / len(background)))
            middle = background * repeats
            middle = middle[:middle_duration_ms]
            print(f"  Looped background {repeats}x to fill {middle_duration_s:.1f}s")

        # Apply fade in and fade out to avoid abrupt transitions
        fade_ms = int(fade_duration * 1000)
        if fade_ms > 0:
            middle = middle.fade_in(fade_ms).fade_out(fade_ms)
            print(f"  Applied {fade_duration}s fade in/out")

        # Reduce background volume
        if background_volume < 1.0:
            gain_db = 20 * math.log10(background_volume)
            middle = middle.apply_gain(gain_db)
            print(f"  Background volume adjusted to {background_volume:.0%} "
                  f"(gain: {gain_db:+.1f} dB)")
    else:
        # ── Generate comfort noise middle section ───────────────────────
        print(f"\n🎛️  Generating comfort noise section...")
        print(f"  Middle section:  {middle_duration_s:.2f} s (comfort noise)")

        num_noise_samples = int(target_sr * middle_duration_s)
        noise_array = np.random.normal(0, SILENCE_COMFORT_NOISE_LEVEL, num_noise_samples).astype(np.float32)

        if channels == 2:
            noise_stereo = np.column_stack([noise_array, noise_array])
            noise_bytes = (noise_stereo * 32768).astype(np.int16).tobytes()
        else:
            noise_bytes = (noise_array * 32768).astype(np.int16).tobytes()

        middle = AudioSegment(
            data=noise_bytes,
            frame_rate=target_sr,
            sample_width=2,
            channels=channels,
        )

        # Apply a very subtle fade in/out to avoid clicks
        fade_ms = min(500, middle_duration_ms // 4)
        if fade_ms > 0 and middle_duration_ms > 2 * fade_ms:
            middle = middle.fade_in(fade_ms).fade_out(fade_ms)
            print(f"  Applied {fade_ms}ms fade in/out to middle section")

    # Assemble: gong + middle + gong
    print(f"\n🔄 Assembling final audio...")
    final_audio = gong + middle + gong

    final_duration_s = len(final_audio) / 1000.0
    print(f"  Final duration:  {final_duration_s:.2f} s")

    return final_audio


def build_audio_key(minutes, mode):
    """Build the R2 key for a meditation audio file.

    All files go to meditations/mute/ regardless of mode.
    E.g. minutes=5, mode='silence' → 'meditations/mute/5_silence.opus'

    Args:
        minutes: Duration in minutes.
        mode: Mode string ('silence', 'binaural', 'nature').

    Returns:
        str: R2 key for the audio file.
    """
    return f"meditations/{OUTPUT_SUBDIRECTORY}/{minutes}_{mode}.opus"


def is_unguided_entry(entry, mode):
    """Check if a log entry is an unguided meditation of the given mode.

    An unguided entry has guided=False and music matching the mode's label.
    """
    music_label = MODE_CONFIG[mode]["music_label"]
    return (entry.get('guided') is False and entry.get('music') == music_label)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Generate unguided meditation audio files with optional background.'
    )
    parser.add_argument(
        '--gong-key', type=str,
        default='sounds/freesound_community-gong-79191.mp3',
        help='R2 key for the gong sound file (default: sounds/freesound_community-gong-79191.mp3)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='List what would be generated without uploading anything'
    )
    parser.add_argument(
        '--durations', type=str,
        default=','.join(str(d) for d in DEFAULT_DURATIONS_MINUTES),
        help=f'Comma-separated list of durations in minutes (default: {",".join(str(d) for d in DEFAULT_DURATIONS_MINUTES)})'
    )
    parser.add_argument(
        '--modes', type=str, default='silence,binaural,nature',
        help='Comma-separated list of modes to generate (default: silence,binaural,nature)'
    )
    args = parser.parse_args()

    # Parse durations
    try:
        durations_minutes = [int(d.strip()) for d in args.durations.split(',')]
    except ValueError:
        print(f"❌ Invalid --durations value: '{args.durations}'. Must be comma-separated integers.")
        return
    durations_minutes = sorted(set(durations_minutes))

    # Parse modes
    modes = [m.strip().lower() for m in args.modes.split(',')]
    invalid_modes = [m for m in modes if m not in MODE_CONFIG]
    if invalid_modes:
        print(f"❌ Invalid mode(s): {invalid_modes}. Valid modes: {list(MODE_CONFIG.keys())}")
        return
    modes = sorted(set(modes))  # deduplicate and sort

    print("=" * 60)
    print("🎧 Unguided Meditation Audio Generator")
    print(f"   Modes:     {', '.join(modes)}")
    print(f"   Durations: {', '.join(f'{d} min' for d in durations_minutes)}")
    print(f"   Output:    meditations/{OUTPUT_SUBDIRECTORY}/")
    print("=" * 60)

    # ── Validate credentials ────────────────────────────────────────────
    required_env_vars = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME']
    missing_vars = [v for v in required_env_vars if not os.getenv(v)]
    if missing_vars:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please ensure they are defined in your .env file."
        )

    bucket_name = os.getenv('R2_BUCKET_NAME')

    # ── Connect to R2 ──────────────────────────────────────────────────
    print("\n🔗 Connecting to Cloudflare R2...")
    r2 = connect_to_r2()
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

    # ── Download the gong sound once (shared across all modes) ──────────
    print(f"\n🔔 Downloading gong sound from '{args.gong_key}'...")
    gong_path = download_from_r2(r2, bucket_name, args.gong_key)
    if gong_path is None:
        print("  ❌ Cannot proceed: gong file not found.")
        return

    # ── Download background sounds (only if needed) ─────────────────────
    background_paths = {}
    for mode in modes:
        cfg = MODE_CONFIG[mode]
        if cfg["background_key"] is not None:
            print(f"\n🎵 Downloading {mode} background from '{cfg['background_key']}'...")
            bg_path = download_from_r2(r2, bucket_name, cfg["background_key"])
            if bg_path is None:
                print(f"  ❌ Cannot proceed: {mode} background file not found.")
                return
            background_paths[mode] = bg_path

    # ── Process each mode ───────────────────────────────────────────────
    overall_success = 0

    for mode in modes:
        cfg = MODE_CONFIG[mode]
        music_label = cfg["music_label"]

        print(f"\n{'='*60}")
        print(f"📀 Mode: {mode.upper()} → meditations/{OUTPUT_SUBDIRECTORY}/")
        print(f"{'='*60}")

        # Find which durations already have this mode's unguided entries
        existing_durations = set()
        for entry in all_entries:
            if is_unguided_entry(entry, mode):
                dur_str = entry.get('duration', '')
                match = re.match(r'(\d+)', dur_str)
                if match:
                    existing_durations.add(int(match.group(1)))

        if existing_durations:
            print(f"   Existing {mode} durations: {sorted(existing_durations)}")
        else:
            print(f"   No existing {mode} unguided entries found.")

        # Find missing durations
        missing = [d for d in durations_minutes if d not in existing_durations]

        print(f"\n🎯 Need to generate: {len(missing)} {mode} file(s)")
        for d in sorted(missing):
            print(f"   - {d}_{mode}.opus ({d} min)")

        if not missing:
            print(f"   ✅ All {mode} durations already exist. Skipping.")
            continue

        if args.dry_run:
            continue

        # Process each missing duration for this mode
        for i, minutes in enumerate(sorted(missing), 1):
            duration_str = f"{minutes} min"
            target_seconds = minutes * 60
            output_key = build_audio_key(minutes, mode)

            print(f"\n{'-'*60}")
            print(f"[{i}/{len(missing)}] Generating {mode}: {duration_str}")
            print(f"   Target: {target_seconds}s → {output_key}")

            # Generate audio
            final_audio = generate_mute_audio(
                gong_path=gong_path,
                target_duration_seconds=target_seconds,
                target_sr=TARGET_SR,
                channels=TARGET_CHANNELS,
                background_path=background_paths.get(mode),
                background_volume=cfg["background_volume"],
                fade_duration=3.0,
            )

            if final_audio is None:
                print(f"   ⚠️ Skipping {output_key} due to generation error.")
                continue

            # Export and upload
            print("\n💾 Exporting audio to memory...")
            buf = io.BytesIO()
            final_audio.export(buf, format="opus")
            opus_bytes = buf.getvalue()
            buf.close()

            final_duration_s = len(final_audio) / 1000.0
            print(f"  ⏱️  Final duration: {final_duration_s:.2f} s")

            print("\n☁️  Uploading to Cloudflare R2...")
            uploaded = upload_bytes_to_r2(r2, bucket_name, opus_bytes, output_key)

            if not uploaded:
                print(f"   ❌ Failed to upload {output_key}")
                continue

            # Update meditations log (both R2 and local copy in sync)
            new_entry = {
                "duration": duration_str,
                "level": None,
                "variation": None,
                "model": None,
                "date_generated": date.today().strftime("%Y-%m-%d"),
                "music": music_label,
                "guided": False,
            }
            meditations_log["meditations"].append(new_entry)
            upload_json_to_r2(
                r2, bucket_name,
                "meditations/meditations_repo_log.json",
                meditations_log
            )
            # Keep local copy in sync after each successful upload
            local_log_path = Path(__file__).resolve().parent.parent / "web-ui" / "public" / "meditations_repo_log.json"
            try:
                with open(local_log_path, 'w', encoding='utf-8') as f:
                    json.dump(meditations_log, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"  ⚠️ Could not update local log: {e}")
            print(f"   🎉 Complete: {output_key}")
            overall_success += 1

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"✅ Batch complete! Generated {overall_success} new unguided audio file(s).")
    print("=" * 60)


if __name__ == "__main__":
    main()