"""
Script to mix solfeggio background sound into an existing meditation audio.

The background sound starts after the opening gong and ends before the closing gong,
using the gong audio file to determine its exact duration.

Usage:
    python src/audio_mixing.py
    
    Optional arguments:
    --meditation-key    R2 key for the original meditation (default: meditations/meditations_meditation_5min_principiante_b1a55e8a-6cae-44e6-b833-977a5694617f_full_audio.wav)
    --solfeggio-key     R2 key for the solfeggio background (default: sounds/solfeggio-mix-285-528-852-hz.mp3)
    --gong-key          R2 key for the gong sound (default: sounds/freesound_community-gong-79191.mp3)
    --background-volume Volume level for background (0.0-1.0, default: 0.15)
    --fade-duration     Fade in/out duration in seconds (default: 3.0)
"""

import os
import argparse
import numpy as np
from dotenv import load_dotenv
import boto3
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
    """Download a file from R2 to local storage"""
    filename = file_key.split('/')[-1]
    local_file_path = f"{local_path}{filename}"
    print(f"  Downloading {file_key}...")
    r2_client.download_file(Bucket=bucket_name, Key=file_key, Filename=local_file_path)
    print(f"  ✅ Saved to {local_file_path}")
    return local_file_path


def upload_to_r2(r2_client, bucket_name, local_path, r2_key):
    """Upload a file to R2"""
    print(f"  Uploading to {r2_key}...")
    r2_client.upload_file(Filename=local_path, Bucket=bucket_name, Key=r2_key)
    print(f"  ✅ Uploaded: {r2_key}")


def main():
    parser = argparse.ArgumentParser(
        description='Add solfeggio background sound to a meditation audio, '
                    'avoiding the opening and closing gong sections.'
    )
    parser.add_argument(
        '--meditation-key', type=str,
        default='meditations/meditation_5min_principiante_'
                'b1a55e8a-6cae-44e6-b833-977a5694617f_full_audio.wav',
        help='R2 key for the original meditation audio (default: the 5min principiante meditation)'
    )
    parser.add_argument(
        '--solfeggio-key', type=str,
        default='sounds/solfeggio-mix-285-528-852-hz.mp3',
        help='R2 key for the solfeggio background sound (default: sounds/solfeggio-mix-285-528-852-hz.mp3)'
    )
    parser.add_argument(
        '--gong-key', type=str,
        default='sounds/freesound_community-gong-79191.mp3',
        help='R2 key for the gong sound file (default: sounds/freesound_community-gong-79191.mp3)'
    )
    parser.add_argument(
        '--background-volume', type=float, default=0.05,
        help='Volume level for the background relative to original (0.0-1.0, default: 0.05)'
    )
    parser.add_argument(
        '--fade-duration', type=float, default=3.0,
        help='Fade in/out duration for the background in seconds (default: 3.0)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🎵 Meditation Audio Mixer — Solfeggio Background")
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
    target_sr = 44100  # CD-quality sample rate for mixing

    # ── Connect to R2 ──────────────────────────────────────────────────
    print("\n🔗 Connecting to Cloudflare R2...")
    r2 = connect_to_r2()
    # Verify connection
    r2.head_bucket(Bucket=bucket_name)
    print("✅ Connection successful")

    # ── Download all audio files ────────────────────────────────────────
    print("\n📥 Downloading audio files from R2...")
    
    meditation_path = download_from_r2(r2, bucket_name, args.meditation_key)
    solfeggio_path = download_from_r2(r2, bucket_name, args.solfeggio_key)
    gong_path = download_from_r2(r2, bucket_name, args.gong_key)

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
    print(f"  Gong sound:        {gong_duration_s:.2f} s")
    print(f"  Original meditation: {meditation_duration_s:.2f} s")
    print(f"  Solfeggio track:   {solfeggio_duration_s:.2f} s")

    # Validate that the meditation is long enough to contain two gongs
    if meditation_duration_ms <= 2 * gong_duration_ms:
        raise ValueError(
            f"Meditation ({meditation_duration_s:.1f}s) is shorter than "
            f"2× gong duration ({2 * gong_duration_s:.1f}s). Cannot proceed."
        )

    # The background should play during the middle section only,
    # i.e. from after the opening gong to before the closing gong.
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
    fade_ms = int(args.fade_duration * 1000)
    if fade_ms > 0:
        background = background.fade_in(fade_ms).fade_out(fade_ms)
        print(f"  Applied {args.fade_duration}s fade in/out")

    # Reduce background volume relative to the original meditation
    # Convert linear volume ratio to dB: gain_db = 20 * log10(ratio)
    if args.background_volume < 1.0:
        import math
        gain_db = 20 * math.log10(args.background_volume)
        background = background.apply_gain(gain_db)
        print(f"  Background volume adjusted to {args.background_volume:.0%} "
              f"(gain: {gain_db:+.1f} dB)")

    # ── Position the background ─────────────────────────────────────────
    # The original meditation has this structure:
    #   [opening gong] [meditation content] [closing gong]
    # We overlay the background so it plays only during the meditation content
    # portion, avoiding both gong sections.
    print("\n🔄 Mixing audio tracks...")

    # Create leading and trailing silence for the gong sections
    silence_before = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)
    silence_after = AudioSegment.silent(duration=gong_duration_ms, frame_rate=target_sr)

    # Build the full background track with silence where gongs play:
    #   [silence = gong duration] + [background] + [silence = gong duration]
    full_background = silence_before + background + silence_after

    # Ensure the background track matches the meditation duration exactly
    if len(full_background) > meditation_duration_ms:
        full_background = full_background[:meditation_duration_ms]
    elif len(full_background) < meditation_duration_ms:
        pad_ms = meditation_duration_ms - len(full_background)
        full_background = full_background + AudioSegment.silent(duration=pad_ms, frame_rate=target_sr)

    # Mix: overlay the background onto the original meditation
    mixed_audio = meditation.overlay(full_background)

    # ── Export locally ──────────────────────────────────────────────────
    print("\n💾 Saving mixed audio...")
    # Derive output filename from the original meditation key
    meditation_filename = args.meditation_key.split('/')[-1]
    base_name = meditation_filename.replace('.wav', '')
    local_output = f"/tmp/{base_name}_with_solfeggio.wav"
    
    mixed_audio.export(local_output, format="wav")
    mixed_duration_s = len(mixed_audio) / 1000.0
    print(f"  ✅ Saved locally: {local_output}")
    print(f"  ⏱️  Mixed audio duration: {mixed_duration_s:.2f} s")

    # ── Upload to R2 ────────────────────────────────────────────────────
    print("\n☁️  Uploading to Cloudflare R2...")
    output_r2_key = f"meditations/{base_name}_with_solfeggio.wav"
    upload_to_r2(r2, bucket_name, local_output, output_r2_key)

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ SUCCESS — Meditation with solfeggio background generated!")
    print("=" * 60)
    print(f"  📥 Original meditation: {args.meditation_key}")
    print(f"  🎵 Background sound:    {args.solfeggio_key}")
    print(f"  🔔 Gong sound:          {args.gong_key}")
    print(f"  🎚️  Background volume:   {args.background_volume:.0%}")
    print(f"  💾 Local file:          {local_output}")
    print(f"  ☁️  R2 key:              {output_r2_key}")
    print("=" * 60)


if __name__ == "__main__":
    main()