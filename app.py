"""
Aplicación Flask para análisis de ubicaciones de nuevas sucursales.
Carga datos de clientes desde CSV, permite filtrar por sucursal,
visualizar en mapa interactivo y analizar distancias a puntos propuestos.
"""

from flask import Flask, render_template, request, jsonify, send_file
import logging
import pandas as pd
import numpy as np
from io import StringIO
import os
from services.distance import calculate_distance_km

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Variables globales para almacenar DataFrames

clientes_df = None
clientes_excluidos_df = None  # Clientes fuera de rango
sucursales_df = None  # Coordenadas de sucursales reales


def cargar_datos_clientes():
    """
    Carga el CSV de clientes y procesa las coordenadas.
    Separa la columna 'Coordenadas' en 'lat' y 'lon' numéricas.
    """
    global clientes_df, clientes_excluidos_df
    csv_path = os.path.join('data', 'clientes.csv')
    
    try:
        # Leer CSV con punto y coma como delimitador
        df = pd.read_csv(csv_path, sep=';')
        
        logger.info("Archivo CSV leído: %d filas", len(df))
        logger.debug("Columnas: %s", df.columns.tolist())
        
        # Procesar columna Coordenadas: "(-23.65129,-70.38372)" -> lat, lon
        def extraer_coordenadas(coord_str):
            try:
                # Convertir a string por si acaso
                coord_str = str(coord_str).strip()
                # Eliminar paréntesis y espacios
                coord_str = coord_str.replace('(', '').replace(')', '').replace(' ', '')
                # Separar por coma
                lat_str, lon_str = coord_str.split(',')
                return float(lat_str), float(lon_str)
            except Exception as e:
                logger.debug("Error procesando coordenada '%s': %s", coord_str, e)
                return np.nan, np.nan
        
        # Aplicar extracción de coordenadas
        df[['lat', 'lon']] = df['Coordenadas'].apply(
            lambda x: pd.Series(extraer_coordenadas(x))
        )
        
        # Eliminar filas con coordenadas inválidas
        df = df.dropna(subset=['lat', 'lon'])

        # Filtro: Chile continental (lat entre -56 y -17, lon entre -76 y -66)
        filtro_chile = (
            (df['lat'] >= -56) & (df['lat'] <= -17) &
            (df['lon'] >= -76) & (df['lon'] <= -66)
        )
        clientes_df = df[filtro_chile].copy()
        clientes_excluidos_df = df[~filtro_chile].copy()

        logger.info("Clientes válidos: %d", len(clientes_df))
        logger.info("Clientes excluidos (fuera de Chile): %d", len(clientes_excluidos_df))
        # Evitar imprimir listas o coordenadas exactas en logs por privacidad
        logger.debug("Sucursales disponibles (count): %d", clientes_df['Sucursal'].nunique())
        logger.debug("Rango de coordenadas - Lat min/max: %s, Lon min/max: %s",
                 f"{clientes_df['lat'].min():.2f}/{clientes_df['lat'].max():.2f}",
                 f"{clientes_df['lon'].min():.2f}/{clientes_df['lon'].max():.2f}")
        
    except FileNotFoundError:
        logger.warning("No se encontró el archivo %s", csv_path)
        logger.debug("Ubicación esperada: %s", os.path.abspath(csv_path))
        # Crear DataFrame vacío con columnas esperadas
        clientes_df = pd.DataFrame(columns=[
            'Sucursal', 'Cod Local', 'Local', 'Tipo Cliente', 
            'Frec SAP', 'Propuesta Frec', 'Propuesta ZR', 
            'Tipo Desviación', 'Cod ZR', 'Zona Reparto', 
            'Coordenadas', 'lat', 'lon'
        ])
    except Exception as e:
        logger.exception("ERROR inesperado cargando datos: %s", e)
        # Crear DataFrame vacío con columnas esperadas
        clientes_df = pd.DataFrame(columns=[
            'Sucursal', 'Cod Local', 'Local', 'Tipo Cliente', 
            'Frec SAP', 'Propuesta Frec', 'Propuesta ZR', 
            'Tipo Desviación', 'Cod ZR', 'Zona Reparto', 
            'Coordenadas', 'lat', 'lon'
        ])


