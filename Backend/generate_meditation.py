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

        Usa el siguiente contexto (en inglés) como inspiración para crear una meditación guiada, siguiendo la **progresión contemplativa** que se encuentra en el Anapanasati y el Satipatthana: comenzando con la respiración, luego el cuerpo, las sensaciones, la mente y finalmente los dhammas (fenómenos mentales como el deseo, el apego o la impermanencia).

        La duración total de la meditación debe ser de aproximadamente **{duration} segundos**.

        El nivel de experiencia del practicante es **{nivel}**.

        **Adapta tanto la forma como el contenido de la meditación a este nivel**, considerando lo siguiente:

        - Si el nivel es *principiante*: utiliza frases claras, concretas y frecuentes. Los silencios deben ser más cortos (5–30 segundos). El enfoque debe estar en aspectos accesibles como la respiración, el cuerpo y las sensaciones simples.

        - Si el nivel es *intermedio*: deja más espacio entre instrucciones, usa lenguaje contemplativo y accesible, con silencios medios (20–60 segundos). Explora también los estados mentales y el flujo cambiante de la experiencia.

        - Si el nivel es *avanzado*: guía mínima y profunda, con silencios largos (40–90 segundos). Lleva la atención hacia fenómenos más sutiles como la impermanencia, el desapego, la disolución del yo y otros dhammas. Permite que la sabiduría emerja desde la experiencia misma, sin interferencias.

        No expliques los textos ni hables del budismo explícitamente. No traduzcas literalmente el contexto ni lo menciones. No des instrucciones técnicas o abstractas. Evitá términos conceptuales o filosóficos. Guía solamente desde la experiencia directa.

        Permite que el contenido específico de cada nivel surja de forma natural a partir del contexto entregado. Inspírate en la estructura y profundidad progresiva que se presenta en los textos fuente, sin imponer una lista fija de temas.

        Estructura la guía como un **script temporal**, con instrucciones breves seguidas de un silencio sugerido. Por ejemplo:

        Pon atención a cómo entra y sale el aire  
        [silencio: 10 segundos]

        Observa cómo se siente el cuerpo al respirar  
        [silencio: 30 segundos]

        La meditación debe avanzar de forma **progresiva**, desde el enfoque en la respiración hacia observaciones más amplias de sensaciones, estados mentales y fenómenos. Usa frases simples, pausadas, y permite que el silencio acompañe cada paso.

        ### Contexto (en inglés):
        {context}

        ### Guía guiada (script temporal) en español:
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
                segmentos.append(("texto", texto_previo))
            segmentos.append(("silencio", segundos))
        else:
            segmentos.append(("texto", linea))
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