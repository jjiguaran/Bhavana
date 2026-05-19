from openai import OpenAI
import os
import json
import time
from dotenv import load_dotenv
import boto3
from datetime import datetime
import uuid

# Load environment variables from .env file
load_dotenv()

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_KEY"),
  timeout=300.0,
)

# Possible values
LEVELS = ['principiante', 'intermedio', 'avanzado']
DURATIONS = [5, 10, 15, 20, 30, 45, 60]

MODEL_NAME = "openrouter/owl-alpha"

LOG_R2_KEY = "scripts/scripts_repo_log.json"
LOG_LOCAL_PATH = os.path.join(os.path.dirname(__file__), 'scripts_repo_log.json')

def get_s3_client():
    """Create and return an S3 client for Cloudflare R2"""
    return boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name='auto'
    )

def download_log_from_r2():
    """Download scripts_repo_log.json from R2 bucket (scripts/ directory)"""
    s3 = get_s3_client()
    bucket = os.getenv('R2_BUCKET_NAME')
    try:
        obj = s3.get_object(Bucket=bucket, Key=LOG_R2_KEY)
        content = obj['Body'].read().decode('utf-8')
        log_data = json.loads(content)
        if 'scripts' not in log_data:
            log_data['scripts'] = []
        return log_data
    except s3.exceptions.NoSuchKey:
        print("  Log file not found in R2, starting with empty log.")
        return {"scripts": []}
    except Exception as e:
        raise Exception(f"Failed to download log from R2: {e}")

