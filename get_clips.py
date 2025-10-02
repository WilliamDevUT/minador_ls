import pandas as pd
from moviepy.editor import VideoFileClip
import os
import re

# --- CONFIGURACIÓN ---
# Archivos CSV
ARCHIVO_WHISPER = r'C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_video.mp4\vid_video.mp4_indice_completo_whisper.csv'
ARCHIVO_DETECCIONES = r'C:\Users\willd\OneDrive\Documentos\my\congreso\detecciones_senas.csv'

# Ruta del video fuente
VIDEO_FUENTE = r'C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_video.mp4\video.mp4'

# Carpetas de salida
CARPETA_VALIDACIONES = r'C:\Users\willd\OneDrive\Documentos\my\congreso\clips\validaciones'
CARPETA_DESCONOCIDO = r'C:\Users\willd\OneDrive\Documentos\my\congreso\clips\desconocido'
# Parámetros
SEGUNDOS_DE_BUSQUEDA = 10  # Ventana de búsqueda hacia atrás
SEGUNDOS_ADICIONALES_DESCONOCIDO = 5  # Segundos después del fin para clips desconocidos
import pandas as pd
from moviepy.editor import VideoFileClip
import os
import re

# --- CONFIGURACIÓN ---
# Archivos CSV
ARCHIVO_WHISPER = r'C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_video.mp4\vid_video.mp4_indice_completo_whisper.csv'
ARCHIVO_DETECCIONES = r'C:\Users\willd\OneDrive\Documentos\my\congreso\detecciones_senas.csv'

# Ruta del video fuente
VIDEO_FUENTE = r'C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_video.mp4\video.mp4'

# Carpetas de salida
CARPETA_VALIDACIONES = r'C:\Users\willd\OneDrive\Documentos\my\congreso\clips\validaciones'
CARPETA_DESCONOCIDO = r'C:\Users\willd\OneDrive\Documentos\my\congreso\clips\desconocido'


# Parámetros
SEGUNDOS_DE_BUSQUEDA = 10  # Ventana de búsqueda hacia atrás
SEGUNDOS_ADICIONALES_DESCONOCIDO = 5  # Segundos después del fin para clips desconocidos

# --- FUNCIONES AUXILIARES ---

def crear_carpeta_si_no_existe(ruta):
    """Crea una carpeta si no existe."""
    if not os.path.exists(ruta):
        os.makedirs(ruta)
        print(f"  [INFO] Carpeta creada: {ruta}")

def limpiar_nombre_archivo(nombre):
    """Limpia un string para que sea un nombre de archivo válido y lo convierte a minúsculas."""
    caracteres_invalidos = '<>:"/\\|?*'
    for char in caracteres_invalidos:
        nombre = nombre.replace(char, '_')
    # Eliminar espacios al inicio y final, y convertir a minúsculas
    nombre = nombre.strip().lower()
    # Eliminar comas al final
    nombre = nombre.rstrip(',')
    return nombre

def obtener_siguiente_numero_video(carpeta_destino):
    """
    Busca en la carpeta destino todos los archivos vid_N.mp4
    y devuelve el siguiente número disponible.
    """
    if not os.path.exists(carpeta_destino):
        return 1
    
    archivos = os.listdir(carpeta_destino)
    numeros_existentes = []
    
    # Patrón para buscar: vid_N.mp4
    patron = re.compile(r'vid_(\d+)\.mp4')
    
    for archivo in archivos:
        match = patron.match(archivo)
        if match:
            numero = int(match.group(1))
            numeros_existentes.append(numero)
    
    if numeros_existentes:
        return max(numeros_existentes) + 1
    else:
        return 1

def cortar_clip(video_path, inicio, fin, carpeta_destino):
    """
    Corta un clip de video desde inicio hasta fin y lo guarda como vid_N.mp4
    """
    try:
        # Obtener el siguiente número de video disponible
        numero_vid = obtener_siguiente_numero_video(carpeta_destino)
        
        # Construir el nombre del archivo simple: vid_N.mp4
        nombre_archivo = f"vid_{numero_vid}.mp4"
        ruta_salida = os.path.join(carpeta_destino, nombre_archivo)
        
        with VideoFileClip(video_path) as video:
            duracion_video = video.duration
            
            # Ajustar tiempos si exceden la duración del video
            if inicio >= duracion_video:
                print(f"  [ERROR] Tiempo de inicio ({inicio:.2f}s) excede la duración del video ({duracion_video:.2f}s)")
                return False
            
            if fin > duracion_video:
                print(f"  [AVISO] Tiempo de fin ajustado de {fin:.2f}s a {duracion_video:.2f}s")
                fin = duracion_video
            
            # Cortar y guardar clip
            clip = video.subclip(inicio, fin)
            clip.write_videofile(ruta_salida, codec="libx264", audio_codec="aac", verbose=False, logger=None)
            print(f"  [CLIP GUARDADO] {nombre_archivo}")
            return True
            
    except Exception as e:
        print(f"  [ERROR] No se pudo cortar el clip: {e}")
        return False

