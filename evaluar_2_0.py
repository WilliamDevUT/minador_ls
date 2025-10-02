import json
import os
import cv2
import numpy as np
import csv
from datetime import datetime
from mediapipe.python.solutions.holistic import Holistic
from keras.models import load_model
from helpers import *
from constants import *


def interpolate_keypoints(keypoints, target_length=15):
    """Interpola keypoints para alcanzar la longitud objetivo."""
    current_length = len(keypoints)
    if current_length == target_length:
        return keypoints
    
    indices = np.linspace(0, current_length - 1, target_length)
    interpolated_keypoints = []
    for i in indices:
        lower_idx = int(np.floor(i))
        upper_idx = int(np.ceil(i))
        weight = i - lower_idx
        if lower_idx == upper_idx:
            interpolated_keypoints.append(keypoints[lower_idx])
        else:
            interpolated_point = (1 - weight) * np.array(keypoints[lower_idx]) + weight * np.array(keypoints[upper_idx])
            interpolated_keypoints.append(interpolated_point.tolist())
    
    return interpolated_keypoints

def normalize_keypoints(keypoints, target_length=15):
    """Normaliza la longitud de los keypoints."""
    current_length = len(keypoints)
    if current_length < target_length:
        return interpolate_keypoints(keypoints, target_length)
    elif current_length > target_length:
        step = current_length / target_length
        indices = np.arange(0, current_length, step).astype(int)[:target_length]
        return [keypoints[i] for i in indices]
    else:
        return keypoints

def draw_status(frame, status, current_time_s, intervalo, last_prediction="N/A", confidence=0.0):
    """Dibuja el estado actual del procesamiento en el frame."""
    h, w, _ = frame.shape
    # Fondo semitransparente
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 110), (0, 0, 0), -1)
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Información a mostrar
    tiempo_str = f"Tiempo Video: {current_time_s:.2f}s"
    intervalo_str = f"Segmento: [{intervalo['start_time']:.2f}s - {intervalo['end_time']:.2f}s]"
    status_str = f"Estado: {status}"
    pred_str = f"Ultima Prediccion: {last_prediction}"
    conf_str = f"Confianza: {confidence:.2f}%" if confidence > 0 else ""
    
    cv2.putText(frame, tiempo_str, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, intervalo_str, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, status_str, (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 255, 50), 2)
    cv2.putText(frame, pred_str, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 200, 255), 2)
    
    if conf_str:
        cv2.putText(frame, conf_str, (w - 200, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 50), 2)
    
    return frame

def save_to_csv(csv_path, detection_data):
    """Guarda los datos de detección en un archivo CSV."""
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['tiempo_start', 'tiempo_fin', 'palabra_detectada', 'confianza']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for data in detection_data:
            writer.writerow(data)
    print(f"\nResultados guardados en: {csv_path}")

