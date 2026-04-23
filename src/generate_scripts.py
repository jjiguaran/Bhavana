from openai import OpenAI
import os
import json
from dotenv import load_dotenv
import boto3
from datetime import datetime
import uuid

# Load environment variables from .env file
load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_KEY"),
)

# First API call with reasoning
response = client.chat.completions.create(
  model="stepfun/step-3.5-flash:free",
  messages=[
          {
            "role": "user",
            "content": """
       Crea una meditación guiada de aproximadamente 900 segundos, adaptada al nivel **principiante** (principiante, intermedio o avanzado), siguiendo la progresión del **Anapanasati y el Satipatthana**: respiración, cuerpo, sensaciones, mente y dhammas.

        Sigue estas pautas según el nivel:

        - *Principiante*: frases claras y frecuentes, silencios cortos (5–30 s), enfoque en la respiración y el cuerpo.
        - *Intermedio*: más espacio, lenguaje contemplativo, silencios medios (20–60 s), explorar mente y experiencia cambiante.
        - *Avanzado*: guía mínima y profunda, silencios largos (40–90 s), contemplación de impermanencia, desapego, disolución del yo.

        No expliques ni traduzcas el contexto, ni menciones el budismo directamente. Guía solo desde la experiencia inmediata. Evita términos conceptuales.

        Usa frases cortas e íntimas en segunda persona (tú), seguidas por silencios entre corchetes. No uses viñetas, números, markdown ni símbolos.

        Ejemplo:
        Observa cómo entra y sale el aire  
        [silencio: 10 segundos]

        Asegúrate de que el texto esté escrito con corrección gramatical y ortográfica impecable en español.
"""
          }
        ],
  extra_body={"reasoning": {"enabled": True}}
)

# Extract the assistant message with reasoning_details
response = response.choices[0].message

# Save response to JSON file
output_data = {
    "meditation_content": response.content,
    "reasoning_details": getattr(response, 'reasoning_details', None),
    "model": "stepfun/step-3.5-flash:free",
    "timestamp": datetime.now().isoformat(),
    "id": str(uuid.uuid4())
}

# Save locally first
local_filename = "meditation_output.json"
with open(local_filename, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

# Upload to Cloudflare R2
try:
    # Initialize S3 client for Cloudflare R2
    s3_client = boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name='auto'
    )
    
    # Generate unique filename for R2
    r2_filename = f"meditations/{output_data['id']}.json"
    
    # Upload to R2
    s3_client.put_object(
        Bucket=os.getenv('R2_BUCKET_NAME'),
        Key=r2_filename,
        Body=json.dumps(output_data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )
    
    print(f"Meditation saved locally to {local_filename}")
    print(f"Meditation uploaded to R2: {r2_filename}")
    
except Exception as e:
    print(f"Error uploading to R2: {e}")
    print(f"Meditation saved locally to {local_filename}")