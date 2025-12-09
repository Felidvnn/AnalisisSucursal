/**
 * Aplicación de análisis de ubicaciones de sucursales
 * Maneja el mapa interactivo, filtros, llamadas a la API y visualización de resultados
 */

// Variables globales
let map;
let clientesLayer;
let marcadorPropuesta;
let marcadorOptimo;
let marcadorSucursalReal;
let ultimoAnalisis = null;

/**
 * Inicializa el mapa Leaflet
 */
function inicializarMapa() {
    // Crear mapa centrado en Chile
    map = L.map('map').setView([-33.45, -70.65], 6);
    
    // Agregar capa de tiles (CartoDB Positron)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 19
    }).addTo(map);
    
    // Crear layer group para los marcadores de clientes
    clientesLayer = L.layerGroup().addTo(map);
    
    // Manejar clic en el mapa
    map.on('click', manejarClicMapa);
}

/**
 * Solicita el punto óptimo al backend y lo muestra en el mapa
 */
async function mostrarOptimoSucursal(sucursal) {
    if (!sucursal) {
        if (marcadorOptimo) {
            map.removeLayer(marcadorOptimo);
            marcadorOptimo = null;
        }
        return;
    }
    try {
        const response = await fetch(`/api/sugerir_optimo?sucursal=${encodeURIComponent(sucursal)}`);
        const data = await response.json();
        if (data.error) {
            if (marcadorOptimo) {
                map.removeLayer(marcadorOptimo);
                marcadorOptimo = null;
            }
            return;
        }
        // Mostrar marcador óptimo (verde)
        if (marcadorOptimo) {
            map.removeLayer(marcadorOptimo);
        }
        marcadorOptimo = L.marker([data.lat_optimo, data.lon_optimo], {
            icon: L.icon({
                iconUrl: '/static/img/marker-icon-2x-green.png',
                shadowUrl: '/static/img/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).addTo(map);
    } catch (error) {
        console.error('Error obteniendo óptimo:', error);
    }
}

/**
 * Muestra la ubicación de la sucursal real en el mapa (color naranja)
 */
async function mostrarSucursalReal(sucursal) {
    if (!sucursal) {
        if (marcadorSucursalReal) {
            map.removeLayer(marcadorSucursalReal);
            marcadorSucursalReal = null;
        }
        return;
    }
    try {
        const response = await fetch(`/api/sucursal_ubicacion?sucursal=${encodeURIComponent(sucursal)}`);
        const data = await response.json();
        if (data.error) {
            if (marcadorSucursalReal) {
                map.removeLayer(marcadorSucursalReal);
                marcadorSucursalReal = null;
            }
            return;
        }
        // Mostrar marcador sucursal real (naranja)
        if (marcadorSucursalReal) {
            map.removeLayer(marcadorSucursalReal);
        }
        marcadorSucursalReal = L.marker([data.lat, data.lon], {
            icon: L.icon({
                iconUrl: '/static/img/marker-icon-2x-orange.png',
                shadowUrl: '/static/img/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).addTo(map);
    } catch (error) {
        console.error('Error obteniendo sucursal real:', error);
    }
}

/**
 * Carga los clientes de una sucursal y los muestra en el mapa
 */
async function cargarClientesSucursal(sucursal) {
    if (!sucursal) {
        clientesLayer.clearLayers();
        actualizarInfoSucursal(sucursal, 0);
        mostrarOptimoSucursal(null);
        mostrarSucursalReal(null);
        return;
    }
    try {
        const response = await fetch(`/api/clientes_por_sucursal?sucursal=${encodeURIComponent(sucursal)}`);
        const data = await response.json();
        if (data.error) {
            alert('Error: ' + data.error);
            mostrarOptimoSucursal(null);
            mostrarSucursalReal(null);
            return;
        }
        // Limpiar marcadores anteriores
        clientesLayer.clearLayers();
        // Agregar marcador por cada cliente
        const bounds = [];
        data.clientes.forEach(cliente => {
            const marker = L.circleMarker([cliente.lat, cliente.lon], {
                radius: 6,
                fillColor: '#3388ff',
                color: '#fff',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.7
            });
            // Tooltip con información del cliente
            marker.bindTooltip(
                `<strong>${cliente.Local}</strong><br>` +
                `Zona: ${cliente['Zona Reparto']}<br>` +
                `Cod: ${cliente['Cod Local']}`,
                { permanent: false, direction: 'top' }
            );
            marker.addTo(clientesLayer);
            bounds.push([cliente.lat, cliente.lon]);
        });
        // Ajustar vista del mapa a los clientes
        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
        // Actualizar información en el panel
        actualizarInfoSucursal(sucursal, data.total);
        // Mostrar óptimo sugerido y sucursal real
        mostrarOptimoSucursal(sucursal);
        mostrarSucursalReal(sucursal);
    } catch (error) {
        console.error('Error cargando clientes:', error);
        alert('Error al cargar los clientes de la sucursal');
        mostrarOptimoSucursal(null);
        mostrarSucursalReal(null);
    }
}

/**
 * Maneja el clic en el mapa para analizar un punto propuesto
 */
async function manejarClicMapa(e) {
    const sucursal = document.getElementById('selectSucursal').value;
    if (!sucursal) {
        alert('Por favor, seleccione una sucursal primero');
        return;
    }
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    const costoKm = parseFloat(document.getElementById('inputCostoKm').value) || 0;
    // Mostrar marcador de la ubicación consultada (rojo)
    if (marcadorPropuesta) {
        map.removeLayer(marcadorPropuesta);
    }
    marcadorPropuesta = L.marker([lat, lon], {
        icon: L.icon({
            iconUrl: '/static/img/marker-icon-2x-red.png',
            shadowUrl: '/static/img/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        })
    }).addTo(map);
    // Llamar a la API para analizar el punto
    try {
        const response = await fetch('/api/analisis_punto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sucursal: sucursal,
                lat_click: lat,
                lon_click: lon,
                costo_km: costoKm
            })
        });
        const resultado = await response.json();
        if (resultado.error) {
            alert('Error: ' + resultado.error);
            return;
        }
        // Guardar resultado para exportación
        ultimoAnalisis = resultado;
        // Mostrar resultados en el panel
        mostrarResultados(resultado);
        // Llenar tabla de detalle
        llenarTablaDetalle(resultado.detalle_clientes);
    } catch (error) {
        console.error('Error en el análisis:', error);
        alert('Error al analizar el punto seleccionado');
    }
}

/**
 * Actualiza la información de la sucursal en el panel
 */
function actualizarInfoSucursal(sucursal, numClientes) {
    document.getElementById('nombreSucursal').textContent = sucursal || '-';
    document.getElementById('numClientes').textContent = `${numClientes} clientes`;
}

/**
 * Muestra los resultados del análisis en el panel derecho
 */
function mostrarResultados(resultado) {
    // Ocultar mensaje inicial y mostrar resultados
    document.getElementById('mensajeInicial').style.display = 'none';
    document.getElementById('resultadosAnalisis').style.display = 'block';
    
    // Llenar campos básicos
    document.getElementById('coordenadasPunto').textContent = 
        `${resultado.lat_click.toFixed(6)}, ${resultado.lon_click.toFixed(6)}`;
    
    document.getElementById('distanciaPromedio').textContent = 
        `${resultado.distancia_promedio} km`;
    
    document.getElementById('costoPromedio').textContent = 
        `$${resultado.costo_promedio.toLocaleString('es-CL')}`;
    
    // Mostrar métricas comparativas con sucursal real
    if (resultado.metricas_comparativas && resultado.metricas_comparativas.sucursal_real) {
        const real = resultado.metricas_comparativas.sucursal_real;
        document.getElementById('metricasReal').style.display = 'block';
        
        document.getElementById('distanciaReal').textContent = `${real.distancia_promedio_actual} km`;
        document.getElementById('distanciaConsultadoReal').textContent = `${real.distancia_consultado_a_real} km`;
        
        // Mejora en distancia (con color)
        const mejoraHTML = real.mejora_distancia_km >= 0 
            ? `<span class="text-success fw-bold">-${real.mejora_distancia_km} km (${real.mejora_porcentaje}% mejor)</span>`
            : `<span class="text-danger fw-bold">+${Math.abs(real.mejora_distancia_km)} km (${Math.abs(real.mejora_porcentaje)}% peor)</span>`;
        document.getElementById('mejoraDistancia').innerHTML = mejoraHTML;
        
        // Ahorro en costo (con color)
        const ahorroHTML = real.ahorro_costo_promedio >= 0
            ? `<span class="text-success fw-bold">$${real.ahorro_costo_promedio.toLocaleString('es-CL')} ahorro</span>`
            : `<span class="text-danger fw-bold">$${Math.abs(real.ahorro_costo_promedio).toLocaleString('es-CL')} más caro</span>`;
        document.getElementById('ahorroCosto').innerHTML = ahorroHTML;
        
        // Barra de progreso de clientes más cercanos
        const porcNueva = real.porcentaje_mejora_consultado;
        const porcActual = 100 - porcNueva;
        document.getElementById('barraNuevaUbicacion').style.width = `${porcNueva}%`;
        document.getElementById('barraUbicacionActual').style.width = `${porcActual}%`;
        document.getElementById('textoNuevaUbicacion').textContent = `${porcNueva.toFixed(0)}%`;
        document.getElementById('textoUbicacionActual').textContent = `${porcActual.toFixed(0)}%`;
    } else {
        document.getElementById('metricasReal').style.display = 'none';
    }
    
    // Mostrar métricas comparativas con óptimo
    if (resultado.metricas_comparativas && resultado.metricas_comparativas.optimo_sugerido) {
        const optimo = resultado.metricas_comparativas.optimo_sugerido;
        document.getElementById('metricasOptimo').style.display = 'block';
        
        document.getElementById('distanciaOptimo').textContent = `${optimo.distancia_promedio_optimo} km`;
        document.getElementById('distanciaConsultadoOptimo').textContent = `${optimo.distancia_consultado_a_optimo} km`;
        
        // Diferencia vs óptimo
        // diferencia_vs_optimo_km es POSITIVO si el consultado es PEOR (mayor distancia)
        // diferencia_vs_optimo_km es NEGATIVO si el consultado es MEJOR (menor distancia)
        const difOptimo = optimo.diferencia_vs_optimo_km <= 0
            ? `<span class="text-success">Mejor por ${Math.abs(optimo.diferencia_vs_optimo_km)} km</span>`
            : `<span class="text-danger">Peor por ${optimo.diferencia_vs_optimo_km} km</span>`;
        document.getElementById('diferenciaOptimo').innerHTML = difOptimo;
    } else {
        document.getElementById('metricasOptimo').style.display = 'none';
    }
}

/**
 * Llena la tabla de detalle con los datos de cada cliente
 */
function llenarTablaDetalle(detalleClientes) {
    const tbody = document.getElementById('cuerpoTablaDetalle');
    tbody.innerHTML = '';
    
    if (!detalleClientes || detalleClientes.length === 0) {
        document.getElementById('contenedorTabla').style.display = 'none';
        document.getElementById('mensajeTablaVacia').style.display = 'block';
        return;
    }
    
    // Mostrar tabla y ocultar mensaje vacío
    document.getElementById('contenedorTabla').style.display = 'block';
    document.getElementById('mensajeTablaVacia').style.display = 'none';
    
    // Crear filas
    detalleClientes.forEach(cliente => {
        const fila = document.createElement('tr');
        fila.innerHTML = `
            <td>${cliente['Cod Local']}</td>
            <td>${cliente.Local}</td>
            <td>${cliente['Zona Reparto']}</td>
            <td>${cliente.lat.toFixed(6)}</td>
            <td>${cliente.lon.toFixed(6)}</td>
            <td class="text-end">${cliente.distancia_km}</td>
            <td class="text-end">$${cliente.costo_estimado.toLocaleString('es-CL')}</td>
        `;
        tbody.appendChild(fila);
    });
}

/**
 * Exporta el detalle del análisis como CSV
 */
function exportarCSV() {
    if (!ultimoAnalisis) {
        alert('No hay datos para exportar. Realice un análisis primero.');
        return;
    }
    
    const sucursal = ultimoAnalisis.sucursal;
    const lat = ultimoAnalisis.lat_click;
    const lon = ultimoAnalisis.lon_click;
    const costoKm = ultimoAnalisis.costo_km;
    
    const url = `/export_detalle_csv?sucursal=${encodeURIComponent(sucursal)}&lat=${lat}&lon=${lon}&costo_km=${costoKm}`;
    
    // Descargar archivo
    window.location.href = url;
}

/**
 * Inicialización cuando el DOM está listo
 */
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar mapa
    inicializarMapa();
    // Manejar cambio de sucursal
    document.getElementById('selectSucursal').addEventListener('change', function(e) {
        const sucursal = e.target.value;
        cargarClientesSucursal(sucursal);
        // Limpiar resultados anteriores
        document.getElementById('mensajeInicial').style.display = 'block';
        document.getElementById('resultadosAnalisis').style.display = 'none';
        document.getElementById('contenedorTabla').style.display = 'none';
        document.getElementById('mensajeTablaVacia').style.display = 'block';
        // Limpiar marcador de consulta
        if (marcadorPropuesta) {
            map.removeLayer(marcadorPropuesta);
            marcadorPropuesta = null;
        }
        ultimoAnalisis = null;
    });
    // Manejar botón de exportar
    document.getElementById('btnExportar').addEventListener('click', exportarCSV);
    // Cargar primera sucursal si existe
    const selectSucursal = document.getElementById('selectSucursal');
    if (selectSucursal.options.length > 1) {
        // Seleccionar primera opción válida (no vacía)
        selectSucursal.selectedIndex = 1;
        cargarClientesSucursal(selectSucursal.value);
    }

    // Upload handlers for master data
    async function uploadFile(endpoint, inputId, button) {
        const input = document.getElementById(inputId);
        if (!input || !input.files || input.files.length === 0) {
            alert('Seleccione un archivo primero');
            return;
        }
        const file = input.files[0];
        const formData = new FormData();
        formData.append('file', file);
        try {
            button.disabled = true;
            const resp = await fetch(endpoint, { method: 'POST', body: formData });
            const data = await resp.json();
            if (resp.ok && data.ok) {
                alert(data.message || 'Archivo cargado correctamente. Se recargará la página.');
                // Recargar para refrescar lista de sucursales
                window.location.reload();
            } else {
                alert('Error cargando archivo: ' + (data.error || JSON.stringify(data)));
            }
        } catch (err) {
            console.error('Error upload:', err);
            alert('Error en la carga del archivo');
        } finally {
            button.disabled = false;
        }
    }

    const btnUploadClientes = document.getElementById('btnUploadClientes');
    if (btnUploadClientes) {
        btnUploadClientes.addEventListener('click', function() {
            uploadFile('/upload_clientes', 'fileClientesInput', btnUploadClientes);
        });
    }
});
