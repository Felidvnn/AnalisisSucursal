# Aplicación de Análisis de Ubicaciones de Sucursales

Aplicación web Flask para analizar y proponer ubicaciones de nuevas sucursales mediante un mapa interactivo. Permite visualizar clientes por sucursal, analizar distancias a puntos propuestos y calcular costos estimados de operación.

## Características

- 📍 **Mapa Interactivo**: Visualización de clientes en mapa Leaflet
- 🔍 **Filtrado por Sucursal**: Análisis específico por sucursal
- 📊 **Análisis de Distancias**: Cálculo de distancias a puntos propuestos
- 💰 **Estimación de Costos**: Parametrización de costo por kilómetro
- 📥 **Exportación CSV**: Descarga de análisis detallado
- 🔄 **Arquitectura Extensible**: Preparada para integrar ruteo OSRM

## Tecnologías

- **Backend**: Python 3, Flask
- **Frontend**: HTML, Bootstrap 5, Leaflet
- **Datos**: Pandas, NumPy
- **Distancias**: Haversine (actual), OSRM (futuro)

## Estructura del Proyecto

```
├── app.py                      # Aplicación Flask principal
├── services/
│   └── distance.py             # Módulo de cálculo de distancias
├── templates/
│   ├── base.html               # Template base con Bootstrap
│   └── index.html              # Vista principal
├── static/
│   ├── css/
│   │   └── styles.css          # Estilos personalizados
│   └── js/
│       └── main.js             # Lógica JavaScript (Leaflet)
├── data/
│   └── clientes.csv            # Base de datos de clientes
├── requirements.txt            # Dependencias Python
└── README.md                   # Este archivo
```

## Instalación

### 1. Clonar o descargar el proyecto

```bash
cd "App propuesta sucursal"
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## Uso

### 1. Iniciar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

### 2. Usar la aplicación

1. **Seleccionar Sucursal**: Escoge una sucursal del dropdown
2. **Visualizar Clientes**: El mapa mostrará todos los clientes de esa sucursal
3. **Analizar Punto**: Haz clic en cualquier ubicación del mapa
4. **Ver Resultados**: Consulta distancias y costos en el panel derecho
5. **Exportar**: Descarga el análisis detallado en CSV

## Formato de Datos

El archivo `data/clientes.csv` debe contener las siguientes columnas:

- `Sucursal`: Nombre de la sucursal
- `Cod Local`: Código único del cliente
- `Local`: Nombre del cliente
- `Tipo Cliente`: Tipo de cliente
- `Frec SAP`: Frecuencia actual en SAP
- `Propuesta Frec`: Frecuencia propuesta
- `Propuesta ZR`: Propuesta de zona de reparto
- `Tipo Desviación`: Tipo de desviación
- `Cod ZR`: Código de zona de reparto
- `Zona Reparto`: Nombre de zona de reparto
- `Coordenadas`: Coordenadas en formato "(-23.651,-70.383)"

## API Endpoints

### GET `/`
Renderiza la página principal.

### GET `/api/clientes_por_sucursal?sucursal=Nombre`
Retorna los clientes de una sucursal específica.

**Respuesta**:
```json
{
  "clientes": [...],
  "total": 10
}
```

### POST `/api/analisis_punto`
Analiza un punto propuesto como nueva sucursal.

**Request**:
```json
{
  "sucursal": "Antofagasta",
  "lat_click": -23.65,
  "lon_click": -70.40,
  "costo_km": 500
}
```

**Respuesta**:
```json
{
  "sucursal": "Antofagasta",
  "lat_click": -23.65,
  "lon_click": -70.40,
  "distancia_promedio": 5.23,
  "distancia_minima": 1.45,
  "distancia_maxima": 12.87,
  "numero_clientes": 10,
  "costo_km": 500,
  "costo_promedio": 2615.00,
  "detalle_clientes": [...]
}
```

### GET `/export_detalle_csv?sucursal=...&lat=...&lon=...&costo_km=...`
Exporta el análisis detallado como CSV.

## Cálculo de Distancias

### Implementación Actual: Haversine

La aplicación utiliza la fórmula Haversine para calcular distancias "a vuelo de pájaro":

```python
from services.distance import calculate_distance_km

distancias = calculate_distance_km(
    clientes_df, 
    lat_dest=-23.65, 
    lon_dest=-70.40, 
    mode="haversine"
)
```

### Implementación Futura: OSRM

El código está preparado para integrar distancias de ruteo real usando OSRM:

```python
# Futuro: cambiar a mode="osrm"
distancias = calculate_distance_km(
    clientes_df, 
    lat_dest=-23.65, 
    lon_dest=-70.40, 
    mode="osrm"
)
```

**Pasos para implementar OSRM**:

1. Instalar y configurar un servidor OSRM
2. Descomentar y completar la función `osrm_route_distance_km()` en `services/distance.py`
3. Cambiar el parámetro `mode` a `"osrm"` en las llamadas

## Personalización

### Cambiar el costo por km por defecto
Editar en `templates/index.html`:
```html
<input type="number" id="inputCostoKm" class="form-control" value="500" ...>
```

### Agregar más sucursales
Agregar filas al archivo `data/clientes.csv` con el formato indicado.

### Personalizar estilos
Modificar `static/css/styles.css`.

### Cambiar centro inicial del mapa
Editar en `static/js/main.js`:
```javascript
map = L.map('map').setView([-33.45, -70.65], 6);
```

## Solución de Problemas

### El mapa no se muestra
- Verifica que los archivos CSS y JS de Leaflet se carguen correctamente
- Revisa la consola del navegador en busca de errores

### No se cargan los clientes
- Verifica que el archivo `data/clientes.csv` exista y tenga el formato correcto
- Revisa que las coordenadas tengan el formato `"(-23.651,-70.383)"`

### Error al calcular distancias
- Asegúrate de que pandas y numpy estén instalados correctamente
- Verifica que las coordenadas sean numéricas válidas

## Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## Contacto

Para preguntas o sugerencias, contacta al desarrollador.
