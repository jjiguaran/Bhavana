"""
Script to batch-generate standalone background audio tracks (nature or binaural)
for all meditation durations that don't yet have a background file.

The generated audio has the following structure:
  [silence = gong duration] [background sound with fade in/out] [silence = gong duration]

This mirrors the background processing in audio_mixing.py's mix_nature_with_meditation
and mix_solfeggio_with_meditation, but produces a standalone background track without
mixing with any voice meditation.

The script reads the backgrounds_log.json from R2 to determine which durations
already have backgrounds, then generates any missing ones based on the durations
found in the meditations_repo_log.json.

Usage:
    python src/generate_background.py --mode nature
    python src/generate_background.py --mode binaural

Optional arguments:
    --mode              'nature' or 'binaural' (default: nature)
    --solfeggio-key     R2 key for the solfeggio background (default: sounds/solfeggio-mix-285-528-852-hz.mp3)
    --nature-key        R2 key for the nature background sound
                        (default: sounds/soundreality-stream-nature-445380.mp3)
    --gong-key          R2 key for the gong sound (used only for duration measurement)
                        (default: sounds/freesound_community-gong-79191.mp3)
    --background-volume Volume level for background (0.0-1.0, default: 0.05)
    --fade-duration     Fade in/out duration in seconds (default: 4.0)
"""

import os
import io
import json
import argparse
import math
import re
from datetime import date
from pathlib import Path
import numpy as np
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


def extract_minutes(duration_str):
    """Extract the number of minutes from a duration string like '5 min' or '30 min'."""
    match = re.match(r'(\d+)', str(duration_str))
    return int(match.group(1)) if match else None


def generate_background_nature(r2, bucket_name, nature_key, gong_key,
                                total_duration_s=300, background_volume=0.05,
                                fade_duration=4.0, target_sr=44100):
    """Generate a standalone nature background audio track.

    The track structure mirrors the background processing in audio_mixing.py:
      [silence = gong_duration] [nature sound with fade in/out] [silence = gong_duration]

    Args:
        r2: R2 client
        bucket_name: R2 bucket name
        nature_key: R2 key for the nature background sound
        gong_key: R2 key for the gong sound (used only for duration measurement)
        total_duration_s: Total duration of the output audio in seconds (default: 300 = 5 min)
        background_volume: Volume level for background (0.0-1.0, default: 0.05)
        fade_duration: Fade in/out duration in seconds (default: 4.0)
        target_sr: Target sample rate (default: 44100)

    Returns:
        AudioSegment with the generated background audio, or None on error
    """
    print("\n📥 Downloading audio files from R2...")

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
    nature = AudioSegment.from_file(nature_path).set_frame_rate(target_sr).set_channels(2)
    gong = AudioSegment.from_file(gong_path).set_frame_rate(target_sr).set_channels(2)

    # ── Compute durations ──────────────────────────────────────────────
    gong_duration_ms = len(gong)
    gong_duration_s = gong_duration_ms / 1000.0
    total_duration_ms = int(total_duration_s * 1000)
    nature_duration_s = len(nature) / 1000.0

    print(f"\n📊 Durations:")
    print(f"  Gong sound:          {gong_duration_s:.2f} s")
    print(f"  Total output:        {total_duration_s:.2f} s")
    print(f"  Nature track:        {nature_duration_s:.2f} s")

    # Validate that total duration is long enough to contain two gong sections
    if total_duration_ms <= 2 * gong_duration_ms:
        print(f"  ❌ Total duration ({total_duration_s:.1f}s) is shorter than "
              f"2× gong duration ({2 * gong_duration_s:.1f}s). Aborting.")
        return None

    # The nature background should play during the middle section only
    background_duration_ms = total_duration_ms - 2 * gong_duration_ms
    background_duration_s = background_duration_ms / 1000.0
    print(f"  Background section:  {background_duration_s:.2f} s "
          f"(total minus 2× gong)")

    # ── Prepare the background track ────────────────────────────────────
    print("\n🎛️  Preparing nature background...")

    # Trim the nature track to avoid fading at the beginning and end
    # Use the segment from second 4 to second 120 (116 seconds of clean audio)
    START_OFFSET_MS = 4_000    # 4 seconds
    END_OFFSET_MS = 120_000    # 120 seconds
    if len(nature) > END_OFFSET_MS:
        nature_trimmed = nature[START_OFFSET_MS:END_OFFSET_MS]
        print(f"  Trimmed nature track from 4s to 120s (original: {nature_duration_s:.0f}s)")
    else:
        nature_trimmed = nature[START_OFFSET_MS:]
        print(f"  Nature track is under {END_OFFSET_MS / 1000:.0f}s, starting from 4s "
              f"({len(nature_trimmed) / 1000:.0f}s)")

    # Loop or trim the nature track to match the exact background duration
    if len(nature_trimmed) >= background_duration_ms:
        background = nature_trimmed[:background_duration_ms]
        print(f"  Trimmed nature track to {background_duration_s:.1f}s")
    else:
        repeats = int(np.ceil(background_duration_ms / len(nature_trimmed)))
        background = nature_trimmed * repeats
        background = background[:background_duration_ms]
        print(f"  Looped nature track {repeats}x to fill {background_duration_s:.1f}s")

    # Reduce background volume
    if background_volume < 1.0:
        gain_db = 20 * math.log10(background_volume)
        background = background.apply_gain(gain_db)
        print(f"  Background volume adjusted to {background_volume:.0%} "
              f"(gain: {gain_db:+.1f} dB)")

    # Apply fade in/out directly to the background audio (not the full track
    # with silence sections) so the fade affects the actual sound, not silence.
    # This makes the background start very quiet and ramp up over the specified
    # duration, and vice versa at the end.
    fade_ms = int(fade_duration * 1000)
    if fade_ms > 0 and len(background) > fade_ms * 2:
        background = background.fade_in(fade_ms).fade_out(fade_ms)
        print(f"  Applied {fade_duration}s fade in/out to background audio")

    # ── Assemble the final track ────────────────────────────────────────
    print("\n🔄 Assembling final audio track...")

    # Create leading and trailing silence for the gong sections
    silence_before = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)
    silence_after = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)

    # Build the full track: silence + nature background + silence
    full_track = silence_before + background + silence_after

    # Ensure the track matches the total duration exactly
    if len(full_track) > total_duration_ms:
        full_track = full_track[:total_duration_ms]
        print(f"  Trimmed excess {len(full_track) / 1000 - total_duration_s:.2f}s")
    elif len(full_track) < total_duration_ms:
        pad_ms = total_duration_ms - len(full_track)
        full_track = full_track + AudioSegment.silent(duration=pad_ms, frame_rate=target_sr)
        print(f"  Padded with {pad_ms / 1000:.2f}s of silence")

    final_duration_s = len(full_track) / 1000.0
    print(f"\n✅ Final track duration: {final_duration_s:.2f} s")

    return full_track


