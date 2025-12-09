"""
Módulo de cálculo de distancias entre puntos geográficos.

Implementación actual: Haversine (distancia a vuelo de pájaro)
Diseño preparado para futuro: OSRM (distancia de ruteo real por carretera)

La función principal calculate_distance_km() actúa como interfaz unificada
que permite cambiar entre diferentes métodos de cálculo sin afectar el resto
de la aplicación.
"""

import numpy as np
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia Haversine entre dos puntos geográficos.
    
    La fórmula Haversine calcula la distancia "a vuelo de pájaro" sobre
    la superficie de una esfera (aproximación de la Tierra).
    
    Parámetros:
        lat1, lon1: Latitud y longitud del punto 1 (pueden ser arrays/Series)
        lat2, lon2: Latitud y longitud del punto 2 (escalares)
    
    Retorna:
        Distancia en kilómetros (array o escalar, según entrada)
    
    Nota: Esta función está vectorizada con numpy para calcular eficientemente
    distancias de múltiples puntos simultáneamente.
    """
    # Radio de la Tierra en kilómetros
    R = 6371.0
    
    # Convertir grados a radianes
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Diferencias
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula Haversine
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    # Distancia en kilómetros
    distance = R * c
    
    return distance


def osrm_route_distance_km(clientes_df, lat_dest, lon_dest, osrm_url="http://localhost:5000"):
    """
    [FUTURO] Calcula distancias de ruteo reales usando un servidor OSRM.
    
    OSRM (Open Source Routing Machine) proporciona distancias de ruta por carretera,
    considerando la red vial real y no solo la distancia en línea recta.
    
    Parámetros:
        clientes_df: DataFrame con columnas 'lat' y 'lon' de los clientes
        lat_dest: Latitud del punto destino (sucursal propuesta)
        lon_dest: Longitud del punto destino (sucursal propuesta)
        osrm_url: URL del servidor OSRM (por defecto localhost:5000)
    
    Retorna:
        Serie de pandas con distancias en kilómetros
    
    Implementación sugerida:
    ----------------------
    1. Construir request a OSRM API con múltiples coordenadas
       Ejemplo: GET /route/v1/driving/{lon1},{lat1};{lon2},{lat2}
    
    2. Opciones de implementación:
       a) Batch: Enviar todas las coordenadas en una sola petición (más eficiente)
          - Requiere construir URL con múltiples puntos
          - Limitar a 100-200 puntos por petición para evitar URLs muy largas
          
       b) Individual: Iterar sobre clientes y hacer una petición por cliente
          - Más simple pero más lento
          - Útil si hay pocos clientes
    
    3. Parsear respuesta JSON de OSRM y extraer distancias
       La respuesta típica incluye: routes[0].distance (en metros)
    
    4. Convertir metros a kilómetros y retornar
    
    Ejemplo de código (comentado para implementación futura):
    
    import requests
    
    distancias = []
    for idx, row in clientes_df.iterrows():
        lat_orig = row['lat']
        lon_orig = row['lon']
        
        # Construir URL para OSRM
        url = f"{osrm_url}/route/v1/driving/{lon_orig},{lat_orig};{lon_dest},{lat_dest}"
        params = {
            'overview': 'false',
            'steps': 'false'
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['code'] == 'Ok':
                # Extraer distancia en metros y convertir a km
                distance_m = data['routes'][0]['distance']
                distance_km = distance_m / 1000.0
                distancias.append(distance_km)
            else:
                # Si falla el ruteo, usar Haversine como fallback
                dist_fallback = haversine_km(lat_orig, lon_orig, lat_dest, lon_dest)
                distancias.append(dist_fallback)
        except:
            # En caso de error, usar Haversine como fallback
            dist_fallback = haversine_km(lat_orig, lon_orig, lat_dest, lon_dest)
            distancias.append(dist_fallback)
    
    return pd.Series(distancias, index=clientes_df.index)
    """
    
    # Placeholder: Por ahora lanzar excepción indicando que no está implementado
    raise NotImplementedError(
        "OSRM routing no está implementado aún. "
        "Descomentar y completar el código sugerido arriba para habilitar."
    )


def calculate_distance_km(clientes_df, lat_dest, lon_dest, mode="haversine"):
    """
    Interfaz unificada para calcular distancias.
    
    Esta función actúa como punto de entrada único para el cálculo de distancias,
    permitiendo cambiar fácilmente entre diferentes métodos (Haversine vs OSRM)
    sin modificar el código que la llama.
    
    Parámetros:
        clientes_df: DataFrame con columnas 'lat' y 'lon' de los clientes
        lat_dest: Latitud del punto destino (sucursal propuesta)
        lon_dest: Longitud del punto destino (sucursal propuesta)
        mode: Método de cálculo a usar
              - "haversine" (default): Distancia a vuelo de pájaro
              - "osrm": Distancia de ruteo real (requiere servidor OSRM)
    
    Retorna:
        Serie de pandas con distancias en kilómetros, un valor por cada cliente
    
    Uso:
        # HOY: Usar Haversine
        distancias = calculate_distance_km(df_clientes, -23.65, -70.40, mode="haversine")
        
        # MAÑANA: Cambiar a OSRM (cuando esté implementado)
        distancias = calculate_distance_km(df_clientes, -23.65, -70.40, mode="osrm")
    """
    
    if mode == "haversine":
        # Método actual: Haversine (distancia a vuelo de pájaro)
        lat_array = clientes_df['lat'].values
        lon_array = clientes_df['lon'].values
        
        distancias = haversine_km(lat_array, lon_array, lat_dest, lon_dest)
        
        return pd.Series(distancias, index=clientes_df.index)
    
    elif mode == "osrm":
        # Método futuro: OSRM (distancia de ruteo real)
        # Cuando se implemente, esta línea llamará a la función OSRM
        return osrm_route_distance_km(clientes_df, lat_dest, lon_dest)
    
    else:
        raise ValueError(
            f"Modo '{mode}' no reconocido. "
            f"Opciones válidas: 'haversine', 'osrm'"
        )


# Funciones auxiliares para el futuro

def batch_osrm_distances(coordinates_list, osrm_url="http://localhost:5000"):
    """
    [FUTURO] Calcula distancias en batch usando OSRM table service.
    
    El servicio 'table' de OSRM es más eficiente para calcular distancias
    de muchos orígenes a muchos destinos.
    
    Ver: http://project-osrm.org/docs/v5.24.0/api/#table-service
    """
    pass


def validate_osrm_server(osrm_url="http://localhost:5000"):
    """
    [FUTURO] Verifica que el servidor OSRM esté disponible y funcionando.
    
    Útil para mostrar advertencias al usuario si OSRM no está disponible.
    """
    pass