# --- INICIO DEL SCRIPT ---

print("=" * 80)
print("VALIDADOR Y CORTADOR DE CLIPS DE VIDEO")
print("=" * 80)

# 1. Verificar que el video fuente existe
if not os.path.exists(VIDEO_FUENTE):
    print(f"\n[ERROR CRÍTICO] No se encontró el video fuente: {VIDEO_FUENTE}")
    print("Por favor, actualiza la ruta VIDEO_FUENTE en el script.")
    exit()

# 2. Cargar archivos CSV
try:
    df_whisper = pd.read_csv(ARCHIVO_WHISPER)
    df_detecciones = pd.read_csv(ARCHIVO_DETECCIONES)
    print("\n[OK] Archivos CSV cargados correctamente")
    print(f"  - Transcripciones Whisper: {len(df_whisper)} palabras")
    print(f"  - Detecciones de señas: {len(df_detecciones)} detecciones")
except FileNotFoundError as e:
    print(f"\n[ERROR] No se pudo encontrar el archivo: {e.filename}")
    exit()

# 3. Limpiar datos para comparación
df_whisper['palabra_limpia'] = df_whisper['palabra'].str.replace(r'[^\w\s]', '', regex=True).str.lower()
df_detecciones['palabra_limpia'] = df_detecciones['palabra_detectada'].str.lower()

# 4. Crear carpetas principales
crear_carpeta_si_no_existe(CARPETA_VALIDACIONES)
crear_carpeta_si_no_existe(CARPETA_DESCONOCIDO)

# 5. PROCESO DE VALIDACIÓN Y CORTE DE CLIPS
print("\n" + "=" * 80)
print("INICIANDO PROCESO DE VALIDACIÓN Y CORTE")
print("=" * 80)

validaciones_exitosas = 0
validaciones_fallidas = 0
palabras_restantes_procesadas = 0

for index, deteccion in df_detecciones.iterrows():
    palabra_detectada = deteccion['palabra_detectada']
    palabra_limpia = deteccion['palabra_limpia']
    tiempo_start = deteccion['tiempo_start']
    tiempo_fin = deteccion['tiempo_fin']
    
    print(f"\n[{index + 1}/{len(df_detecciones)}] Procesando: '{palabra_detectada}' ({tiempo_start:.2f}s - {tiempo_fin:.2f}s)")
    
    # Definir ventana de búsqueda
    tiempo_inicio_busqueda = tiempo_start - SEGUNDOS_DE_BUSQUEDA
    tiempo_fin_busqueda = tiempo_start
    
    # Filtrar transcripciones en la ventana temporal
    df_ventana = df_whisper[
        (df_whisper['inicio'] >= tiempo_inicio_busqueda) &
        (df_whisper['inicio'] <= tiempo_fin_busqueda)
    ]
    
    # Verificar si la palabra está en la transcripción
    palabra_validada = palabra_limpia in df_ventana['palabra_limpia'].values
    
    if palabra_validada:
        # PALABRA VALIDADA
        print(f"  [✓ VALIDADA] Encontrada en transcripción")
        validaciones_exitosas += 1
        
        # Crear carpeta para la palabra validada
        nombre_carpeta = limpiar_nombre_archivo(palabra_detectada)
        carpeta_palabra = os.path.join(CARPETA_VALIDACIONES, nombre_carpeta)
        crear_carpeta_si_no_existe(carpeta_palabra)
        
        # Cortar clip con numeración automática
        cortar_clip(VIDEO_FUENTE, tiempo_start, tiempo_fin, carpeta_palabra)
        
    else:
        # PALABRA NO VALIDADA (DESCONOCIDA)
        print(f"  [✗ NO VALIDADA] No encontrada en rango [{tiempo_inicio_busqueda:.2f}s - {tiempo_fin_busqueda:.2f}s]")
        validaciones_fallidas += 1
        
        # Buscar qué palabra REAL estaba en ese momento en el Whisper
        df_palabra_real = df_whisper[
            (df_whisper['inicio'] <= tiempo_start) &
            (df_whisper['fin'] >= tiempo_start)
        ]
        
        # Si encontramos la palabra real en ese tiempo
        if len(df_palabra_real) > 0:
            palabra_real = df_palabra_real.iloc[0]['palabra']
            print(f"  [INFO] Palabra real en ese momento: '{palabra_real}'")
            
            # Crear carpeta con la palabra REAL del Whisper
            nombre_carpeta = limpiar_nombre_archivo(palabra_real)
            carpeta_palabra = os.path.join(CARPETA_DESCONOCIDO, nombre_carpeta)
            
            # Si la carpeta ya existe, solo informamos
            if os.path.exists(carpeta_palabra):
                print(f"  [INFO] Carpeta '{nombre_carpeta}' ya existe, agregando clip...")
            else:
                crear_carpeta_si_no_existe(carpeta_palabra)
            
        else:
            # Si no encontramos palabra en ese momento, usar "sin_palabra"
            print(f"  [AVISO] No se encontró ninguna palabra en el Whisper en el tiempo {tiempo_start:.2f}s")
            nombre_carpeta = "sin_palabra"
            carpeta_palabra = os.path.join(CARPETA_DESCONOCIDO, nombre_carpeta)
            crear_carpeta_si_no_existe(carpeta_palabra)
        
        # Calcular tiempos del clip (desde tiempo_fin hasta tiempo_fin + 5 segundos)
        clip_inicio = tiempo_fin
        clip_fin = tiempo_fin + SEGUNDOS_ADICIONALES_DESCONOCIDO
        
        print(f"  [INFO] Cortando clip desconocido: {clip_inicio:.2f}s - {clip_fin:.2f}s")
        
        # Cortar clip con numeración automática
        cortar_clip(VIDEO_FUENTE, clip_inicio, clip_fin, carpeta_palabra)