def generate_background_binaural(r2, bucket_name, solfeggio_key, gong_key,
                                  total_duration_s=300, background_volume=0.05,
                                  fade_duration=4.0, target_sr=44100):
    """Generate a standalone binaural (solfeggio) background audio track.

    The track structure mirrors the background processing in audio_mixing.py:
      [silence = gong_duration] [solfeggio sound] [silence = gong_duration]

    Unlike nature, the solfeggio track is used directly (no trimming of start/end
    segments) since it's a continuous ambient tone.

    Args:
        r2: R2 client
        bucket_name: R2 bucket name
        solfeggio_key: R2 key for the solfeggio background sound
        gong_key: R2 key for the gong sound (used only for duration measurement)
        total_duration_s: Total duration of the output audio in seconds (default: 300 = 5 min)
        background_volume: Volume level for background (0.0-1.0, default: 0.05)
        fade_duration: Fade in/out duration in seconds (default: 4.0)
        target_sr: Target sample rate (default: 44100)

    Returns:
        AudioSegment with the generated background audio, or None on error
    """
    print("\n📥 Downloading audio files from R2...")

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
    solfeggio = AudioSegment.from_file(solfeggio_path).set_frame_rate(target_sr).set_channels(2)
    gong = AudioSegment.from_file(gong_path).set_frame_rate(target_sr).set_channels(2)

    # ── Compute durations ──────────────────────────────────────────────
    gong_duration_ms = len(gong)
    gong_duration_s = gong_duration_ms / 1000.0
    total_duration_ms = int(total_duration_s * 1000)
    solfeggio_duration_s = len(solfeggio) / 1000.0

    print(f"\n📊 Durations:")
    print(f"  Gong sound:          {gong_duration_s:.2f} s")
    print(f"  Total output:        {total_duration_s:.2f} s")
    print(f"  Solfeggio track:     {solfeggio_duration_s:.2f} s")

    # Validate that total duration is long enough to contain two gong sections
    if total_duration_ms <= 2 * gong_duration_ms:
        print(f"  ❌ Total duration ({total_duration_s:.1f}s) is shorter than "
              f"2× gong duration ({2 * gong_duration_s:.1f}s). Aborting.")
        return None

    # The solfeggio background should play during the middle section only
    background_duration_ms = total_duration_ms - 2 * gong_duration_ms
    background_duration_s = background_duration_ms / 1000.0
    print(f"  Background section:  {background_duration_s:.2f} s "
          f"(total minus 2× gong)")

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

    # Reduce background volume
    if background_volume < 1.0:
        gain_db = 20 * math.log10(background_volume)
        background = background.apply_gain(gain_db)
        print(f"  Background volume adjusted to {background_volume:.0%} "
              f"(gain: {gain_db:+.1f} dB)")

    # Apply fade in/out directly to the background audio (not the full track
    # with silence sections) so the fade affects the actual sound, not silence.
    fade_ms = int(fade_duration * 1000)
    if fade_ms > 0 and len(background) > fade_ms * 2:
        background = background.fade_in(fade_ms).fade_out(fade_ms)
        print(f"  Applied {fade_duration}s fade in/out to background audio")

    # ── Assemble the final track ────────────────────────────────────────
    print("\n🔄 Assembling final audio track...")

    # Create leading and trailing silence for the gong sections
    silence_before = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)
    silence_after = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)

    # Build the full track: silence + solfeggio background + silence
    full_track = silence_before + background + silence_after

    # Ensure the track matches the total duration exactly
    if len(full_track) > total_duration_ms:
        full_track = full_track[:total_duration_ms]
        print(f"  Trimmed excess {len(full_track) / 1000 - total_duration_s:.2f}s")
    elif len(full_track) < total_duration_ms:
        pad_ms = total_duration_ms - len(full_track)
        full_track = full_track + AudioSegment.silent(duration=pad_ms, frame_rate=target_sr)
        print(f"  Padded with {pad_ms / 1000:.2f}s of silence")

    final_duration_s = len(full_track) / 1000.0
    print(f"\n✅ Final track duration: {final_duration_s:.2f} s")

    return full_track


