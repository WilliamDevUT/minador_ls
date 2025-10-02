import pandas as pd

# --- CONFIGURACIÓN ---
# Nombres de los archivos de entrada y salida.
# ¡Asegúrate de que tus archivos CSV se llamen así o cambia los nombres aquí!
NOMBRE_ARCHIVO_1 = r'C:\Users\willd\OneDrive\Documentos\my\congreso\minador\output\vid_simple.mp4\vid_simple.mp4_indice_completo_whisper.csv'
NOMBRE_ARCHIVO_2 = r'C:\Users\willd\OneDrive\Documentos\my\congreso\detecciones_senas.csv'
NOMBRE_ARCHIVO_SALIDA = 'validaciones_con_ventana_temporal.csv'

# Ventana de tiempo en segundos para buscar la palabra en la transcripción (hacia atrás).
SEGUNDOS_DE_BUSQUEDA_WHISPER = 4

# --- NUEVA REGLA ---
# Ventana de tiempo en segundos para considerar una detección como "consecutiva".
# Si la misma palabra se detecta después de este tiempo, se trata como una nueva detección.
SEGUNDOS_REPETICION_CONSECUTIVA = 4

# --- INICIO DEL SCRIPT ---

try:
    # 1. Leer los dos archivos CSV usando pandas.
    df_transcripcion = pd.read_csv(NOMBRE_ARCHIVO_1)
    df_detecciones = pd.read_csv(NOMBRE_ARCHIVO_2)

    print("Archivo 1 (transcripcion.csv) cargado correctamente.")
    print("Archivo 2 (detecciones.csv) cargado correctamente.\n")

except FileNotFoundError as e:
    print(f"Error: No se pudo encontrar el archivo '{e.filename}'.")
    print("Por favor, asegúrate de que los archivos CSV estén en la misma carpeta que el script y que los nombres sean correctos.")
    exit()


# 2. Limpieza y preparación de los datos.
df_transcripcion['palabra_limpia'] = df_transcripcion['palabra'].str.replace(r'[^\w\s]', '', regex=True).str.lower()
df_detecciones['palabra_limpia'] = df_detecciones['palabra_detectada'].str.lower()


# 3. Pre-procesamiento: Identificar "créditos" de palabras consecutivas en la transcripción.
pares_consecutivos_disponibles = []
for i in range(len(df_transcripcion) - 1):
    fila_actual = df_transcripcion.iloc[i]
    fila_siguiente = df_transcripcion.iloc[i+1]
    
    if fila_actual['palabra_limpia'] == fila_siguiente['palabra_limpia']:
        pares_consecutivos_disponibles.append({
            'palabra': fila_actual['palabra_limpia'],
            'tiempo_inicio': fila_actual['inicio'],
            'usado': False 
        })

print(f"Se encontraron {len(pares_consecutivos_disponibles)} pares de palabras consecutivas en la transcripción (Whisper).")
print("Estos se usarán como 'excepciones' para permitir detecciones consecutivas.\n")


# 4. Proceso de validación con la nueva lógica temporal.
filas_validadas = []
# --- MODIFICACIÓN: Ahora necesitamos guardar la palabra Y el tiempo de la última validación ---
ultima_palabra_validada = None
tiempo_ultima_validacion = -1.0 # Inicializamos en un valor negativo

print("Iniciando proceso de validación con reglas de consecutividad y ventana temporal...")

