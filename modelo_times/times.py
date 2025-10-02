import json
from moviepy.editor import VideoFileClip
import os

# ==============================================================================
# PARTE 1: LEER VIDEO Y DIVIDIRLO EN PARTES
# Esta función lee la duración real de un video y la divide en segmentos.
# ==============================================================================
def dividir_video_en_segmentos(ruta_del_video, numero_de_partes=4):
    times_between = 2
    """
    Lee la duración total de un video, la divide en el número de partes
    especificado y devuelve una lista de diccionarios con los tiempos de
    inicio y fin de cada segmento.
    """
    print(f"--- Analizando '{ruta_del_video}' para obtener su duración... ---")
    
    # Comprobar si el archivo de video existe
    if not os.path.exists(ruta_del_video):
        print(f"Error: El archivo de video no se encuentra en la ruta: {ruta_del_video}")
        return None

    try:
        # Cargar el video y obtener su duración total en segundos
        clip = VideoFileClip(ruta_del_video)
        duracion_total = clip.duration
        clip.close() # Es buena práctica cerrar el clip
        numero_de_partes = int(duracion_total/times_between)
        print(f"Duración total del video: {duracion_total:.2f} segundos.")
        
        # Calcular cuánto debe durar cada parte
        duracion_por_parte = duracion_total / numero_de_partes
        print(f"Dividiendo en {numero_de_partes} partes de {duracion_por_parte:.2f} segundos cada una.")
        
        lista_para_json = []
        tiempo_inicio_actual = 0
        
        # Crear un diccionario para cada una de las 4 partes
        for i in range(numero_de_partes):
            tiempo_fin_actual = tiempo_inicio_actual + duracion_por_parte
            
            # Formateo: Crear el diccionario para el segmento actual
            segmento = {
                "start_time": round(tiempo_inicio_actual, 2),
                "end_time": round(tiempo_fin_actual, 2)
            }
            lista_para_json.append(segmento)
            
            print(f"Segmento {i+1}: Inicio: {segmento['start_time']}s, Fin: {segmento['end_time']}s")
            
            # El inicio del siguiente segmento es el fin del actual
            tiempo_inicio_actual = tiempo_fin_actual
            
        print("-" * 60)
        return lista_para_json

    except Exception as e:
        print(f"Ocurrió un error al procesar el video: {e}")
        return None

# ==============================================================================
# PARTE 2: GUARDAR LOS RESULTADOS EN UN ARCHIVO JSON
# Esta función toma la lista de segmentos y la escribe en un archivo.
# ==============================================================================
def guardar_resultados_en_json(lista_de_segmentos, nombre_archivo_salida):
    """
    Toma la lista de segmentos y la guarda en un archivo JSON formateado.
    """
    if lista_de_segmentos is None:
        print("No se generó ningún segmento, no se creará el archivo JSON.")
        return

    print("--- Guardando los segmentos en un archivo JSON... ---")
    
    # Guardado: Escribir la lista en un archivo JSON
    with open(nombre_archivo_salida, 'w') as f:
        json.dump(lista_de_segmentos, f, indent=4)
        
    print("-" * 60)
    print(f"--- ¡Hecho! Se generó el archivo '{nombre_archivo_salida}' con los tiempos divididos. ---")
    print("se genero un csv se feliz") # Mensaje solicitado en el prompt original
    
# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    # IMPORTANTE: Reemplaza esta ruta con la ruta real de tu video.
    # Se recomienda usar rutas absolutas para evitar problemas.
    # Ejemplo Windows: "C:\\Users\\tu_usuario\\Videos\\mi_video.mp4"
    # Ejemplo Linux/Mac: "/home/tu_usuario/videos/mi_video.mp4"

    ruta_del_video_a_procesar = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_prueba2.mp4\prueba2.mp4"

    # 1. Obtenemos los segmentos de tiempo dividiendo el video
    segmentos_de_tiempo = dividir_video_en_segmentos(ruta_del_video_a_procesar, numero_de_partes=4)
    
    # 2. Guardamos esos segmentos en un archivo JSON
    nombre_archivo_json = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\modelo_times\resultado_final3.json"
    guardar_resultados_en_json(segmentos_de_tiempo, nombre_archivo_json)