def cargar_datos_sucursales():
    """
    Carga el Excel de sucursales y procesa las coordenadas.
    Formato esperado: columnas 'Sucursal' y 'Coordenadas'.
    """
    global sucursales_df
    excel_path = os.path.join('data', 'Sucursales.xlsx')
    
    try:
        df = pd.read_excel(excel_path)
        
        logger.info("Excel de sucursales leído: %d filas", len(df))
        logger.debug("Columnas sucursales: %s", df.columns.tolist())
        
        # Procesar columna Coordenadas
        def extraer_coordenadas(coord_str):
            try:
                coord_str = str(coord_str).strip()
                coord_str = coord_str.replace('(', '').replace(')', '').replace(' ', '')
                lat_str, lon_str = coord_str.split(',')
                return float(lat_str), float(lon_str)
            except Exception as e:
                logger.debug("Error procesando coordenada de sucursal '%s': %s", coord_str, e)
                return np.nan, np.nan
        
        df[['lat', 'lon']] = df['Coordenadas'].apply(
            lambda x: pd.Series(extraer_coordenadas(x))
        )
        
        df = df.dropna(subset=['lat', 'lon'])
        sucursales_df = df
        
        logger.info("Sucursales cargadas: %d", len(sucursales_df))
        logger.debug("Sucursales disponibles (count): %d", sucursales_df['Sucursal'].nunique())
        
    except FileNotFoundError:
        logger.warning("No se encontró el archivo %s", excel_path)
        sucursales_df = pd.DataFrame(columns=['Sucursal', 'Coordenadas', 'lat', 'lon'])
    except Exception as e:
        logger.exception("ERROR cargando sucursales: %s", e)
        sucursales_df = pd.DataFrame(columns=['Sucursal', 'Coordenadas', 'lat', 'lon'])


# --- Upload endpoint for clientes (temporary, in-memory) ---
ALLOWED_CLIENTES_EXT = {'.csv'}


@app.route('/upload_clientes', methods=['POST'])
def upload_clientes():
    """Recibe un archivo CSV de clientes, lo procesa en memoria y reemplaza los datos activos temporalmente.
    No guarda el archivo en el repositorio para evitar que se incluya en GitHub.
    """
    global clientes_df, clientes_excluidos_df

    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo en la petición (field name "file" requerido)'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_CLIENTES_EXT:
        return jsonify({'error': 'Extensión de archivo no permitida. Use .csv'}), 400

    try:
        # Leer CSV directamente desde el objeto FileStorage
        # Intentamos con separador ';' por compatibilidad con el maestro original
        df = pd.read_csv(file, sep=';')

        # Procesar columna Coordenadas
        def extraer_coordenadas(coord_str):
            try:
                coord_str = str(coord_str).strip()
                coord_str = coord_str.replace('(', '').replace(')', '').replace(' ', '')
                lat_str, lon_str = coord_str.split(',')
                return float(lat_str), float(lon_str)
            except Exception:
                return np.nan, np.nan

        df[['lat', 'lon']] = df['Coordenadas'].apply(lambda x: pd.Series(extraer_coordenadas(x)))
        df = df.dropna(subset=['lat', 'lon'])

        # Filtrar Chile continental
        filtro_chile = (
            (df['lat'] >= -56) & (df['lat'] <= -17) &
            (df['lon'] >= -76) & (df['lon'] <= -66)
        )
        clientes_df = df[filtro_chile].copy()
        clientes_excluidos_df = df[~filtro_chile].copy()

        return jsonify({
            'ok': True,
            'message': 'Archivo de clientes procesado en memoria correctamente.',
            'total': len(clientes_df),
            'excluidos': len(clientes_excluidos_df)
        })
    except Exception as e:
        return jsonify({'error': f'Error procesando archivo: {e}'}), 500