for index, deteccion in df_detecciones.iterrows():
    palabra_a_validar = deteccion['palabra_limpia']
    tiempo_deteccion = deteccion['tiempo_start']
    
    tiempo_inicio_busqueda = tiempo_deteccion - SEGUNDOS_DE_BUSQUEDA_WHISPER
    tiempo_fin_busqueda = tiempo_deteccion

    # Filtramos la transcripción en la ventana de tiempo.
    df_ventana_temporal = df_transcripcion[
        (df_transcripcion['inicio'] >= tiempo_inicio_busqueda) &
        (df_transcripcion['inicio'] <= tiempo_fin_busqueda)
    ]
    
    # Condición 1: La palabra DEBE estar presente en la ventana de tiempo de Whisper.
    if palabra_a_validar not in df_ventana_temporal['palabra_limpia'].values:
        print(f"  [FALLO] La palabra '{deteccion['palabra_detectada']}' no fue encontrada en la transcripción en el rango de tiempo [{tiempo_inicio_busqueda:.2f}s - {tiempo_fin_busqueda:.2f}s].")
        continue

    # --- INICIO DE LA LÓGICA MODIFICADA ---
    # Condición 2: Comprobar si es una detección consecutiva DENTRO de la ventana de tiempo permitida.
    es_deteccion_consecutiva_restringida = False
    if palabra_a_validar == ultima_palabra_validada:
        # Calculamos el tiempo transcurrido desde la última vez que validamos esta misma palabra.
        tiempo_desde_ultima = tiempo_deteccion - tiempo_ultima_validacion
        if tiempo_desde_ultima <= SEGUNDOS_REPETICION_CONSECUTIVA:
            # Solo si se cumplen AMBAS condiciones (misma palabra Y dentro del tiempo) se considera consecutiva.
            es_deteccion_consecutiva_restringida = True
    # --- FIN DE LA LÓGICA MODIFICADA ---

    validacion_final_exitosa = False
    
    if not es_deteccion_consecutiva_restringida:
        # Si NO es una detección consecutiva restringida, es válida.
        # Esto cubre dos casos:
        # 1. Es una palabra diferente a la anterior.
        # 2. Es la misma palabra, pero ya pasaron más de 4 segundos.
        validacion_final_exitosa = True
        print(f"  [ÉXITO] La palabra '{deteccion['palabra_detectada']}' fue validada en {tiempo_deteccion:.2f}s (es una nueva instancia).")
    else:
        # Si ES una detección consecutiva restringida, necesitamos usar un "crédito".
        print(f"  [INFO] Detección consecutiva de '{deteccion['palabra_detectada']}' dentro de los {SEGUNDOS_REPETICION_CONSECUTIVA}s. Buscando justificación...")
        
        # Buscamos en nuestra lista de pares un crédito que no hayamos usado.
        for par in pares_consecutivos_disponibles:
            if (par['palabra'] == palabra_a_validar and 
                not par['usado'] and
                tiempo_inicio_busqueda <= par['tiempo_inicio'] <= tiempo_fin_busqueda):
                
                print(f"          -> Justificación encontrada (par en transcripción a los {par['tiempo_inicio']:.2f}s). La detección es VÁLIDA.")
                par['usado'] = True
                validacion_final_exitosa = True
                break
        
        if not validacion_final_exitosa:
             print(f"          -> No se encontró justificación. La detección es INVÁLIDA.")

    # Si la validación final fue exitosa, añadimos la fila y actualizamos el estado.
    if validacion_final_exitosa:
        filas_validadas.append(deteccion)
        # --- MODIFICACIÓN: Actualizamos AMBOS valores para la siguiente iteración ---
        ultima_palabra_validada = palabra_a_validar
        tiempo_ultima_validacion = tiempo_deteccion


# 5. Creación y guardado del archivo de resultados.
if filas_validadas:
    df_resultado = pd.DataFrame(filas_validadas)
    columnas_finales = [col for col in df_detecciones.columns if col != 'palabra_limpia']
    df_resultado = df_resultado[columnas_finales]
    df_resultado.to_csv(NOMBRE_ARCHIVO_SALIDA, index=False)
    
    print(f"\nProceso completado. Se han encontrado {len(df_resultado)} validaciones correctas bajo las nuevas reglas.")
    print(f"Los resultados han sido guardados en el archivo '{NOMBRE_ARCHIVO_SALIDA}'.")
else:
    print("\nProceso completado. No se encontró ninguna coincidencia que validar con las nuevas reglas.")