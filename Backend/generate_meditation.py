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

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "buddhist_texts_mn"

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Kokoro configuration
KOKORO_MODEL = "mistral"  # Change this to your specific model



ollama_client = Client(host=OLLAMA_BASE_URL)
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
embedding_model = SentenceTransformer(EMBEDDING_MODEL) 

query= "give me a guided breath meditation step by step based on the anapanasati and the satipatana suttas that would lead me to insight"
query_embedding = embedding_model.encode(query).tolist()
results = client.search(
    collection_name=COLLECTION_NAME,
    query_vector=query_embedding,
    limit=5,
    with_payload=True   # top 5 most similar
)
context = "\n\n".join([r.payload.get("text", "") for r in results])



def generate_text(minutes, nivel):
    duration = minutes * 60
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
    response = ollama_client.chat(
        model="mistral",  # or "llama3", etc.
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return(response['message']['content'])


def generate_meditation(minutes, level, musica=False, path_binaural="../data/audio/simply-meditation-series-11hz-alpha-binaural-waves-for-relaxed-focus-8028.mp3"):
    # Generar texto de meditación
    meditation_text = generate_text(minutes, level)
    pipeline = KPipeline(lang_code='e')

    silencio_re = re.compile(r"\[silencio:\s*(\d+)\s*segundos?\]", re.IGNORECASE)

    audio_total = []

    for linea in meditation_text.strip().split('\n'):
        linea = linea.strip()
        if not linea:
            continue

        match = silencio_re.match(linea)

        if match:
            duracion_segundos = int(match.group(1))
            duracion_muestras = duracion_segundos * 24000  # 24kHz samplerate
            silencio = np.zeros(duracion_muestras, dtype=np.float32)
            audio_total.append(silencio)
        else:
            generator = pipeline(linea, voice="em_alex", speed=0.75)
            for _, _, audio in generator:
                audio_total.append(audio)

    # Concatenar el audio generado
    audio_final = np.concatenate(audio_total)

    # Guardado provisional si no se requiere música
    if not musica:
        output_path = f"../data/audio/meditacion_kokoro_{minutes}_{level}_mute.wav"
        sf.write(output_path, audio_final, samplerate=24000)
        return output_path

    # Si se requiere música, pasamos a AudioSegment para mezclar
    # Convertir el array numpy a WAV temporal en memoria
    
    temp_buffer = BytesIO()
    sf.write(temp_buffer, audio_final, samplerate=24000, format='WAV')
    temp_buffer.seek(0)
    meditacion = AudioSegment.from_file(temp_buffer, format="wav")

    # Cargar binaural y adaptar duración
    binaural = AudioSegment.from_file(path_binaural, format="mp3")
    duracion_meditacion = len(meditacion)

    if len(binaural) >= duracion_meditacion:
        binaural = binaural[:duracion_meditacion]
    else:
        repeticiones = duracion_meditacion // len(binaural) + 1
        binaural = (binaural * repeticiones)[:duracion_meditacion]

    # Ajustar volumen del binaural y mezclar
    binaural = binaural - 20
    mezcla = meditacion.overlay(binaural)

    # Guardar el archivo final
    output_path = f"../data/audio/meditacion_kokoro_{minutes}_{level}_con_musica.wav"
    mezcla.export(output_path, format="wav")

    return output_path


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(   description="Generate a meditation and return the output path.")
    parser.add_argument("minutes", type=int, help="The number of minutes for the meditation")
    parser.add_argument("nivel", type=str, help="The level of the practitioner (principiante, intermedio, avanzado)")
    parser.add_argument("musica", type=bool, help="Whether to include music in the meditation")
    parser.add_argument("path_binaural", type=str, help="The path to the binaural audio file")

    args = parser.parse_args()

    output_path = generate_meditation(args.minutes, args.nivel, args.musica, args.path_binaural)
    print(output_path)