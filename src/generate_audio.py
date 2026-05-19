# cell 1
# Install qwen-tts and soundfile
!pip install -q qwen-tts soundfile
!pip install -q boto3
!pip install -q pydub

# Optional but recommended: FlashAttention 2 for lower VRAM usage
# (takes ~5 min to compile — skip if you're in a hurry)
# !pip install -q flash-attn --no-build-isolation

print('✅ Dependencies installed')

import torch
import soundfile as sf
from IPython.display import Audio, display
from qwen_tts import Qwen3TTSModel
from pydub import AudioSegment

# ── Choose your model ──────────────────────────────────────────────────────
# Options:
#   "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"   ← preset voices + instruction control
#   "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"   ← describe any voice freely
#   "Qwen/Qwen3-TTS-12Hz-1.7B-Base"          ← voice cloning
#   "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"   ← lighter, faster
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
# ──────────────────────────────────────────────────────────────────────────

print(f'Loading {MODEL_ID} ...')
model = Qwen3TTSModel.from_pretrained(
    MODEL_ID,
    device_map="cuda:0",
    dtype=torch.bfloat16,
    # attn_implementation="flash_attention_2",  # uncomment if flash-attn is installed
)
print('✅ Model loaded')

# Show available speakers (only relevant for CustomVoice models)
if hasattr(model, 'get_supported_speakers'):
    print('\nAvailable speakers:', model.get_supported_speakers())
    print('Available languages:', model.get_supported_languages())

# ── Configure ──────────────────────────────────────────────────────────────
SESSION_NAME = "sleep_meditation_designed"
LANGUAGE     = "Spanish"
VOICE_DESC   = """
Soft, female voice, mid-range, very slow and deliberate pace. Argentinian accent.
Slightly breathy, with a warm resonance. Like a whisper that fills the room.
Each word is spaced with intention. Calm to the point of near-stillness.
"""

# cell 2
import json
import getpass
from pathlib import Path
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import numpy as np
import re

def get_r2_credentials():
    """Prompt for R2 credentials securely"""
    print("🔐 Please enter your R2 credentials:")
    access_key = getpass.getpass("Access Key ID: ")
    secret_key = getpass.getpass("Secret Access Key: ")
    account_id = getpass.getpass("Account ID: ")
    bucket_name = getpass.getpass("Bucket Name: ")
    
    return {
        'access_key': access_key,
        'secret_key': secret_key,
        'account_id': account_id,
        'bucket_name': bucket_name
    }

def connect_to_r2(credentials):
    """Create R2 connection"""
    return boto3.client(
        's3',
        endpoint_url=f'https://{credentials["account_id"]}.r2.cloudflarestorage.com',
        aws_access_key_id=credentials['access_key'],
        aws_secret_access_key=credentials['secret_key'],
        region_name='auto'
    )

def list_json_files_in_meditations(r2_client, bucket_name):
    """List all JSON files in the scripts directory"""
    try:
        response = r2_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='scripts/',
            Delimiter='/'
        )
        
        json_files = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith('.json') and key != 'scripts/':
                json_files.append({
                    'key': key,
                    'last_modified': obj['LastModified'],
                    'size': obj['Size']
                })
        
        # Sort by last modified (most recent first)
        json_files.sort(key=lambda x: x['last_modified'], reverse=True)
        return json_files
        
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return []

def list_voice_files_in_r2(r2_client, bucket_name):
    """List all audio files in the voices directory"""
    try:
        response = r2_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='voices/',
            Delimiter='/'
        )
        
        voice_files = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            # Support common audio formats
            if key.endswith(('.wav', '.mp3', '.flac', '.m4a', '.ogg')) and key != 'voices/':
                voice_files.append({
                    'key': key,
                    'filename': key.split('/')[-1],
                    'last_modified': obj['LastModified'],
                    'size': obj['Size']
                })
        
        # Sort by filename
        voice_files.sort(key=lambda x: x['filename'])
        return voice_files
        
    except Exception as e:
        print(f"❌ Error listing voice files: {e}")
        return []

def download_from_r2(r2_client, bucket_name, file_key, local_path="/tmp/"):
    """Download any file from R2 to local storage"""
    try:
        filename = file_key.split('/')[-1]
        local_file_path = f"{local_path}{filename}"
        r2_client.download_file(bucket_name, file_key, local_file_path)
        print(f"✅ File downloaded: {local_file_path}")
        return local_file_path
    except Exception as e:
        print(f"❌ Error downloading file {file_key}: {e}")
        return None


def download_gong_from_r2(r2_client, bucket_name, gong_filename="freesound_community-gong-79191.mp3", local_path="/tmp/"):
    """Download the gong sound from the sounds/ directory in R2"""
    gong_key = f"sounds/{gong_filename}"
    return download_from_r2(r2_client, bucket_name, gong_key, local_path)