# --- NUEVO: Función para sugerir punto óptimo (geometric median) ---
def calcular_punto_optimo_sucursal(sucursal):
    """
    Calcula el punto óptimo para ubicar la sucursal usando el geometric median (Weiszfeld algorithm).
    Este punto minimiza la suma de distancias a todos los clientes.
    Retorna lat, lon del óptimo o None si no hay clientes.
    """
    global clientes_df
    df = clientes_df[clientes_df['Sucursal'] == sucursal]
    if len(df) == 0:
        return None, None
    
    # Extraer coordenadas
    coords = df[['lat', 'lon']].values
    
    # Si hay un solo cliente, el óptimo es ese cliente
    if len(coords) == 1:
        return float(coords[0][0]), float(coords[0][1])
    
    # Iniciar con el centroide como estimación inicial
    punto_actual = coords.mean(axis=0)
    
    # Algoritmo de Weiszfeld para encontrar el geometric median
    max_iteraciones = 100
    tolerancia = 1e-6
    
    for _ in range(max_iteraciones):
        # Calcular distancias desde punto actual a cada cliente
        distancias = np.sqrt(np.sum((coords - punto_actual) ** 2, axis=1))
        
        # Evitar división por cero
        distancias = np.where(distancias < 1e-8, 1e-8, distancias)
        
        # Calcular pesos inversamente proporcionales a las distancias
        pesos = 1.0 / distancias
        suma_pesos = pesos.sum()
        
        # Calcular nuevo punto como promedio ponderado
        punto_nuevo = (coords.T @ pesos) / suma_pesos
        
        # Verificar convergencia
        if np.linalg.norm(punto_nuevo - punto_actual) < tolerancia:
            break
        
        punto_actual = punto_nuevo
    
    return float(punto_actual[0]), float(punto_actual[1])


# --- NUEVO: Endpoint para sugerir punto óptimo ---
@app.route('/api/sugerir_optimo')
def api_sugerir_optimo():
    sucursal = request.args.get('sucursal', '')
    if not sucursal:
        return jsonify({'error': 'Parámetro sucursal requerido'}), 400
    lat_opt, lon_opt = calcular_punto_optimo_sucursal(sucursal)
    if lat_opt is None or lon_opt is None:
        return jsonify({'error': 'No hay clientes para esta sucursal'}), 404
    return jsonify({
        'sucursal': sucursal,
        'lat_optimo': round(lat_opt, 6),
        'lon_optimo': round(lon_opt, 6)
    })


# --- NUEVO: Endpoint para obtener ubicación de sucursal real ---
@app.route('/api/sucursal_ubicacion')
def api_sucursal_ubicacion():
    global sucursales_df
    sucursal = request.args.get('sucursal', '')
    if not sucursal:
        return jsonify({'error': 'Parámetro sucursal requerido'}), 400
    if sucursales_df is None or len(sucursales_df) == 0:
        return jsonify({'error': 'No hay datos de sucursales'}), 404
    
    suc_data = sucursales_df[sucursales_df['Sucursal'] == sucursal]
    if len(suc_data) == 0:
        return jsonify({'error': f'Sucursal {sucursal} no encontrada'}), 404
    
    return jsonify({
        'sucursal': sucursal,
        'lat': float(suc_data.iloc[0]['lat']),
        'lon': float(suc_data.iloc[0]['lon'])
    })


# --- NUEVO: Endpoint para consultar clientes excluidos por coordenadas ---
@app.route('/api/clientes_excluidos')
def api_clientes_excluidos():
    global clientes_excluidos_df
    # Devuelve los clientes excluidos por estar fuera de Chile continental
    if clientes_excluidos_df is None or len(clientes_excluidos_df) == 0:
        return jsonify({'excluidos': [], 'total': 0})
    excluidos = clientes_excluidos_df[[
        'Cod Local', 'Local', 'Sucursal', 'Zona Reparto', 'lat', 'lon'
    ]].to_dict('records')
    return jsonify({'excluidos': excluidos, 'total': len(excluidos)})


