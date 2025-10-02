import os
import csv
import yt_dlp
from groq import Groq
from pydub import AudioSegment
import json
from os import getenv
from dotenv import load_dotenv

load_dotenv()  # solo en dev




# ==== CONFIGURACIÓN ====
#YOUTUBE_URL = "https://youtu.be/nERLaE7m8rQ?si=BK833SWc5SUGw026"  # ← Cambia a tu video

GROQ_API_KEY = getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise RuntimeError('GROQ_API_KEY is required')
AUDIO_FILE = "audio.wav"
VIDEO_FILE = "video.mp4"
CSV_COMPLETO = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\whisper\indice_completo_whisper.csv"
CSV_CEREBRO = "palabras_descubiertas.csv"

#capeta donde están los videos a procesar
ruta_input = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\input" 

#carpeta donde se guardaran en forma de sub carpetas los audios, csv y videos procesados
ruta_output = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output"

# --- 2. Preparación del Entorno ---
# Nos aseguramos de que las carpetas base existan antes de empezar.
# Si no existen, las creamos. Si ya existen, no hacemos nada.

print("Preparando el entorno de trabajo...")
os.makedirs(ruta_input, exist_ok=True)
os.makedirs(ruta_output, exist_ok=True)

print("Entorno listo. Coloca los videos en la carpeta de origen y ejecuta el script.")


# ==== 1. Descargar video de YouTube ====
def descargar_video(url, nombre_archivo):
    print("[+] Descargando video...")
    ydl_opts = {
        'format': 'mp4/bestaudio/best',
        'outtmpl': nombre_archivo
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ==== 2. Extraer audio WAV ====
def extraer_audio(video_file, audio_file):
    print("[+] Extrayendo audio...")
    audio = AudioSegment.from_file(video_file)
    audio = audio.set_channels(1).set_frame_rate(16000)  # Mono y 16kHz para Whisper
    audio.export(audio_file, format="wav")

# ==== 3. Transcribir con Groq Whisper ====
def transcribir_whisper(audio_path):
    print("[+] Transcribiendo audio con Whisper en Groq...")
    client = Groq(api_key=GROQ_API_KEY)

    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )

    return transcription

# ==== 4. Convertir segmentos a palabras con timestamps ====
def segmentar_palabras(transcripcion):
    # Extraer palabras con tiempos
    print("[+] Segmentando palabras con timestamps...")
    # transformar la trasncripción en una lista de palabras con tiempos
    palabras_con_tiempo = []
    # cambiar el formato de la transcripción a una lista de palabras con tiempos con comando
    print(transcripcion)
    for segmento in transcripcion.segments:
        start = segmento["start"]
        end = segmento["end"]
        texto = segmento["text"].strip()

        # Dividir en palabras
        lista_palabras = texto.split()
        duracion_segmento = end - start
        duracion_por_palabra = duracion_segmento / len(lista_palabras)

        for i, palabra in enumerate(lista_palabras):
            inicio_palabra = start + i * duracion_por_palabra
            fin_palabra = inicio_palabra + duracion_por_palabra
            palabras_con_tiempo.append((round(inicio_palabra, 2), round(fin_palabra, 2), palabra))

    return palabras_con_tiempo

# ==== 5. Guardar CSV y actualizar cerebro ====
def guardar_csv_y_cerebro(palabras):
    # Cargar cerebro existente
    if os.path.exists(CSV_CEREBRO):
        with open(CSV_CEREBRO, "r", encoding="utf-8") as f:
            cerebro = set(line.strip() for line in f if line.strip())
    else:
        cerebro = set()

    nuevas_palabras = []

    # Guardar todas las palabras en CSV completo
    with open(CSV_COMPLETO, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["inicio", "fin", "palabra"])
        for inicio, fin, palabra in palabras:
            writer.writerow([inicio, fin, palabra])
            if palabra.lower() not in cerebro:
                nuevas_palabras.append(palabra.lower())

    # Actualizar cerebro
    if nuevas_palabras:
        with open(CSV_CEREBRO, "a", encoding="utf-8") as f:
            for palabra in nuevas_palabras:
                f.write(palabra + "\n")

    print(f"[+] Guardado {len(palabras)} palabras en {CSV_COMPLETO}")
    print(f"[+] {len(nuevas_palabras)} palabras nuevas añadidas a {CSV_CEREBRO}")

# ==== MAIN ====
if __name__ == "__main__":

    #descargar_video(YOUTUBE_URL, VIDEO_FILE)
    for i in os.listdir(ruta_input):

        if i.endswith(".mp4") or i.endswith(".mkv") or i.endswith(".avi") or i.endswith(".mov"):
            VIDEO_FILE = os.path.join(ruta_input, i)
            print(f"Procesando video: {VIDEO_FILE}")
            
            # guardar en los output los archivos correspondientes en forma de carpetas (vid_1: audio, csv, video)

            AUDIO_FILE = os.path.join(ruta_output, f"vid_{i}_audio.wav")
            CSV_COMPLETO = os.path.join(ruta_output, f"vid_{i}_indice_completo_whisper.csv")
            #CSV_CEREBRO = os.path.join(ruta_output, f"vid_{i}_palabras_descubiertas.csv")

            extraer_audio(VIDEO_FILE, AUDIO_FILE)
            transcripcion = transcribir_whisper(AUDIO_FILE)
            palabras = segmentar_palabras(transcripcion)
            guardar_csv_y_cerebro(palabras)
            print(f"[+] Procesamiento de {VIDEO_FILE} completado.\n")
            # una vez procesado el video, moverlo a una carpeta de procesados en forma de carpetas (vid_1: audio, csv, video)
            os.makedirs(os.path.join(ruta_output, f"vid_{i}"), exist_ok=True)
            os.rename(VIDEO_FILE, os.path.join(ruta_output, f"vid_{i}", i))
            os.rename(AUDIO_FILE, os.path.join(ruta_output, f"vid_{i}", f"vid_{i}_audio.wav"))
            os.rename(CSV_COMPLETO, os.path.join(ruta_output, f"vid_{i}", f"vid_{i}_indice_completo_whisper.csv"))
            #os.rename(CSV_CEREBRO, os.path.join(ruta_output, f"vid_{i}", f"vid_{i}_palabras_descubiertas.csv"))
            # fin del for
            # fin del for
# NOTA: el archivo CSV_CEREBRO es un archivo acumulativo,

# se usara este archivo como base para poder obtener las palabras y sus tiempos en el video

