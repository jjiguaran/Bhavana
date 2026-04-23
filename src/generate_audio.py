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

# ── Choose your model ──────────────────────────────────────────────────────
# Options:
#   "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"   ← preset voices + instruction control
#   "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"   ← describe any voice freely
#   "Qwen/Qwen3-TTS-12Hz-1.7B-Base"          ← voice cloning
#   "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"   ← lighter, faster
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
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
    """List all JSON files in the meditations directory"""
    try:
        response = r2_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='meditations/',
            Delimiter='/'
        )
        
        json_files = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith('.json') and key != 'meditations/':
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

def select_json_file(json_files):
    """Select the most recent JSON file or let user choose"""
    if not json_files:
        print("❌ No JSON files found in meditations directory")
        return None
    
    print(f"\n📁 Found {len(json_files)} JSON file(s) in meditations directory:")
    
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

def read_json_from_r2(r2_client, bucket_name, file_key):
    """Read JSON file from R2"""
    try:
        response = r2_client.get_object(Bucket=bucket_name, Key=file_key)
        json_content = response['Body'].read().decode('utf-8')
        return json.loads(json_content)
    except Exception as e:
        print(f"❌ Error reading JSON from R2: {e}")
        return None

def parse_and_generate_audio(model, content, language, voice_desc):
    """Parse meditation content and generate combined audio directly"""
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    audio_segments = []
    target_sr = 24000
    
    for line in lines:
        silence_match = re.match(r'\[silencio:\s*(\d+)\s*segundos?\]', line, re.IGNORECASE)
        if silence_match:
            # Create silence
            duration = int(silence_match.group(1))
            silence = np.zeros(duration * target_sr, dtype=np.float32)
            audio_segments.append(silence)
        else:
            # Generate TTS
            wavs, sr = model.generate_voice_design(
                text=line,
                language=language,
                instruct=voice_desc.strip(),
            )
            # Resample to target rate if needed
            if sr != target_sr:
                from scipy import signal
                resampled = signal.resample(wavs[0], int(len(wavs[0]) * target_sr / sr))
                audio_segments.append(resampled.astype(np.float32))
            else:
                audio_segments.append(wavs[0])
    
    return np.concatenate(audio_segments), target_sr

# Main workflow
try:
    # Get credentials and connect
    credentials = get_r2_credentials()
    r2_client = connect_to_r2(credentials)
    
    # Test connection
    print("🔗 Testing R2 connection...")
    r2_client.head_bucket(Bucket=credentials['bucket_name'])
    print("✅ R2 connection successful")
    
    # List and select JSON file from meditations directory
    print("\n🔍 Searching for JSON files in meditations directory...")
    json_files = list_json_files_in_meditations(r2_client, credentials['bucket_name'])
    json_file_key = select_json_file(json_files)
    
    if json_file_key:
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
            
            # Generate audio directly
            print("🎵 Generating audio...")
            final_audio, final_sr = parse_and_generate_audio(model, text_content, LANGUAGE, VOICE_DESC)
            
            duration = len(final_audio) / final_sr
            print(f"✅ Audio created: {duration:.1f} seconds")
            
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
        print("❌ No JSON file selected")
        
except NoCredentialsError:
    print("❌ Invalid R2 credentials")
except ClientError as e:
    print(f"❌ R2 Client Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

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