# ===================================================================================
# NUEVA VERSIÓN DE LA FUNCIÓN - REEMPLAZAR LA ANTIGUA POR ESTA
# ===================================================================================
def procesar_video_por_segmentos(video_path, json_path, output_csv_path=None, 
                                threshold=0.8, show_visualization=True):
    """
    Procesa un video grabando keypoints DURANTE TODO el intervalo del JSON.
    La detección ya no depende de si hay manos o no, sino de los tiempos exactos del JSON.
    """
    
    # Preparar path de salida CSV
    if output_csv_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv_path = f"detecciones_{timestamp}.csv"
    
    # Cargar recursos
    print("Cargando modelo y configuración...")
    word_ids = get_word_ids(WORDS_JSON_PATH)
    model = load_model(MODEL_PATH)
    
    # Cargar intervalos de tiempo del JSON
    with open(json_path, 'r') as f:
        intervalos = json.load(f)
    print(f"Se procesarán {len(intervalos)} intervalos definidos por el JSON.")
    
    all_detections = []
    
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"Error al abrir el video: '{video_path}'")
        return None
    
    fps = video.get(cv2.CAP_PROP_FPS)
    print(f"FPS del video: {fps}")
    
    with Holistic() as holistic_model:
        # Procesar cada intervalo del JSON uno por uno
        for idx_intervalo, intervalo in enumerate(intervalos):
            start_time = intervalo['start_time']
            end_time = intervalo['end_time']
            
            print(f"\n[Intervalo {idx_intervalo+1}/{len(intervalos)}] "
                  f"Grabando keypoints de {start_time:.2f}s a {end_time:.2f}s")
            
            # Mover el video al inicio del segmento
            video.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
            
            # Lista para guardar los keypoints de ESTE segmento
            kp_seq_intervalo = []
            
            # Bucle para leer fotogramas solo dentro del intervalo
            while video.isOpened():
                current_time_s = video.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                
                # Si ya nos pasamos del tiempo final del intervalo, paramos de leer
                if current_time_s > end_time:
                    break
                
                ret, frame = video.read()
                if not ret:
                    break
                height, width, _ = frame.shape

                # Define las coordenadas para la esquina inferior derecha
                # (la mitad derecha y la mitad inferior del fotograma)
                
                start_row = int(height * (1 - 0.5))
                end_row = height
                start_col =  int(width * (1 - 0.25))
                end_col = width 

                # Recorta el fotograma para obtener solo la parte inferior derecha
                frame = frame[start_row:end_row, start_col:end_col]
                
                # --- LÓGICA SIMPLIFICADA ---
                # Ya no esperamos a ver manos. Extraemos keypoints en CADA fotograma del intervalo.
                results = mediapipe_detection(frame, holistic_model)
                kp_frame = extract_keypoints(results)
                kp_seq_intervalo.append(kp_frame)
                
                # Visualización (opcional)
                if show_visualization:
                    frame_display = draw_status(frame, "GRABANDO SEGMENTO", current_time_s, intervalo)
                    draw_keypoints(frame_display, results)
                    cv2.imshow('Detector de Señas por Segmentos', frame_display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nProceso interrumpido por el usuario.")
                break
            
            # --- PREDICCIÓN AL FINALIZAR EL INTERVALO ---
            # Una vez que hemos recopilado TODOS los keypoints del intervalo, hacemos la predicción.
            if len(kp_seq_intervalo) > 0:
                # Normalizar la secuencia de keypoints a la longitud que el modelo espera
                kp_normalized = normalize_keypoints(kp_seq_intervalo, int(MODEL_FRAMES))
                
                # Realizar la predicción
                res = model.predict(np.expand_dims(kp_normalized, axis=0))[0]
                
                max_idx = np.argmax(res)
                confidence = res[max_idx] * 100
                
                if confidence > threshold * 100:
                    word_id = word_ids[max_idx].split('-')[0]
                    palabra_detectada = words_text.get(word_id, f"palabra_{max_idx}")
                    
                    # Guardar la detección con los tiempos del JSON
                    detection = {
                        'tiempo_start': round(start_time, 2),
                        'tiempo_fin': round(end_time, 2),
                        'palabra_detectada': palabra_detectada,
                        'confianza': round(confidence, 2)
                    }
                    all_detections.append(detection)
                    
                    print(f"  ✓ Detectado: '{palabra_detectada}' con Confianza: {confidence:.2f}%")
                    
                    # Text to speech (opcional)
                    
                else:
                    print(f"  ✗ No se superó el umbral de confianza ({confidence:.2f}%)")
    #cerrar si oprimo q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nProceso interrumpido por el usuario.")
            
    # Limpiar recursos y guardar resultados

                video.release()
                cv2.destroyAllWindows()
    
    if all_detections:
        save_to_csv(output_csv_path, all_detections)
        print(f"\nTotal de detecciones: {len(all_detections)}")
        print("\nResumen de detecciones:")
        print("-" * 60)
        for det in all_detections:
            print(f"{det['tiempo_start']:6.2f}s - {det['tiempo_fin']:6.2f}s | "
                  f"{det['palabra_detectada']:15s} | Confianza: {det['confianza']:6.2f}%")
    else:
        print("\nNo se realizaron detecciones que superaran el umbral de confianza.")
    
    return output_csv_path    
    # Limpiar recursos
    

if __name__ == "__main__":
    # Configuración de rutas
    VIDEO_PATH = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_video.mp4\video.mp4"
    JSON_PATH = r"C:\Users\willd\OneDrive\Documentos\my\congreso\minador\modelo_times\resultado_final.json"
    OUTPUT_CSV = "detecciones_senas.csv"
    
    # Crear archivo JSON de ejemplo si no existe
    if not os.path.exists(JSON_PATH):
        print("Creando archivo JSON de ejemplo...")
        sample_data = [
            {"start_time": 2.0, "end_time": 5.5},
            {"start_time": 7.0, "end_time": 10.0},
            {"start_time": 12.0, "end_time": 15.0},
            {"start_time": 17.0, "end_time": 20.0}
        ]
        with open(JSON_PATH, 'w') as f:
            json.dump(sample_data, f, indent=4)
        print(f"Archivo JSON creado en: {JSON_PATH}")
    
    # Ejecutar procesamiento
    print("=" * 60)
    print("DETECTOR DE SEÑAS POR SEGMENTOS")
    print("=" * 60)
    
    resultado_csv = procesar_video_por_segmentos(
        video_path=VIDEO_PATH,
        json_path=JSON_PATH,
        output_csv_path=OUTPUT_CSV,
        threshold=0.8,
        show_visualization=True
    )
    
    if resultado_csv:
        print(f"\n✓ Proceso completado. Resultados en: {resultado_csv}")
    else:
        print("\n✗ El proceso no se completó correctamente")