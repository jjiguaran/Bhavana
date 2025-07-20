import numpy as np
from sentence_transformers import SentenceTransformer
from ollama import Client
from IPython.display import Audio
from kokoro import KPipeline
import soundfile as sf
import re
from qdrant_client import QdrantClient
from io import BytesIO
from pydub import AudioSegment
import argparse
import logging
import language_tool_python
from meditation_cache import get_or_generate_text, ensure_collection


# Configure logging (do this once, at the top-level of your main file)
logging.basicConfig(
    level=logging.INFO,  # Or DEBUG for more verbosity
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

ensure_collection()

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "buddhist_texts_mn"

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Kokoro configuration
KOKORO_MODEL = "mistral"  # Change this to your specific model


sample_rate = 24000
ollama_client = Client(host=OLLAMA_BASE_URL)
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
embedding_model = SentenceTransformer(EMBEDDING_MODEL) 
tool = language_tool_python.LanguageTool('es')

def generate_text(minutes, nivel):
    duration = minutes * 60

    query = f"guided meditation based on anapanasati and satipatthana, {minutes} minutes, level {nivel}"
    query_embedding = embedding_model.encode(query).tolist()


    def ollama_generate():

        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=5,
            with_payload=True
        )
        context = "\n\n".join([r.payload.get("text", "") for r in results])
        prompt = f"""
        Eres un guía de meditación con profundo conocimiento de las enseñanzas budistas.

        Crea una meditación guiada de aproximadamente {duration} segundos, adaptada al nivel **{nivel}** (principiante, intermedio o avanzado), siguiendo la progresión del **Anapanasati y el Satipatthana**: respiración, cuerpo, sensaciones, mente y dhammas.

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

        ### Contexto:
        {context}

        ### Meditación:
        """
        logger.info("Step 1: Generating text with Ollama")
        response = ollama_client.chat(
            model="mistral",  # or "llama3", etc.
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        logger.info("Step 2: Text generated successfully")
        return(response['message']['content'])

    return get_or_generate_text(query, nivel, duration, generate_fn=ollama_generate)


def corregir_texto(texto):
    matches = tool.check(texto)
    return language_tool_python.utils.correct(texto, matches)

def parsear_meditacion(texto):
    silencio_re = re.compile(r"\[silencio:\s*(\d+)\s*segundos?\]", re.IGNORECASE)
    segmentos = []

    for linea in texto.strip().split('\n'):
        linea = linea.strip()
        if not linea:
            continue

        match = silencio_re.search(linea)
        if match:
            segundos = int(match.group(1))
            texto_previo = silencio_re.sub('', linea).strip()
            if texto_previo:
                texto_corregido = corregir_texto(texto_previo)
                segmentos.append(("texto", texto_corregido))
            segmentos.append(("silencio", segundos))
        else:
            texto_corregido = corregir_texto(linea)
            segmentos.append(("texto", texto_corregido))

    return segmentos

def generar_audio_segmentos(segmentos, pipeline):
    audio_texto = []
    dur_texto_muestras = 0
    dur_silencios_segundos = 0
    for tipo, contenido in segmentos:
        if tipo == 'texto':
            logger.info(f"Generando audio para texto: {contenido}")
            generator = pipeline(contenido, voice="em_alex", speed=0.75)
            audio = np.concatenate([audio for _, _, audio in generator])
            audio_texto.append(audio)
            dur_texto_muestras += len(audio)
        elif tipo == 'silencio':
            dur_silencios_segundos += contenido
    return audio_texto, dur_texto_muestras, dur_silencios_segundos

def ajustar_silencios_y_reconstruir(segmentos, audio_texto, dur_texto_muestras, dur_silencios_segundos, duracion_deseada_segundos):
    audio_total = []
    index_texto = 0
    factor = 1.0
    if dur_silencios_segundos > 0:
        factor = max(0.0, (duracion_deseada_segundos - (dur_texto_muestras / sample_rate)) / dur_silencios_segundos)
    logger.info(f"Factor de ajuste de silencios: {factor:.3f}")

    for tipo, contenido in segmentos:
        if tipo == 'texto':
            audio_total.append(audio_texto[index_texto])
            index_texto += 1
        elif tipo == 'silencio':
            muestras = int(contenido * factor * sample_rate)
            logger.info(f"Insertando silencio ajustado: {muestras/sample_rate:.2f} segundos")
            audio_total.append(np.zeros(muestras, dtype=np.float32))

    return np.concatenate(audio_total)

def mezclar_con_musica(audio_np, path_binaural):
    buffer = BytesIO()
    sf.write(buffer, audio_np, samplerate=sample_rate, format='WAV')
    buffer.seek(0)
    meditacion = AudioSegment.from_file(buffer, format="wav")

    binaural = AudioSegment.from_file(path_binaural, format="mp3")
    if len(binaural) < len(meditacion):
        binaural = (binaural * (len(meditacion) // len(binaural) + 1))[:len(meditacion)]
    else:
        binaural = binaural[:len(meditacion)]

    binaural = binaural - 20  # reducir volumen
    return meditacion.overlay(binaural)

def guardar_audio(audio_np, path):
    sf.write(path, audio_np, samplerate=sample_rate)

def generate_meditation(minutes, level, musica=False, path_binaural="../data/audio/simply-meditation-series-11hz-alpha-binaural-waves-for-relaxed-focus-8028.mp3"):
    texto = generate_text(minutes, level)
    segmentos = parsear_meditacion(texto)
    pipeline = KPipeline(lang_code='e')

    audio_texto, dur_texto_muestras, dur_silencios_segundos = generar_audio_segmentos(segmentos, pipeline)
    audio_final = ajustar_silencios_y_reconstruir(segmentos, audio_texto, dur_texto_muestras, dur_silencios_segundos, minutes * 60)

    if not musica:
        output = f"../data/audio/meditacion_kokoro_{minutes}_{level}_mute.wav"
        guardar_audio(audio_final, output)
        return output
    else:
        mezcla = mezclar_con_musica(audio_final, path_binaural)
        output = f"../data/audio/meditacion_kokoro_{minutes}_{level}_con_musica.wav"
        mezcla.export(output, format="wav")
        return output


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(   description="Generate a meditation and return the output path.")
    parser.add_argument("minutes", type=int, help="The number of minutes for the meditation")
    parser.add_argument("nivel", type=str, help="The level of the practitioner (principiante, intermedio, avanzado)")
    parser.add_argument("musica", type=bool, help="Whether to include music in the meditation")
    parser.add_argument("path_binaural", type=str, help="The path to the binaural audio file")

    args = parser.parse_args()

    output_path = generate_meditation(args.minutes, args.nivel, args.musica, args.path_binaural)
    print(output_path)