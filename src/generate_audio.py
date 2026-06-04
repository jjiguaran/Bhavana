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
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
# ──────────────────────────────────────────────────────────────────────────

print(f'Loading {MODEL_ID} ...')
model = Qwen3TTSModel.from_pretrained(
    MODEL_ID,
    device_map="cuda:0",
    dtype=torch.bfloat16,
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
            if key.endswith(('.wav', '.mp3', '.flac', '.m4a', '.ogg')) and key != 'voices/':
                voice_files.append({
                    'key': key,
                    'filename': key.split('/')[-1],
                    'last_modified': obj['LastModified'],
                    'size': obj['Size']
                })
        
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
        print(f"  ✅ Downloaded: {local_file_path}")
        return local_file_path
    except Exception as e:
        print(f"  ❌ Error downloading file {file_key}: {e}")
        return None

def download_gong_from_r2(r2_client, bucket_name, gong_filename="freesound_community-gong-79191.mp3", local_path="/tmp/"):
    """Download the gong sound from the sounds/ directory in R2"""
    gong_key = f"sounds/{gong_filename}"
    return download_from_r2(r2_client, bucket_name, gong_key, local_path)

def load_audio_as_numpy(audio_path, target_sr=24000):
    """Load an audio file and convert to numpy array at target sample rate."""
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(target_sr)
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
        print(f"  ✅ Voice file downloaded: {local_file_path}")
        return local_file_path
        
    except Exception as e:
        print(f"  ❌ Error downloading voice file: {e}")
        return None

def select_voice_file(voice_files):
    """Select the first available voice file for cloning"""
    if not voice_files:
        print("❌ No voice files found in voices directory")
        return None
    
    selected = voice_files[0]
    print(f"\n🎙️ Using voice: {selected['filename']}")
    return selected['key']

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

def build_script_filename(script_info):
    """Build the filename for a script given its duration, level, and variation."""
    duration_str = script_info.get('duration', '')
    match = re.match(r'(\d+)', duration_str)
    minutes = match.group(1) if match else '0'
    level = script_info.get('level', 'unknown')
    variation = script_info.get('variation', 1)
    return f"{minutes}_{level}_{variation}.json"

def build_meditation_key(script_filename):
    """Turn a script filename like '5_principiante_1.json' into the audio key."""
    basename = script_filename.replace('.json', '')
    return f"meditations/silence/{basename}.opus"

def extract_target_duration_from_filename(json_file_key):
    """Extract intended meditation duration from JSON filename"""
    filename = json_file_key.split('/')[-1]
    
    match = re.search(r'(\d+)\s*min', filename, re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        return minutes * 60
    
    match = re.match(r'(\d+)_', filename)
    if match:
        minutes = int(match.group(1))
        return minutes * 60
    
    return None

def parse_and_generate_audio(model, content, language, reference_audio_path, ref_text="", instruct=""):
    """Parse meditation content, generate TTS for speech lines ONCE, and track silence durations.
    Fades the voice signal down to match the exact level of the organic background hum,
    preventing any "dead air" drops before structural silences.
    """
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    target_sr = 24000
    segments = []
    
    for line in lines:
        silence_match = re.match(r'\[silencio:\s*(\d+)\s*segundos?\]', line, re.IGNORECASE)
        if silence_match:
            segments.append(('silence', int(silence_match.group(1))))
        else:
            # Ensure the line has a trailing cadence marker so the model winds down naturally
            clean_line = line.strip()
            if not clean_line.endswith(('.', ',', '?', '!', '...')):
                clean_line += "..."

            wavs, sr = model.generate_voice_clone(
                text=clean_line,
                language=language,
                ref_audio=reference_audio_path,
                ref_text=ref_text,
                instruct=instruct,
            )
            
            speech_signal = wavs[0]
            if sr != target_sr:
                from scipy import signal
                speech_signal = signal.resample(speech_signal, int(len(speech_signal) * target_sr / sr))
            
            # ─── FIXED: FADE TO ORGANIC BACKGROUND HUM ───
            # 1. Create a natural trailing cushion (0.5s)
            buffer_duration = 0.50  
            buffer_samples = int(buffer_duration * target_sr)
            
            # Generate the exact same organic comfort noise profile used in the rest of the app
            HUM_LEVEL = 0.00005
            comfort_tail = np.random.normal(0, HUM_LEVEL, buffer_samples).astype(np.float32)
            
            # Concatenate the voice with our trailing room cushion
            extended_signal = np.concatenate([speech_signal, comfort_tail])
            
            # 2. Apply the 400ms exponential fade-out to the VOICE ONLY
            fade_duration = 0.40  
            fade_samples = int(fade_duration * target_sr)
            
            if len(extended_signal) > fade_samples:
                # Creates an exponential decay window from 1.0 down to 0.0
                fade_window = np.logspace(0, -3, num=fade_samples, base=10.0)
                fade_window = (fade_window - fade_window[-1]) / (fade_window[0] - fade_window[-1])
                
                # Extract the audio chunk we want to fade
                fade_chunk = extended_signal[-fade_samples:]
                
                # Generate a parallel layer of clean background hum for this chunk
                constant_hum = np.random.normal(0, HUM_LEVEL, fade_samples).astype(np.float32)
                
                # Apply the fade to the audio chunk, but add back the un-faded constant hum.
                # This ensures the voice signals disappear to 0, leaving ONLY the hum active.
                extended_signal[-fade_samples:] = (fade_chunk * fade_window) + (constant_hum * (1.0 - fade_window))
            # ─────────────────────────────────────────────

            segments.append(('speech', extended_signal.astype(np.float32)))
    
    speech_duration = sum(len(audio) for seg_type, audio in segments if seg_type == 'speech') / target_sr
    total_silence = sum(dur for seg_type, dur in segments if seg_type == 'silence')
    
    return segments, target_sr, speech_duration, total_silence

def assemble_adjusted_audio(segments, sample_rate, target_duration=None, gong_audio=None):
    """Assemble final audio, converting digital zero silence blocks to microscopic room tone."""
    speech_duration = sum(len(audio) for seg_type, audio in segments if seg_type == 'speech') / sample_rate
    total_original_silence = sum(dur for seg_type, dur in segments if seg_type == 'silence')
    
    gong_duration = (len(gong_audio) / sample_rate) if gong_audio is not None else 0.0
    total_gong_duration = 2 * gong_duration
    
    if target_duration is not None:
        fixed_duration = speech_duration + total_gong_duration
        needed_total_silence = max(0, target_duration - fixed_duration)
        if total_original_silence > 0 and needed_total_silence >= 0:
            silence_factor = needed_total_silence / total_original_silence
        else:
            silence_factor = 1.0
    else:
        silence_factor = 1.0
    
    final_parts = []
    
    if gong_audio is not None:
        final_parts.append(gong_audio)
    
    for seg_type, data in segments:
        if seg_type == 'speech':
            final_parts.append(data)
        else:
            original_dur = data
            adjusted_dur = int(original_dur * silence_factor * sample_rate)
            
            # Fix 3: Fill silences with microscopic Gaussian comfort noise instead of absolute zeros
            # This subtle noise floor prevents users' headphones from sounding "dead" or dropping out.
            comfort_noise = np.random.normal(0, 0.00005, adjusted_dur).astype(np.float32)
            final_parts.append(comfort_noise)
    
    if gong_audio is not None:
        final_parts.append(gong_audio)
    
    return np.concatenate(final_parts), sample_rate

def save_audio_to_r2(r2_client, bucket_name, audio_data, sr, script_filename):
    """Save audio to R2 in meditations/ directory"""
    try:
        temp_file = f"/tmp/generated_audio.opus"
        audio_segment = AudioSegment(
            (audio_data * 32768).astype(np.int16).tobytes(),
            frame_rate=sr,
            sample_width=2,
            channels=1
        )
        audio_segment.export(temp_file, format="opus")
        
        basename = script_filename.replace('.json', '')
        audio_filename = f"{basename}.opus"
        audio_key = f"meditations/silence/{audio_filename}"
        
        r2_client.upload_file(temp_file, bucket_name, audio_key)
        print(f"  ✅ Audio saved to R2: {audio_key}")
        return audio_key
    except Exception as e:
        print(f"  ❌ Error saving audio to R2: {e}")
        return None


# ── Main workflow: batch-generate missing meditations ──────────────────────
try:
    credentials = get_r2_credentials()
    r2_client = connect_to_r2(credentials)
    
    print("🔗 Testing R2 connection...")
    r2_client.head_bucket(Bucket=credentials['bucket_name'])
    print("✅ R2 connection successful")
    
    print("\n📋 Reading scripts repo log...")
    scripts_log = read_json_or_default(
        r2_client, credentials['bucket_name'],
        "scripts/scripts_repo_log.json",
        {"scripts": []}
    )
    all_scripts = scripts_log.get("scripts", [])
    print(f"   Found {len(all_scripts)} script(s) registered in the repo log.")
    
    print("\n📋 Reading meditations repo log...")
    meditations_log = read_json_or_default(
        r2_client, credentials['bucket_name'],
        "meditations/meditations_repo_log.json",
        {"meditations": []}
    )
    existing_meditations = meditations_log.get("meditations", [])
    print(f"   Found {len(existing_meditations)} meditation(s) already generated.")
    
    existing_set = set()
    for m in existing_meditations:
        existing_set.add((
            m.get('duration'),
            m.get('level'),
            m.get('variation')
        ))
    
    missing = []
    for script in all_scripts:
        key = (script.get('duration'), script.get('level'), script.get('variation'))
        if key not in existing_set:
            missing.append(script)
    
    if not missing:
        print("\n✅ All scripts already have their meditation audio generated. Nothing to do.")
    else:
        print(f"\n🎯 Found {len(missing)} meditation(s) to generate:")
        for s in missing:
            print(f"   - {s.get('duration')} | {s.get('level')} | variation {s.get('variation')} | model: {s.get('model')}")
    
    print("\n🎙️ Searching for voice files in voices directory...")
    voice_files = list_voice_files_in_r2(r2_client, credentials['bucket_name'])
    voice_file_key = select_voice_file(voice_files)
    
    print("\n🔔 Downloading gong sound from 'sounds/' directory...")
    gong_path = download_gong_from_r2(r2_client, credentials['bucket_name'])
    gong_audio = None
    if gong_path:
        gong_audio, gong_sr = load_audio_as_numpy(gong_path, target_sr=24000)
        gong_dur = len(gong_audio) / 24000
        print(f"   Gong loaded: {gong_dur:.1f}s (will be added at beginning and end)")
    else:
        print("   ⚠️ No gong sound found — proceeding without it")
    
    if not voice_file_key:
        print("❌ No voice file available. Aborting.")
    else:
        reference_audio_path = download_voice_from_r2(r2_client, credentials['bucket_name'], voice_file_key)
        
        if not reference_audio_path:
            print("❌ Failed to download voice file. Aborting.")
        else:
            ref_text = "Encontré una psicóloga a cinco minutos de tu casa. Si quieres, te puedo dar su número de teléfono."
            
            for script_info in missing:
                duration_str = script_info.get('duration', '')
                level = script_info.get('level', 'unknown')
                variation = script_info.get('variation', 1)
                script_model = script_info.get('model', 'unknown')
                
                script_filename = build_script_filename(script_info)
                script_key = f"scripts/{script_filename}"
                meditation_key = build_meditation_key(script_filename)
                
                print(f"\n{'='*60}")
                print(f"🎯 Generating: {duration_str} | {level} | variation {variation}")
                
                json_data = read_json_from_r2(r2_client, credentials['bucket_name'], script_key)
                if not json_data:
                    print(f"   ⚠️ Could not read script, skipping.")
                    continue
                
                text_content = (json_data.get('meditation_content') or 
                              json_data.get('text') or 
                              json_data.get('content') or 
                              json_data.get('meditation_text')) if isinstance(json_data, dict) else str(json_data)
                
                if not text_content:
                    text_content = "Prepárate para iniciar la sesión. Siéntate en un lugar cómodo y respira profundamente.\n[silencio: 10 segundos]"
                
                print(f"   📝 Content: {len(text_content)} chars")
                
                if len(text_content) > 10000:
                    print(f"   ⚠️ Content exceeds 10,000 chars. Skipping.")
                    continue
                
                target_duration = extract_target_duration_from_filename(script_key)
                if target_duration:
                    print(f"   ⏱️ Target: {target_duration // 60} min {target_duration % 60} sec")
                
                print("   🎵 Generating TTS...")
                segments, final_sr, speech_duration, total_silence = parse_and_generate_audio(
                    model, text_content, LANGUAGE, reference_audio_path, ref_text, VOICE_DESC
                )
                
                gong_total = (2 * len(gong_audio) / final_sr) if gong_audio is not None else 0.0
                
                initial_audio, _ = assemble_adjusted_audio(segments, final_sr, target_duration=None, gong_audio=gong_audio)
                initial_duration = len(initial_audio) / final_sr
                print(f"   📊 Raw: {speech_duration:.1f}s speech + {gong_total:.1f}s gong + {total_silence:.1f}s silence = {initial_duration:.1f}s total")
                
                if target_duration:
                    if abs(initial_duration - target_duration) > 1.5:
                        if total_silence > 0:
                            fixed_content = speech_duration + gong_total
                            needed_silence = target_duration - fixed_content
                            silence_factor = needed_silence / total_silence
                            
                            print(f"   🔧 Adjusting silences ×{silence_factor:.2f} to hit {target_duration:.0f}s")
                            final_audio, final_sr = assemble_adjusted_audio(segments, final_sr, target_duration, gong_audio=gong_audio)
                            duration = len(final_audio) / final_sr
                        else:
                            padding_duration = target_duration - initial_duration
                            padding_samples = int(padding_duration * final_sr)
                            
                            # Pad missing time with the same soft comfort noise floor
                            padding = np.random.normal(0, 0.00005, padding_samples).astype(np.float32)
                            final_audio = np.concatenate([initial_audio, padding])
                            duration = len(final_audio) / final_sr
                            print(f"   🔧 Padding with {padding_duration:.1f}s comfort noise at end")
                    else:
                        print(f"   ✅ Duration already matches target")
                        final_audio = initial_audio
                        duration = initial_duration
                else:
                    final_audio = initial_audio
                    duration = initial_duration
                
                print(f"   ✅ Final: {duration:.1f}s")
                
                combined_key = save_audio_to_r2(
                    r2_client, credentials['bucket_name'],
                    final_audio, final_sr, script_filename
                )
                
                if combined_key:
                    from datetime import date
                    new_entry = {
                        "duration": duration_str,
                        "level": level,
                        "variation": variation,
                        "model": MODEL_ID,
                        "date_generated": date.today().strftime("%Y-%m-%d"),
                        "music": "silence"
                    }
                    meditations_log["meditations"].append(new_entry)
                    upload_json_to_r2(
                        r2_client, credentials['bucket_name'],
                        "meditations/meditations_repo_log.json",
                        meditations_log
                    )
                    print(f"   🎉 Complete: {combined_key}")
                else:
                    print(f"   ❌ Failed to save audio for {script_filename}")
            
            print(f"\n{'='*60}")
            print(f"✅ Batch complete! Generated {len(missing)} new meditation(s).")
    
except NoCredentialsError:
    print("❌ Invalid R2 credentials")
except ClientError as e:
    print(f"❌ R2 Client Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")