def upload_log_to_r2(log_data):
    """Upload scripts_repo_log.json to R2 bucket (scripts/ directory)"""
    s3 = get_s3_client()
    bucket = os.getenv('R2_BUCKET_NAME')
    s3.put_object(
        Bucket=bucket,
        Key=LOG_R2_KEY,
        Body=json.dumps(log_data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )

def load_log():
    """Load the existing scripts_repo_log.json from R2 (with local fallback)"""
    # First try to load from R2
    try:
        return download_log_from_r2()
    except Exception:
        pass
    # Fallback: load from local file
    try:
        with open(LOG_LOCAL_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"scripts": []}

def save_log(log_data):
    """Save the scripts_repo_log.json locally and upload to R2"""
    # Save locally
    with open(LOG_LOCAL_PATH, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    # Upload to R2
    try:
        upload_log_to_r2(log_data)
    except Exception as e:
        print(f"  Warning: could not upload log to R2: {e}")

def build_existing_set(log_data):
    """Build a set of (duration_str, level, variation) tuples from the log"""
    existing = set()
    for entry in log_data['scripts']:
        existing.add((entry['duration'], entry['level'], entry['variation']))
    return existing

def generate_meditation(duration, level, variation, max_retries=3):
    """Call the LLM to generate a meditation script for the given duration and level with retry logic"""
    focus_options = [
        "Enfoque técnico y concentración (anclarse en la respiración, estabilidad)",
        "Enfoque en la autocompasión y ecuanimidad (paciencia con la mente errante, amabilidad, soltar la frustración)",
        "Enfoque en la relajación profunda y el cuerpo (soltar tensiones físicas, hundirse en la quietud, calma corporal)"
    ]

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": f"""
            Crea una meditación guiada cuya duración total (silencios + lectura) sea de {duration * 60} segundos, adaptada al nivel **{level}** (principiante, intermedio o avanzado), siguiendo la progresión del Anapanasati y el Satipatthana: respiración, cuerpo, sensaciones, mente y dhammas.

            Antes de escribir el texto, calcula internamente la duración total.

            Reglas estrictas:
            - La suma de todos los silencios + el tiempo estimado de lectura debe ser de {duration * 60} segundos.
            - Asume una velocidad de lectura meditativa de 90 palabras por minuto.
            - Ajusta la cantidad y duración de los silencios para no exceder el tiempo total.
            - No excedas el tiempo total bajo ninguna circunstancia.

            Según el nivel, el tiempo total dedicado a silencios debe ser aproximadamente:
            - Principiante: 30–40% del tiempo total
            - Intermedio: 40–55% del tiempo total
            - Avanzado: 55–70% del tiempo total

            Sigue estas pautas según el nivel:
            - Principiante: frases claras y frecuentes, silencios cortos (5–30 s), enfoque en la respiración y el cuerpo.
            - Intermedio: más espacio, lenguaje contemplativo, silencios medios (20–60 s), explorar mente y experiencia cambiante.
            - Avanzado: guía mínima y profunda, silencios largos (40–90 s), contemplación de impermanencia, desapego, disolución del yo.

            Matiz de esta variación específica:
            Para esta versión de la meditación, infunde un {focus_options[variation - 1]}. Elige palabras y recordatorios que apunten sutilmente a este estado mental, manteniendo siempre la estructura del Anapanasati y el Satipatthana requerida.

            No expliques ni traduzcas el contexto, ni menciones el budismo directamente. Guía solo desde la experiencia inmediata. Evita términos conceptuales.

            Usa frases cortas e íntimas en segunda persona (tú), seguidas por silencios entre corchetes. No uses viñetas, números, markdown ni símbolos.

            Ejemplo:
            Observa cómo entra y sale el aire
            [silencio: 10 segundos]

            Antes de entregar el texto final, verifica internamente que la duración total no exceda el tiempo indicado y ajusta silencios o texto si es necesario.

            No incluyas cálculos, verificaciones, conteos de palabras, explicaciones ni secciones de control en la salida final. Solo entrega el texto de la meditación.

            La salida final debe contener únicamente el texto de la meditación y los silencios entre corchetes.

            Asegúrate de que el texto esté escrito con corrección gramatical y ortográfica impecable en español.
    """
                    }
                ],
                extra_body={"reasoning": {"enabled": True}}
            )

            # Extract the assistant message (with reasoning_details)
            result = response.choices[0].message
            return result

        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = 2 ** attempt  # exponential backoff: 2, 4, 8 seconds
                print(f"\n  [RETRY {attempt}/{max_retries}] Error: {e}. Retrying in {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)

    # All retries exhausted
    raise last_error

def upload_to_r2(output_data, r2_filename):
    """Upload meditation JSON to Cloudflare R2"""
    s3_client = boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name='auto'
    )

    s3_client.put_object(
        Bucket=os.getenv('R2_BUCKET_NAME'),
        Key=r2_filename,
        Body=json.dumps(output_data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )

def save_meditation_files(duration, level, variation, response, meditation_id):
    """Save the meditation to R2 only"""
    r2_filename = f"scripts/{duration}_{level}_{variation}.json"
    output_data = {
        "meditation_content": response.content,
        "reasoning_details": getattr(response, 'reasoning_details', None),
        "model": MODEL_NAME,
        "timestamp": datetime.now().isoformat(),
        "id": meditation_id,
        "duration_minutes": duration,
        "level": level,
        "variation": variation
    }
    try:
        upload_to_r2(output_data, r2_filename)
        print(f"  Uploaded to R2: {r2_filename}")
    except Exception as e:
        print(f"  Error uploading to R2: {e}")

def main():
    print("=== Guided Meditation Script Generator ===")
    print(f"Generating missing meditations for all duration/level/variation combinations...")
    print()

    # Load existing log
    log_data = load_log()
    existing = build_existing_set(log_data)

    total_possible = len(DURATIONS) * len(LEVELS) * 3  # 3 variations
    generated_count = 0
    skipped_count = 0

    for duration in DURATIONS:
        for level in LEVELS:
            for variation in range(1, 4):
                duration_str = f"{duration} min"

                if (duration_str, level, variation) in existing:
                    print(f"[SKIP] {duration_str}, {level}, variation {variation} — already exists")
                    skipped_count += 1
                    continue

                print(f"[GENERATE] {duration_str}, {level}, variation {variation}...", end=" ", flush=True)

                try:
                    # Generate the meditation using the LLM
                    response = generate_meditation(duration, level, variation)

                    meditation_id = str(uuid.uuid4())
                    current_date = datetime.now().strftime("%Y-%m-%d")

                    # Save files locally and to R2
                    save_meditation_files(duration, level, variation, response, meditation_id)

                    # Update the log with the new entry
                    new_entry = {
                        "duration": duration_str,
                        "level": level,
                        "variation": variation,
                        "model": MODEL_NAME,
                        "date_generated": current_date
                    }
                    log_data['scripts'].append(new_entry)
                    save_log(log_data)

                    generated_count += 1
                    print(f"✓ Done (id: {meditation_id})")

                except Exception as e:
                    print(f"✗ Error: {e}")

    print()
    print("=== Summary ===")
    print(f"Total possible combinations: {total_possible}")
    print(f"Skipped (already exist):     {skipped_count}")
    print(f"Generated:                   {generated_count}")
    print(f"Remaining:                   {total_possible - skipped_count - generated_count}")

if __name__ == "__main__":
    main()