@app.route('/')
def index():
    """
    Página principal de la aplicación.
    Renderiza el template con la lista de sucursales disponibles.
    """
    # Si no hay datos cargados aún, enviar lista vacía
    if clientes_df is None or len(clientes_df) == 0:
        sucursales = []
    else:
        sucursales = sorted(clientes_df['Sucursal'].unique().tolist())
    return render_template('index.html', sucursales=sucursales)


@app.route('/api/clientes_por_sucursal')
def api_clientes_por_sucursal():
    """
    Endpoint GET que devuelve los clientes filtrados por sucursal.
    Query param: sucursal (string)
    Retorna: JSON con lista de clientes y sus coordenadas.
    """
    sucursal = request.args.get('sucursal', '')
    
    if not sucursal:
        return jsonify({'error': 'Parámetro sucursal requerido'}), 400
    
    # Filtrar clientes por sucursal
    clientes_filtrados = clientes_df[
        clientes_df['Sucursal'] == sucursal
    ].copy()
    
    if len(clientes_filtrados) == 0:
        return jsonify({'clientes': []})
    
    # Preparar datos para el frontend
    clientes_list = clientes_filtrados[[
        'Cod Local', 'Local', 'Sucursal', 
        'Zona Reparto', 'lat', 'lon'
    ]].to_dict('records')
    
    return jsonify({
        'clientes': clientes_list,
        'total': len(clientes_list)
    })


