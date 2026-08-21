# -*- coding: utf-8 -*-
"""Conversión de coordenadas. Todo en WGS84, sin cambio de datum.

Copia recortada del módulo del hub, verificado contra las 40 estaciones CORS de
la red geodésica nacional —cuyas coordenadas geográficas y UTM constan en los
«Network Adjustment Report» oficiales— con una peor discrepancia de 0.6 mm.

**Se recortó a propósito.** El original interpreta coordenadas escritas a mano en
seis formatos distintos, porque en aquellas herramientas el usuario las teclea.
Aquí no las teclea nadie: entran en UTM 19N desde el servidor del Registro
Inmobiliario y salen en grados hacia Google Maps y Waze. Todo el parseo de DMS
sobraba, y arrastrarlo sería mantener código que nadie ejecuta.

`always_xy=True` NO ES OPCIONAL. Sin eso pyproj respeta el orden de ejes que
declara cada CRS, y EPSG:4326 declara **lat, lon** — al revés de lo que escribe
todo el mundo. El error no da excepción: da coordenadas plausibles en otro
continente.
"""

import pyproj

EPSG_GEO = "EPSG:4326"
ZONAS = {18: "EPSG:32618", 19: "EPSG:32619", 20: "EPSG:32620"}

# El Registro Inmobiliario sirve y recibe en UTM 19N, y todo el país entra en esa
# zona. Se declara igualmente como parámetro por si algún día hiciera falta.
ZONA_PAIS = 19

# Extremos del territorio dominicano, redondeados hacia afuera. Sirven solo para
# AVISAR, nunca para bloquear.
LIMITES = {"lat_min": 17.36, "lat_max": 19.98,
           "lon_min": -72.01, "lon_max": -68.32}

_cache = {}


def _tr(zona, hacia_utm):
    clave = (zona, hacia_utm)
    if clave not in _cache:
        a, b = EPSG_GEO, ZONAS[zona]
        if not hacia_utm:
            a, b = b, a
        _cache[clave] = pyproj.Transformer.from_crs(a, b, always_xy=True)
    return _cache[clave]


def geo_a_utm(lon, lat, zona=ZONA_PAIS):
    """Grados -> `(este, norte)`. Ojo al orden: entra **lon, lat**."""
    return _tr(zona, True).transform(lon, lat)


def utm_a_geo(este, norte, zona=ZONA_PAIS):
    """`(este, norte)` -> `(lon, lat)`. Ojo al orden: sale **lon, lat**."""
    return _tr(zona, False).transform(este, norte)


def a_dms(valor, es_latitud, decimales=2):
    """Grados decimales -> texto en grados, minutos y segundos, con letra.

    Se enseña junto a los decimales porque es como vienen escritas las
    coordenadas en un título y en una certificación del RI: quien tiene el papel
    delante puede comparar sin convertir nada.
    """
    letra = (("N" if valor >= 0 else "S") if es_latitud
             else ("E" if valor >= 0 else "W"))
    v = abs(valor)
    g = int(v)
    resto = (v - g) * 60
    mi = int(resto)
    se = (resto - mi) * 60
    # Arrastre por redondeo: 59.999" no puede imprimirse como 60.00".
    if round(se, decimales) >= 60:
        se = 0.0
        mi += 1
    if mi >= 60:
        mi = 0
        g += 1
    return "%d°%02d'%0*.*f\"%s" % (g, mi, decimales + 3, decimales, se, letra)


def fuera_del_pais(lat, lon):
    """Devuelve None si el punto cae en el país, o el motivo si no.

    Aquí el punto no lo escribe el usuario sino el Registro Inmobiliario, así que
    esto no atrapa un error de tecleo: atrapa **un dato oficial mal proyectado**.
    Si un posicional devolviera una parcela en mitad del Atlántico, el aviso es lo
    único que impediría que el enlace de Waze la diera por buena.
    """
    if not (LIMITES["lat_min"] <= lat <= LIMITES["lat_max"]
            and LIMITES["lon_min"] <= lon <= LIMITES["lon_max"]):
        return ("El punto que devolvió el Registro Inmobiliario cae **fuera de "
                "la República Dominicana** (lat %.5f, lon %.5f). No use estas "
                "coordenadas para ir a ningún sitio: consulte el portal oficial."
                % (lat, lon))
    return None
