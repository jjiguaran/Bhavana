# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 12:31:39 2025

@author: danie
"""

import os
import pandas as pd
import numpy as np
import regex as re
import requests
import time
from tqdm import tqdm
import re
import uuid
from pathlib import Path
import requests



# LangChain imports
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# from langchain.schema import Document
# from langchain.vectorstores import Chroma

# --- Configuración (DEBE COINCIDIR CON LA CONFIGURACIÓN DE TU CÓDIGO ANTERIOR) ---
MODEL_NAME = "all-mpnet-base-v2" # Modelo de embedding usado para generar los embeddings
CHROMA_PERSIST_DIR = r"C:\Users\danie\Desktop\Meditacion\Salidas\Base de datos vectorial" # Directorio donde Chroma guarda la DB
OLLAMA_MODEL = "gemma3:27b" # TU MODELO DE OLLAMA
TOP_K = 50
duracion_minutos = 5



inicio = time.time()

# Paso 1: Cargar embeddings y vectorstore existente
embedding_model = HuggingFaceEmbeddings(model_name=MODEL_NAME)

print("Cargando base de datos vectorial desde Chroma...")
vectorstore = Chroma(
    persist_directory=CHROMA_PERSIST_DIR,
    embedding_function=embedding_model
)

# Paso 2: Instrucción principal para el LLM
duracion_minutos = 5
palabras_esperadas = duracion_minutos * 150
pregunta_usuario = (
    f"Eres un guía de meditación con profundo conocimiento de las enseñanzas budistas. "
    f"Usa el siguiente contexto (en inglés) como fuente de inspiración para crear una guía de meditación paso a paso. "
    f"Escríbela completamente en español, con un tono calmado, contemplativo, suave y claro. "
    f"No traduzcas literalmente el contexto ni lo menciones directamente. "
    f"La guía debe estar diseñada para ser narrada en voz alta, con una extensión aproximada de {palabras_esperadas} palabras. "
    f"Divide el texto en secciones breves, con frases cortas y comprensibles. "
    f"Al final de cada sección, incluye una pausa sugerida en el formato: [Pausa X segundos], donde X debe estar entre 3 y 12 segundos. "
    f"La duración total estimada del texto completo con pausas debe ser de aproximadamente {duracion_minutos} minutos. "
    f"No uses más de 10 pausas de más de 10 segundos. "
    f"Evita pausas excesivamente largas o innecesarias. "
    f"Utiliza silencios y respiraciones conscientes como herramienta para la calma, sin exagerar. "
    f"El objetivo es lograr una experiencia pausada pero fluida, sin estancamientos. "
    f"Escribe solo la guía de meditación, sin explicaciones externas ni avisos."
)

# Promp de Pruebas 
# pregunta_usuario = (
#     "Eres un guía de meditación con profundo conocimiento de las enseñanzas budistas. "
#     "Usa el siguiente contexto (en inglés) como fuente de inspiración para crear una guía de meditación paso a paso. "
#     "Escríbela completamente en **español**, usando un tono **calmado, contemplativo, suave y claro**. "
#     "Evita traducir literalmente el contexto. No lo menciones directamente. "
#     "Escribe la guía como si fuera a ser narrada en audio durante aproximadamente **dos minutos**. "
#     "Divide el texto en **secciones cortas**, cada una con una **pausa sugerida al final** (por ejemplo: “[pausa]”, “[silencio]”, o “[respira profundamente]”). "
#     "Haz frases breves y utiliza silencios sugeridos, respiraciones conscientes y un ritmo pausado. "
#     "La estructura debe permitir que el oyente escuche con calma, respire con conciencia y se relaje gradualmente. "
#     "El objetivo es una experiencia clara, pausada y meditativa."
# )

# Paso 3: Buscar los textos más similares
resultados = vectorstore.similarity_search(pregunta_usuario, k=TOP_K)
contexto = "\n\n".join([r.page_content for r in resultados])

# Paso 4: Crear el prompt para el LLM
def crear_prompt_con_contexto(pregunta, contexto):
    return (
        f"A continuación tienes un contexto basado en textos de meditación:\n\n"
        f"{contexto}\n\n"
        f"Basado en el contexto anterior, responde la siguiente pregunta de forma clara y útil:\n"
        f"{pregunta}\n\n"
        f"Respuesta:"
    )

prompt_final = crear_prompt_con_contexto(pregunta_usuario, contexto)

# Paso 5: Enviar prompt a Ollama
def consultar_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": OLLAMA_MODEL,  # Reemplaza con el modelo que tienes cargado en Ollama
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()['response'].strip()
        else:
            return f"ERROR {response.status_code}: {response.text}"
    except Exception as e:
        return f"EXCEPTION: {str(e)}"

# Paso 6: Ejecutar y mostrar
respuesta_llm = consultar_ollama(prompt_final)
print("\n=== RESPUESTA DEL LLM ===")
print(respuesta_llm)



ruta_salida = r"C:\Users\danie\Desktop\Meditacion\Salidas\Salidas de texto\guia_meditacion1.txt"

with open(ruta_salida, "w", encoding="utf-8") as f:
    f.write(respuesta_llm)