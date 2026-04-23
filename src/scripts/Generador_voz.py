# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 21:33:04 2025

@author: danie
"""
import re
import numpy as np
import soundfile as sf
from kokoro import KPipeline


# Asumimos que ya está importado KPipeline y configurado
pipeline = KPipeline(lang_code='e')

with open(r'C:\Users\danie\Desktop\Meditacion\Salidas\Salidas de texto\Guia1_Gemma3_27b_k10promp2_1.txt', 'r', encoding='utf-8') as archivo:
    respuesta_llm = archivo.read()

# Texto de entrada desde el LLM
texto = respuesta_llm

# Patrón para detectar [Pausa X seg]
patron_pausa = re.compile(r"\[Pausa (\d+) segundos\]")

# Separar el texto en segmentos de narración y pausas
segmentos = patron_pausa.split(texto)

# Lista final de audio
audio_chunks = []

i = 0
while i < len(segmentos):
    if i % 2 == 0:
        # Texto narrado
        texto_segmento = segmentos[i].strip()
        if texto_segmento:
            generator = pipeline(texto_segmento, voice="em_alex", speed=0.7)
            for _, _, audio in generator:
                audio_chunks.append(audio)
    else:
        # Pausa en segundos
        segundos = int(segmentos[i])
        silencio = np.zeros(int(24000 * segundos), dtype=np.float32)
        audio_chunks.append(silencio)
    i += 1

# Concatenar todo el audio
audio_total = np.concatenate(audio_chunks)

# Guardar en archivo WAV
sf.write("voz_kokoro.wav", audio_total, samplerate=24000)