# 6. CONTINUAR CON LAS PALABRAS RESTANTES DEL WHISPER
print("\n" + "=" * 80)
print("PROCESANDO PALABRAS RESTANTES DEL WHISPER (después de la última detección)")
print("=" * 80)

# Encontrar el tiempo de la última detección
if len(df_detecciones) > 0:
    tiempo_ultima_deteccion = df_detecciones['tiempo_fin'].max()
    print(f"\nÚltima detección terminó en: {tiempo_ultima_deteccion:.2f}s")
    
    # Filtrar palabras del Whisper que están después de la última detección
    df_palabras_restantes = df_whisper[df_whisper['inicio'] >= tiempo_ultima_deteccion].copy()
    
    if len(df_palabras_restantes) > 0:
        print(f"Palabras restantes por procesar: {len(df_palabras_restantes)}")
        
        for index, fila_whisper in df_palabras_restantes.iterrows():
            palabra_real = fila_whisper['palabra']
            tiempo_inicio = fila_whisper['inicio']
            tiempo_fin = fila_whisper['fin']
            
            print(f"\n[{palabras_restantes_procesadas + 1}/{len(df_palabras_restantes)}] Procesando palabra restante: '{palabra_real}' ({tiempo_inicio:.2f}s - {tiempo_fin:.2f}s)")
            
            # Crear carpeta con la palabra real
            nombre_carpeta = limpiar_nombre_archivo(palabra_real)
            carpeta_palabra = os.path.join(CARPETA_DESCONOCIDO, nombre_carpeta)
            
            # Si la carpeta ya existe, solo informamos
            if os.path.exists(carpeta_palabra):
                print(f"  [INFO] Carpeta '{nombre_carpeta}' ya existe, agregando clip...")
            else:
                crear_carpeta_si_no_existe(carpeta_palabra)
            
            # Calcular tiempos del clip (desde tiempo_fin hasta tiempo_fin + 5 segundos)
            clip_inicio = tiempo_fin
            clip_fin = tiempo_fin + SEGUNDOS_ADICIONALES_DESCONOCIDO
            
            print(f"  [INFO] Cortando clip: {clip_inicio:.2f}s - {clip_fin:.2f}s")
            
            # Cortar clip con numeración automática
            if cortar_clip(VIDEO_FUENTE, clip_inicio, clip_fin, carpeta_palabra):
                palabras_restantes_procesadas += 1
        
        print(f"\nPalabras restantes procesadas: {palabras_restantes_procesadas}")
    else:
        print("\nNo hay palabras restantes después de la última detección.")
else:
    print("\nNo había detecciones para procesar.")

# 7. RESUMEN FINAL
print("\n" + "=" * 80)
print("PROCESO COMPLETADO")
print("=" * 80)
print(f"Total de detecciones procesadas: {len(df_detecciones)}")
print(f"  - Validaciones exitosas: {validaciones_exitosas}")
print(f"  - Validaciones fallidas (desconocidas): {validaciones_fallidas}")
print(f"Palabras restantes del Whisper procesadas: {palabras_restantes_procesadas}")
print(f"\nClips guardados en:")
print(f"  - Validadas: {CARPETA_VALIDACIONES}")
print(f"  - Desconocidas: {CARPETA_DESCONOCIDO}")
print("=" * 80)