@app.route('/api/analisis_punto', methods=['POST'])
def api_analisis_punto():
    """
    Endpoint POST que analiza un punto propuesto como nueva sucursal.
    Recibe: JSON con sucursal, lat_click, lon_click, costo_km
    Calcula distancias de todos los clientes de la sucursal al punto.
    Retorna: JSON con estadísticas y detalle por cliente.
    """
    data = request.get_json()
    
    sucursal = data.get('sucursal')
    lat_click = data.get('lat_click')
    lon_click = data.get('lon_click')
    costo_km = data.get('costo_km', 0)
    
    # Validar parámetros
    if not all([sucursal, lat_click is not None, lon_click is not None]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
    
    try:
        lat_click = float(lat_click)
        lon_click = float(lon_click)
        costo_km = float(costo_km)
    except ValueError:
        return jsonify({'error': 'Valores numéricos inválidos'}), 400
    
    # Filtrar clientes por sucursal
    clientes_filtrados = clientes_df[
        clientes_df['Sucursal'] == sucursal
    ].copy()
    
    if len(clientes_filtrados) == 0:
        return jsonify({'error': 'No hay clientes para esta sucursal'}), 404
    
    # Calcular distancias usando el módulo de distancia
    # HOY: Haversine (modo por defecto)
    # MAÑANA: se puede cambiar a mode="osrm" cuando esté implementado
    distancias_km = calculate_distance_km(
        clientes_filtrados, 
        lat_click, 
        lon_click, 
        mode="haversine"
    )
    
    # Agregar distancias al DataFrame filtrado
    clientes_filtrados['distancia_km'] = distancias_km
    clientes_filtrados['costo_estimado'] = distancias_km * costo_km
    
    # Calcular estadísticas básicas
    distancia_promedio = float(distancias_km.mean())
    distancia_minima = float(distancias_km.min())
    distancia_maxima = float(distancias_km.max())
    numero_clientes = len(clientes_filtrados)
    costo_promedio = distancia_promedio * costo_km
    
    # --- NUEVAS MÉTRICAS: Comparación con sucursal real y óptimo ---
    metricas_comparativas = {}
    
    # Obtener coordenadas de sucursal real
    if sucursales_df is not None and len(sucursales_df) > 0:
        suc_real = sucursales_df[sucursales_df['Sucursal'] == sucursal]
        if len(suc_real) > 0:
            lat_real = float(suc_real.iloc[0]['lat'])
            lon_real = float(suc_real.iloc[0]['lon'])
            
            # Calcular distancias de clientes a sucursal real
            distancias_real = calculate_distance_km(
                clientes_filtrados, lat_real, lon_real, mode="haversine"
            )
            distancia_promedio_real = float(distancias_real.mean())
            costo_promedio_real = distancia_promedio_real * costo_km
            
            # Distancia entre punto consultado y sucursal real
            from services.distance import haversine_km
            dist_consultado_real = haversine_km(lat_click, lon_click, lat_real, lon_real)
            
            # Clientes más cercanos a cada ubicación
            clientes_mas_cerca_consultado = int((distancias_km < distancias_real).sum())
            clientes_mas_cerca_real = numero_clientes - clientes_mas_cerca_consultado
            
            # Mejora/empeoramiento
            mejora_distancia = distancia_promedio_real - distancia_promedio
            mejora_porcentaje = (mejora_distancia / distancia_promedio_real * 100) if distancia_promedio_real > 0 else 0
            ahorro_costo = costo_promedio_real - costo_promedio
            
            metricas_comparativas['sucursal_real'] = {
                'lat': lat_real,
                'lon': lon_real,
                'distancia_promedio_actual': round(distancia_promedio_real, 2),
                'costo_promedio_actual': round(costo_promedio_real, 2),
                'distancia_consultado_a_real': round(float(dist_consultado_real), 2),
                'clientes_mas_cerca_consultado': clientes_mas_cerca_consultado,
                'clientes_mas_cerca_real': clientes_mas_cerca_real,
                'porcentaje_mejora_consultado': round((clientes_mas_cerca_consultado / numero_clientes * 100), 1),
                'mejora_distancia_km': round(mejora_distancia, 2),
                'mejora_porcentaje': round(mejora_porcentaje, 1),
                'ahorro_costo_promedio': round(ahorro_costo, 2)
            }
    
    # Obtener coordenadas del óptimo sugerido
    lat_optimo, lon_optimo = calcular_punto_optimo_sucursal(sucursal)
    if lat_optimo is not None:
        # Calcular distancias de clientes al óptimo
        distancias_optimo = calculate_distance_km(
            clientes_filtrados, lat_optimo, lon_optimo, mode="haversine"
        )
        distancia_promedio_optimo = float(distancias_optimo.mean())
        costo_promedio_optimo = distancia_promedio_optimo * costo_km
        
        # Distancia entre punto consultado y óptimo
        from services.distance import haversine_km
        dist_consultado_optimo = haversine_km(lat_click, lon_click, lat_optimo, lon_optimo)
        
        # Comparación consultado vs óptimo
        # Si distancia_promedio > distancia_promedio_optimo → peor (diferencia positiva)
        # Si distancia_promedio < distancia_promedio_optimo → mejor (diferencia negativa)
        clientes_mas_cerca_consultado_vs_optimo = int((distancias_km < distancias_optimo).sum())
        diferencia_vs_optimo = distancia_promedio - distancia_promedio_optimo
        diferencia_porcentaje_vs_optimo = (diferencia_vs_optimo / distancia_promedio_optimo * 100) if distancia_promedio_optimo > 0 else 0
        
        metricas_comparativas['optimo_sugerido'] = {
            'lat': round(lat_optimo, 6),
            'lon': round(lon_optimo, 6),
            'distancia_promedio_optimo': round(distancia_promedio_optimo, 2),
            'costo_promedio_optimo': round(costo_promedio_optimo, 2),
            'distancia_consultado_a_optimo': round(float(dist_consultado_optimo), 2),
            'clientes_mas_cerca_consultado': clientes_mas_cerca_consultado_vs_optimo,
            'clientes_mas_cerca_optimo': numero_clientes - clientes_mas_cerca_consultado_vs_optimo,
            'diferencia_vs_optimo_km': round(diferencia_vs_optimo, 2),
            'diferencia_vs_optimo_porcentaje': round(diferencia_porcentaje_vs_optimo, 1)
        }
        
        # Si tenemos ambos (real y óptimo), calcular distancia entre ellos
        if 'sucursal_real' in metricas_comparativas:
            lat_real = metricas_comparativas['sucursal_real']['lat']
            lon_real = metricas_comparativas['sucursal_real']['lon']
            dist_optimo_real = haversine_km(lat_optimo, lon_optimo, lat_real, lon_real)
            metricas_comparativas['distancia_optimo_a_real'] = round(float(dist_optimo_real), 2)
    
    # Generar tabla detallada
    detalle_clientes = clientes_filtrados[[
        'Cod Local', 'Local', 'Sucursal', 
        'Zona Reparto', 'lat', 'lon', 
        'distancia_km', 'costo_estimado'
    ]].to_dict('records')
    
    # Redondear valores para presentación
    for cliente in detalle_clientes:
        cliente['distancia_km'] = round(cliente['distancia_km'], 2)
        cliente['costo_estimado'] = round(cliente['costo_estimado'], 2)
    
    # Preparar respuesta
    response = {
        'sucursal': sucursal,
        'lat_click': lat_click,
        'lon_click': lon_click,
        'distancia_promedio': round(distancia_promedio, 2),
        'distancia_minima': round(distancia_minima, 2),
        'distancia_maxima': round(distancia_maxima, 2),
        'numero_clientes': numero_clientes,
        'costo_km': costo_km,
        'costo_promedio': round(costo_promedio, 2),
        'metricas_comparativas': metricas_comparativas,
        'detalle_clientes': detalle_clientes
    }
    
    return jsonify(response)


@app.route('/export_detalle_csv')
def export_detalle_csv():
    """
    Endpoint GET que exporta el detalle del análisis como CSV descargable.
    Query params: sucursal, lat, lon, costo_km
    Retorna: archivo CSV con el detalle de distancias por cliente.
    """
    sucursal = request.args.get('sucursal', '')
    lat_str = request.args.get('lat', '')
    lon_str = request.args.get('lon', '')
    costo_km_str = request.args.get('costo_km', '0')
    
    # Validar parámetros
    if not all([sucursal, lat_str, lon_str]):
        return "Parámetros incompletos", 400
    
    try:
        lat_click = float(lat_str)
        lon_click = float(lon_str)
        costo_km = float(costo_km_str)
    except ValueError:
        return "Valores numéricos inválidos", 400
    
    # Filtrar clientes por sucursal
    clientes_filtrados = clientes_df[
        clientes_df['Sucursal'] == sucursal
    ].copy()
    
    if len(clientes_filtrados) == 0:
        return "No hay clientes para esta sucursal", 404
    
    # Calcular distancias (modo haversine)
    distancias_km = calculate_distance_km(
        clientes_filtrados, 
        lat_click, 
        lon_click, 
        mode="haversine"
    )
    
    # Agregar distancias y costos
    clientes_filtrados['distancia_km'] = distancias_km.round(2)
    clientes_filtrados['costo_estimado'] = (distancias_km * costo_km).round(2)
    
    # Seleccionar columnas para exportar
    df_export = clientes_filtrados[[
        'Cod Local', 'Local', 'Sucursal', 
        'Zona Reparto', 'lat', 'lon', 
        'distancia_km', 'costo_estimado'
    ]]
    
    # Convertir a CSV
    output = StringIO()
    df_export.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    # Crear respuesta con el CSV
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=detalle_analisis_{sucursal}.csv'
        }
    )


if __name__ == '__main__':
    # Cargar datos al iniciar la aplicación
    logger.info("Iniciando aplicación Flask...")
    # No cargamos clientes automáticamente para evitar incluir datos en el repo.
    # Los clientes se deben subir a través del endpoint `/upload_clientes`.
    cargar_datos_sucursales()

    # Ejecutar servidor Flask
    app.run(debug=False, host='0.0.0.0', port=5000)