def main():
    parser = argparse.ArgumentParser(
        description='Batch-generate background audio tracks (nature or binaural) for all '
                    'meditation durations that are missing from backgrounds_log.json.'
    )
    parser.add_argument(
        '--mode', type=str, choices=['nature', 'binaural'], default='nature',
        help='Generation mode: "nature" uses nature sounds, '
             '"binaural" uses solfeggio tones (default: nature)'
    )
    parser.add_argument(
        '--solfeggio-key', type=str,
        default='sounds/solfeggio-mix-285-528-852-hz.mp3',
        help='R2 key for the solfeggio background sound '
             '(default: sounds/solfeggio-mix-285-528-852-hz.mp3)'
    )
    parser.add_argument(
        '--nature-key', type=str,
        default='sounds/soundreality-stream-nature-445380.mp3',
        help='R2 key for the nature background sound '
             '(default: sounds/soundreality-stream-nature-445380.mp3)'
    )
    parser.add_argument(
        '--gong-key', type=str,
        default='sounds/freesound_community-gong-79191.mp3',
        help='R2 key for the gong sound file '
             '(default: sounds/freesound_community-gong-79191.mp3)'
    )
    parser.add_argument(
        '--background-volume', type=float,
        help='Volume level for the background (0.0-1.0). '
             'Defaults to 0.05 for nature, 0.025 for binaural.'
    )
    parser.add_argument(
        '--fade-duration', type=float, default=4.0,
        help='Fade in/out duration for the background in seconds (default: 4.0)'
    )
    args = parser.parse_args()

    mode = args.mode

    # Set background volume default based on mode
    if args.background_volume is not None:
        background_volume = args.background_volume
    else:
        background_volume = 0.05 if mode == 'nature' else 0.025

    MODE_LABELS = {
        'nature': ('nature', '🌿 Batch Nature Background Generator'),
        'binaural': ('binaural', '🎵 Batch Binaural Background Generator'),
    }

    music_label, title = MODE_LABELS[mode]

    print("=" * 60)
    print(title)
    print("=" * 60)
    print(f"\n📋 Configuration:")
    print(f"  Mode:                {mode}")
    if mode == 'nature':
        print(f"  Background key:      {args.nature_key}")
    else:
        print(f"  Background key:      {args.solfeggio_key}")
    print(f"  Gong key:            {args.gong_key}")
    print(f"  Background volume:   {background_volume:.0%}")
    print(f"  Fade duration:       {args.fade_duration} s")

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

    # ── Read the backgrounds log ────────────────────────────────────────
    print("\n📋 Reading backgrounds log from R2...")
    log_key = "sounds/backgrounds/backgrounds_log.json"
    backgrounds_log = read_json_or_default(
        r2, bucket_name, log_key, {"backgrounds": []}
    )
    existing_backgrounds = backgrounds_log.get("backgrounds", [])
    print(f"   Found {len(existing_backgrounds)} background entrie(s) in the log.")

    # Build a set of (duration, music) tuples already covered
    existing_set = set()
    for entry in existing_backgrounds:
        dur = entry.get('duration')
        mus = entry.get('music')
        if dur and mus:
            existing_set.add((dur, mus))
    existing_for_mode = {d for (d, m) in existing_set if m == music_label}
    print(f"   {music_label.capitalize()} backgrounds already covered: "
          f"{sorted(existing_for_mode) if existing_for_mode else 'none'}")

    # ── Read the meditations log to get all unique durations ────────────
    print("\n📋 Reading meditations repo log from R2...")
    meditations_log = read_json_or_default(
        r2, bucket_name,
        "meditations/meditations_repo_log.json",
        {"meditations": []}
    )
    all_meditations = meditations_log.get("meditations", [])
    print(f"   Found {len(all_meditations)} meditation entrie(s) in the log.")

    # Extract all unique duration strings from meditations
    all_durations = set()
    for entry in all_meditations:
        dur = entry.get('duration')
        if dur:
            all_durations.add(dur)
    print(f"   Unique durations in meditations: {sorted(all_durations)}")

    # ── Find missing durations for this mode ────────────────────────────
    missing_durations = sorted(all_durations - existing_for_mode)
    print(f"\n🎯 Found {len(missing_durations)} duration(s) missing {mode} backgrounds:")
    for d in missing_durations:
        print(f"   - {d}")

    if not missing_durations:
        print(f"\n✅ All meditation durations already have {mode} background files. Nothing to do.")
        return

    # ── Process each missing duration ───────────────────────────────────
    target_sr = 44100
    success_count = 0

    for i, duration_str in enumerate(missing_durations, 1):
        minutes = extract_minutes(duration_str)
        if minutes is None:
            print(f"\n⚠️ Could not parse duration '{duration_str}', skipping.")
            continue

        total_duration_s = minutes * 60
        output_key = f"sounds/backgrounds/{minutes}_{mode}.opus"

        print(f"\n{'='*60}")
        print(f"[{i}/{len(missing_durations)}] Generating {mode} background for {duration_str} "
              f"({minutes} min)")
        print(f"   Output: {output_key}")

        # ── Generate the background audio ───────────────────────────────
        if mode == 'nature':
            background_audio = generate_background_nature(
                r2, bucket_name,
                nature_key=args.nature_key,
                gong_key=args.gong_key,
                total_duration_s=total_duration_s,
                background_volume=background_volume,
                fade_duration=args.fade_duration,
                target_sr=target_sr
            )
        else:  # mode == 'binaural'
            background_audio = generate_background_binaural(
                r2, bucket_name,
                solfeggio_key=args.solfeggio_key,
                gong_key=args.gong_key,
                total_duration_s=total_duration_s,
                background_volume=background_volume,
                fade_duration=args.fade_duration,
                target_sr=target_sr
            )

        if background_audio is None:
            print(f"   ⚠️ Skipping {duration_str} due to processing error.")
            continue

        # ── Export to memory and upload to R2 ───────────────────────────
        print("\n💾 Exporting audio to memory...")
        buf = io.BytesIO()
        background_audio.export(buf, format="opus")
        opus_bytes = buf.getvalue()
        buf.close()

        final_duration_s = len(background_audio) / 1000.0
        print(f"  ⏱️  Final audio duration: {final_duration_s:.2f} s")

        print("\n☁️  Uploading to Cloudflare R2...")
        upload_bytes_to_r2(r2, bucket_name, opus_bytes, output_key)

        # ── Update backgrounds log ──────────────────────────────────────
        source_key = args.nature_key if mode == 'nature' else args.solfeggio_key
        source_filename = source_key.split('/')[-1]
        new_entry = {
            "duration": duration_str,
            "date_generated": date.today().strftime("%Y-%m-%d"),
            "music": music_label,
            "source_file": source_filename
        }
        backgrounds_log["backgrounds"].append(new_entry)
        upload_json_to_r2(r2, bucket_name, log_key, backgrounds_log)
        print(f"   🎉 Complete: {output_key}")
        success_count += 1

    # ── Update local copy of the log ────────────────────────────────────
    local_log_path = Path(__file__).resolve().parent.parent / "web-ui" / "public" / "backgrounds_log.json"
    try:
        with open(local_log_path, 'w', encoding='utf-8') as f:
            json.dump(backgrounds_log, f, indent=2, ensure_ascii=False)
        print(f"\n  ✅ Local log updated: {local_log_path}")
    except Exception as e:
        print(f"\n  ⚠️ Could not update local log at {local_log_path}: {e}")

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"✅ Batch complete! Generated {success_count} new {mode} background file(s).")
    print("=" * 60)


if __name__ == "__main__":
    main()