def load_audio_as_numpy(audio_path, target_sr=24000):
    """Load an audio file (MP3, WAV, etc.) and convert to numpy array at target sample rate.
    
    Returns:
        tuple: (numpy array of float32 samples, sample_rate)
    """
    audio = AudioSegment.from_file(audio_path)
    # Convert to target sample rate
    audio = audio.set_frame_rate(target_sr)
    # Convert to numpy array (mono)
    if audio.channels > 1:
        audio = audio.set_channels(1)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0
    return samples, target_sr


def download_voice_from_r2(r2_client, bucket_name, voice_key, local_path="/tmp/"):
    """Download voice file from R2 to local storage"""
    try:
        filename = voice_key.split('/')[-1]
        local_file_path = f"{local_path}{filename}"
        
        r2_client.download_file(bucket_name, voice_key, local_file_path)
        print(f"✅ Voice file downloaded: {local_file_path}")
        return local_file_path
        
    except Exception as e:
        print(f"❌ Error downloading voice file: {e}")
        return None

def select_json_file(json_files):
    """Select the most recent JSON file or let user choose"""
    if not json_files:
        print("❌ No JSON files found in scripts directory")
        return None
    
    print(f"\n📁 Found {len(json_files)} JSON file(s) in scripts directory:")
    
    # Show all files with info
    for i, file_info in enumerate(json_files, 1):
        filename = file_info['key'].split('/')[-1]
        size_kb = file_info['size'] / 1024
        date_str = file_info['last_modified'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {i}. {filename} ({size_kb:.1f} KB, {date_str})")
    
    # Auto-select most recent if there's only one, or ask user to choose
    if len(json_files) == 1:
        selected = json_files[0]
        print(f"\n✅ Auto-selected: {selected['key'].split('/')[-1]}")
    else:
        print(f"\n🕐 Auto-selecting most recent: {json_files[0]['key'].split('/')[-1]}")
        selected = json_files[0]
    
    return selected['key']

def select_voice_file(voice_files):
    """Select a voice file for cloning"""
    if not voice_files:
        print("❌ No voice files found in voices directory")
        return None
    
    print(f"\n🎙️ Found {len(voice_files)} voice file(s) in voices directory:")
    
    # Show all files with info
    for i, file_info in enumerate(voice_files, 1):
        filename = file_info['filename']
        size_kb = file_info['size'] / 1024
        print(f"  {i}. {filename} ({size_kb:.1f} KB)")
    
    # Auto-select first if there's only one
    if len(voice_files) == 1:
        selected = voice_files[0]
        print(f"\n✅ Auto-selected: {selected['filename']}")
    else:
        print(f"\n🕐 Auto-selecting first voice: {voice_files[0]['filename']}")
        selected = voice_files[0]
    
    return selected['key']

def read_json_from_r2(r2_client, bucket_name, file_key):
    """Read JSON file from R2"""
    try:
        response = r2_client.get_object(Bucket=bucket_name, Key=file_key)
        json_content = response['Body'].read().decode('utf-8')
        return json.loads(json_content)
    except Exception as e:
        print(f"❌ Error reading JSON from R2: {e}")
        return None

def extract_target_duration_from_filename(json_file_key):
    """Extract intended meditation duration from JSON filename
    
    Expected format: meditation_5min_level_uuid.json
    Returns duration in seconds, or None if not found
    """
    filename = json_file_key.split('/')[-1]
    
    # Look for duration pattern like "5min", "10min", etc.
    match = re.search(r'meditation_(\d+)min', filename)
    if match:
        minutes = int(match.group(1))
        return minutes * 60  # Convert to seconds
    return None

def parse_and_generate_audio(model, content, language, reference_audio_path, ref_text="", instruct=""):
    """Parse meditation content, generate TTS for speech lines ONCE, and track silence durations.
    
    Returns:
        tuple: (final_audio, sample_rate, speech_duration, total_silence_duration)
    """
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    target_sr = 24000
    
    # Generate all audio segments: speech via TTS, silence as placeholder durations
    segments = []  # list of (type, data) where type is 'speech' (audio array) or 'silence' (duration in seconds)
    
    for line in lines:
        silence_match = re.match(r'\[silencio:\s*(\d+)\s*segundos?\]', line, re.IGNORECASE)
        if silence_match:
            segments.append(('silence', int(silence_match.group(1))))
        else:
            # Generate TTS using voice cloning (happens only once)
            wavs, sr = model.generate_voice_clone(
                text=line,
                language=language,
                ref_audio=reference_audio_path,
                ref_text=ref_text,
                instruct=instruct,
            )
            if sr != target_sr:
                from scipy import signal
                resampled = signal.resample(wavs[0], int(len(wavs[0]) * target_sr / sr))
                segments.append(('speech', resampled.astype(np.float32)))
            else:
                segments.append(('speech', wavs[0]))
    
    # Calculate speech duration and total original silence
    speech_duration = sum(len(audio) for seg_type, audio in segments if seg_type == 'speech') / target_sr
    total_silence = sum(dur for seg_type, dur in segments if seg_type == 'silence')
    
    return segments, target_sr, speech_duration, total_silence


def assemble_adjusted_audio(segments, sample_rate, target_duration=None, gong_audio=None):
    """Assemble final audio from segments, adjusting silence durations to hit target.
    
    This does NOT regenerate TTS — it only scales silence segments.
    If target_duration is None, original silence durations are kept.
    If there's no speech content, falls back to silence-only audio.
    
    If gong_audio is provided, it is added at the beginning and end of the audio.
    The gong duration is factored into the silence adjustment calculation so the
    total audio (speech + 2×gong + adjusted silence) matches target_duration.
    
    Args:
        segments: list of ('speech', audio_array) or ('silence', duration_seconds)
        sample_rate: target sample rate
        target_duration: desired total duration in seconds, or None for original timing
        gong_audio: numpy array of gong audio samples, or None to skip
    
    Returns:
        numpy array of audio samples
    """
    speech_duration = sum(len(audio) for seg_type, audio in segments if seg_type == 'speech') / sample_rate
    total_original_silence = sum(dur for seg_type, dur in segments if seg_type == 'silence')
    
    # Account for gong duration (2x since it plays at beginning and end)
    gong_duration = (len(gong_audio) / sample_rate) if gong_audio is not None else 0.0
    total_gong_duration = 2 * gong_duration
    
    # Determine silence factor
    if target_duration is not None:
        # Fixed content includes speech + gong at both ends
        fixed_duration = speech_duration + total_gong_duration
        needed_total_silence = max(0, target_duration - fixed_duration)
        if total_original_silence > 0 and needed_total_silence >= 0:
            silence_factor = needed_total_silence / total_original_silence
        else:
            silence_factor = 1.0
    else:
        silence_factor = 1.0
    
    final_parts = []
    
    # Add gong at the beginning
    if gong_audio is not None:
        final_parts.append(gong_audio)
    
    for seg_type, data in segments:
        if seg_type == 'speech':
            final_parts.append(data)
        else:  # silence
            original_dur = data
            adjusted_dur = int(original_dur * silence_factor * sample_rate)
            final_parts.append(np.zeros(adjusted_dur, dtype=np.float32))
    
    # Add gong at the end
    if gong_audio is not None:
        final_parts.append(gong_audio)
    
    return np.concatenate(final_parts), sample_rate

def save_audio_to_r2(r2_client, bucket_name, audio_data, sr, json_file_key, prefix="full"):
    """Save audio to R2 in same directory as JSON"""
    try:
        # Save audio to temporary file first
        temp_file = f"/tmp/generated_audio_{prefix}.wav"
        sf.write(temp_file, audio_data, sr)
        
        # Create audio file key in same directory as JSON
        json_filename = json_file_key.split('/')[-1]
        json_basename = json_filename.replace('.json', '')
        audio_filename = f"{json_basename}_{prefix}_audio.wav"
        audio_key = f"meditations/{audio_filename}"
        
        # Upload to R2
        r2_client.upload_file(temp_file, bucket_name, audio_key)
        print(f"✅ Audio saved to R2: {audio_key}")
        return audio_key
    except Exception as e:
        print(f"❌ Error saving audio to R2: {e}")
        return None


# Main workflow
try:
    # Get credentials and connect
    credentials = get_r2_credentials()
    r2_client = connect_to_r2(credentials)
    
    # Test connection
    print("🔗 Testing R2 connection...")
    r2_client.head_bucket(Bucket=credentials['bucket_name'])
    print("✅ R2 connection successful")
    
    # List and select JSON file from scripts directory
    print("\n🔍 Searching for JSON files in scripts directory...")
    json_files = list_json_files_in_meditations(r2_client, credentials['bucket_name'])
    json_file_key = select_json_file(json_files)
    
    # List and select voice file from voices directory
    print("\n🎙️ Searching for voice files in voices directory...")
    voice_files = list_voice_files_in_r2(r2_client, credentials['bucket_name'])
    voice_file_key = select_voice_file(voice_files)
    
    if json_file_key and voice_file_key:
        # Download voice file
        print(f"\n📥 Downloading voice file: {voice_file_key}")
        reference_audio_path = download_voice_from_r2(r2_client, credentials['bucket_name'], voice_file_key)
        
        if reference_audio_path:
            # Read JSON from R2
            print(f"\n📖 Reading JSON from: {json_file_key}")
            json_data = read_json_from_r2(r2_client, credentials['bucket_name'], json_file_key)
            
            if json_data:
                # Extract meditation content from JSON
                text_content = (json_data.get('meditation_content') or 
                              json_data.get('text') or 
                              json_data.get('content') or 
                              json_data.get('meditation_text')) if isinstance(json_data, dict) else str(json_data)
                
                if not text_content:
                    text_content = "Prepárate para iniciar la sesión. Siéntate en un lugar cómodo y respira profundamente.\n[silencio: 10 segundos]"
                
                print(f"📝 Processing meditation content ({len(text_content)} chars)...")
                
                # Extract target duration from filename
                target_duration = extract_target_duration_from_filename(json_file_key)
                if target_duration:
                    print(f"⏱️ Target duration: {target_duration // 60} min {target_duration % 60} sec")
                
                # ref_text: transcription of the reference audio for better voice cloning accuracy
                ref_text = "Encontré una psicóloga a cinco minutos de tu casa. Si quieres, te puedo dar su número de teléfono."
                
                # Download gong sound from R2 sounds directory
                print("🔔 Downloading gong sound from 'sounds/' directory...")
                gong_path = download_gong_from_r2(r2_client, credentials['bucket_name'])
                gong_audio = None
                if gong_path:
                    gong_audio, gong_sr = load_audio_as_numpy(gong_path, target_sr=24000)
                    gong_dur = len(gong_audio) / 24000
                    print(f"🔔 Gong loaded: {gong_dur:.1f}s (will be added at beginning and end)")
                else:
                    print("⚠️ No gong sound found — proceeding without it")
                
                # Generate audio using voice cloning — TTS happens ONLY ONCE
                print("🎵 Generating audio with cloned voice...")
                segments, final_sr, speech_duration, total_silence = parse_and_generate_audio(
                    model, text_content, LANGUAGE, reference_audio_path, ref_text, VOICE_DESC
                )
                
                # Calculate effective durations accounting for gong
                gong_total = (2 * len(gong_audio) / final_sr) if gong_audio is not None else 0.0
                
                # Assemble with original silence durations for initial measurement (with gong)
                initial_audio, _ = assemble_adjusted_audio(segments, final_sr, target_duration=None, gong_audio=gong_audio)
                initial_duration = len(initial_audio) / final_sr
                print(f"✅ Audio created: {speech_duration:.1f}s speech + {gong_total:.1f}s gong + {total_silence:.1f}s silence = {initial_duration:.1f}s total")
                
                # Adjust silence proportionally if target duration was found
                if target_duration:
                    if abs(initial_duration - target_duration) > 1.5:  # More than 1.5 seconds difference
                        if total_silence > 0:
                            # Calculate what silence factor is needed to reach target (gong included in fixed content)
                            fixed_content = speech_duration + gong_total
                            needed_silence = target_duration - fixed_content
                            silence_factor = needed_silence / total_silence
                            
                            print(f"\n🔧 Adjusting silences: speech={speech_duration:.1f}s + gong={gong_total:.1f}s + silence (×{silence_factor:.2f}) = {needed_silence:.1f}s")
                            # assemble_adjusted_audio does NOT regenerate TTS — only scales silence samples
                            final_audio, final_sr = assemble_adjusted_audio(segments, final_sr, target_duration, gong_audio=gong_audio)
                            duration = len(final_audio) / final_sr
                            print(f"✅ Audio adjusted: {duration:.1f} seconds (target: {target_duration:.1f} seconds)")
                        else:
                            # No silences in content, pad with silence at the end
                            padding_duration = target_duration - initial_duration
                            padding_samples = int(padding_duration * final_sr)
                            padding = np.zeros(padding_samples, dtype=np.float32)
                            final_audio = np.concatenate([initial_audio, padding])
                            duration = len(final_audio) / final_sr
                            print(f"\n🔧 Padding with {padding_duration:.1f}s of silence at the end")
                            print(f"✅ Audio adjusted: {duration:.1f} seconds (target: {target_duration:.1f} seconds)")
                    else:
                        print(f"✅ Duration already matches target ({initial_duration:.1f}s ≈ {target_duration:.1f}s)")
                        final_audio = initial_audio
                else:
                    final_audio = initial_audio
                
                # Display and save
                display(Audio(final_audio, rate=final_sr))
                
                # Save to R2
                combined_key = save_audio_to_r2(r2_client, credentials['bucket_name'], 
                                             final_audio, final_sr, json_file_key, "full")
                
                if combined_key:
                    print(f"🎉 Complete! Audio saved: {combined_key}")
                
                # Save local copy
                sf.write("/tmp/meditation_audio.wav", final_audio, final_sr)
        else:
            print("❌ Failed to download voice file")
    else:
        if not json_file_key:
            print("❌ No JSON file selected")
        if not voice_file_key:
            print("❌ No voice file selected")
        
except NoCredentialsError:
    print("❌ Invalid R2 credentials")
except ClientError as e:
    print(f"❌ R2 Client Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")


