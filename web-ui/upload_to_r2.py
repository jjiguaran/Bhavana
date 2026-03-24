#!/usr/bin/env python3
"""
Script to upload meditation files to Cloudflare R2
Requires: pip install boto3
"""

import os
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cloudflare R2 configuration from environment
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

def upload_to_r2():
    """Upload all meditation audio files to Cloudflare R2"""
    
    # Check required environment variables
    required_vars = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return
    
    # Initialize S3 client for R2
    s3_client = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name='auto'
    )
    
    # Upload directory
    audio_dir = Path("public/data")
    
    # Upload all .wav files (except test files)
    for file_path in audio_dir.glob("*.wav"):
        if file_path.name.startswith("meditacion_kokoro_test"):
            continue
            
        print(f"Uploading {file_path.name}...")
        
        try:
            s3_client.upload_file(
                str(file_path),
                R2_BUCKET_NAME,
                file_path.name,
                ExtraArgs={
                    'ContentType': 'audio/wav',
                    'CacheControl': 'max-age=31536000', # Cache for 1 year
                    'Metadata': {
                        'minutes': str(file_path.stem.split('_')[2]),
                        'level': file_path.stem.split('_')[3],
                        'music': 'con_musica' if 'con_musica' in file_path.name else 'mute'
                    }
                }
            )
            print(f"✅ Uploaded {file_path.name}")
            
        except Exception as e:
            print(f"❌ Failed to upload {file_path.name}: {e}")
    
    print("\nUpload complete! 🎵")
    print(f"Files available at: https://{R2_BUCKET_NAME}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com")

if __name__ == "__main__":
    upload_to_r2()
