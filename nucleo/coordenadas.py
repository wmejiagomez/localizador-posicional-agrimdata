# -*- coding: utf-8 -*-
"""Motor de conversion de coordenadas. Todo en WGS84, sin cambio de datum.

Verificado contra las 40 estaciones CORS de la red geodesica nacional, cuyas
coordenadas geograficas y UTM constan en los «Network Adjustment Report»
oficiales: peor discrepancia 0.6 mm. Ver `pruebas/test_coordenadas.py`.

`always_xy=True` NO ES OPCIONAL. Sin eso pyproj respeta el orden de ejes que
declara cada CRS, y EPSG:4326 declara **lat, lon** — al reves de lo que escribe
todo el mundo. El error no da excepcion: da coordenadas plausibles en otro
continente.
"""

import re
import pyproj

EPSG_GEO = "EPSG:4326"
ZONAS = {18: "EPSG:32618", 19: "EPSG:32619", 20: "EPSG:32620"}

# Extremos del territorio dominicano, redondeados hacia afuera. Sirven solo
# para AVISAR, nunca para bloquear: alguien puede estar trabajando legitimamente
# fuera del pais, y una herramienta que se niega a convertir es peor que una que
# convierte y advierte.
LIMITES = {"lat_min": 17.36, "lat_max": 19.98,
           "lon_min": -72.01, "lon_max": -68.32}

ZONA_PAIS = 19

_cache = {}


def _tr(zona, hacia_utm):
    clave = (zona, hacia_utm)
    if clave not in _cache:
        a, b = EPSG_GEO, ZONAS[zona]
        if not hacia_utm:
            a, b = b, a
        _cache[clave] = pyproj.Transformer.from_crs(a, b, always_xy=True)
    return _cache[clave]


# --- Parseo de DMS -----------------------------------------------------------
# Acepta: 18d12'31.31670"   18°12'31.31670"N   18 12 31.3167 N   -71°05'53.6"
# La letra puede ser N/S/E/W/O (en espanol el oeste se escribe O), y puede ir
# delante o detras del numero: «N18°28'22.8"» es como lo pintan varios GPS.
#
# **Los signos de minuto y segundo pueden ser la prima y la doble prima**
# —′ U+2032 y ″ U+2033—, ademas de las comillas rectas y tipograficas. Son los
# signos correctos y los que copian Wikipedia, GeoHack y varios visores: hasta
# el 2026-08-18 «18°28′22.8″N» se rechazaba con «formato no reconocido», y quien
# lo pegaba desde una ficha no tenia forma de saber que la culpa era del tipo
# de comilla.

_LETRAS = {"N": 1, "S": -1, "E": 1, "W": -1, "O": -1}

_RE_DMS = re.compile(
    r"""^\s*
    (?P<letra_delante>[NSEWO])?\s*
    (?P<signo>[+-])?\s*
    (?P<g>\d{1,3})\s*(?:[d°º:]|\s)\s*
    (?P<m>\d{1,2})\s*(?:['’′m:]|\s)\s*
    (?P<s>\d{1,2}(?:[.,]\d+)?)\s*(?:["”″s]|''|′′)?\s*
    (?P<letra>[NSEWO])?\s*$""",
    re.VERBOSE | re.IGNORECASE,
)

# Grados y minutos decimales: 18°28.380'N, 18 28.38 N, -69 55.86.
#
# **Añadido el 2026-08-16**, a petición de Werner, y repartido a todas las
# copias el 2026-08-18: es el formato
# que sueltan los GPS de mano y los teléfonos, y hasta ahora se rechazaba con un
# «formato no reconocido» que no ayudaba a nadie. Es una ampliación, no un
# cambio: todo lo que se interpretaba antes se sigue interpretando igual.
#
# El orden en que se prueban importa. Primero DMS, que exige TRES números, y
# después éste, que exige DOS: al revés, «18 28 22.8» entraría aquí leyendo 28
# minutos y tirando los segundos, y el punto acabaría a 380 metros de su sitio
# sin que nada avisara.
_RE_GDM = re.compile(
    r"""^\s*
    (?P<letra_delante>[NSEWO])?\s*
    (?P<signo>[+-])?\s*
    (?P<g>\d{1,3})\s*(?:[d°º:]|\s)\s*
    (?P<m>\d{1,2}(?:[.,]\d+)?)\s*(?:['’′m:]|\s)?\s*
    (?P<letra>[NSEWO])?\s*$""",
    re.VERBOSE | re.IGNORECASE,
)

_RE_DEC = re.compile(
    r"""^\s*(?P<letra_delante>[NSEWO])?\s*
        (?P<signo>[+-])?\s*(?P<v>\d{1,3}(?:[.,]\d+)?)\s*[°º]?\s*
        (?P<letra>[NSEWO])?\s*$""",
    re.VERBOSE | re.IGNORECASE,
)


class ErrorCoordenada(ValueError):
    pass


def parsear_angulo(texto, es_latitud):
    """Devuelve grados decimales. Lanza ErrorCoordenada si no es interpretable."""
    if texto is None:
        raise ErrorCoordenada("vacio")
    texto = str(texto).strip()
    if not texto:
        raise ErrorCoordenada("vacio")

    m = _RE_DMS.match(texto)
    if m:
        g = int(m.group("g"))
        mi = int(m.group("m"))
        se = float(m.group("s").replace(",", "."))
        if mi >= 60:
            raise ErrorCoordenada("minutos >= 60: %s" % texto)
        if se >= 60:
            raise ErrorCoordenada("segundos >= 60: %s" % texto)
        valor = g + mi / 60.0 + se / 3600.0
    else:
        m = _RE_GDM.match(texto)
        if m:
            g = int(m.group("g"))
            mi = float(m.group("m").replace(",", "."))
            if mi >= 60:
                raise ErrorCoordenada("minutos >= 60: %s" % texto)
            valor = g + mi / 60.0
        else:
            m = _RE_DEC.match(texto)
            if not m:
                raise ErrorCoordenada("formato no reconocido: %r" % texto)
            valor = float(m.group("v").replace(",", "."))

    signo_txt = -1 if m.group("signo") == "-" else 1
    delante = (m.group("letra_delante") or "").upper()
    detras = (m.group("letra") or "").upper()
    if delante and detras and delante != detras:
        raise ErrorCoordenada("dos letras que se contradicen: %r" % texto)
    letra = detras or delante

    if letra:
        eje_lat = letra in ("N", "S")
        if eje_lat != es_latitud:
            raise ErrorCoordenada(
                "la letra %s no corresponde a %s"
                % (letra, "latitud" if es_latitud else "longitud")
            )
        signo_letra = _LETRAS[letra]
        # Contradiccion explicita: no adivinar cual gana.
        if m.group("signo") == "-" and signo_letra == 1:
            raise ErrorCoordenada("signo y letra se contradicen: %r" % texto)
        if m.group("signo") == "-" and signo_letra == -1:
            pass  # -71 W: redundante pero coherente
        signo = signo_letra
    else:
        signo = signo_txt

    valor *= signo
    limite = 90.0 if es_latitud else 180.0
    if abs(valor) > limite:
        raise ErrorCoordenada("fuera de rango: %s" % texto)
    return valor


def a_dms(valor, es_latitud, decimales=5):
    """Grados decimales -> texto DMS con letra."""
    letra = ("N" if valor >= 0 else "S") if es_latitud else ("E" if valor >= 0 else "W")
    v = abs(valor)
    g = int(v)
    resto = (v - g) * 60
    mi = int(resto)
    se = (resto - mi) * 60
    # Arrastre por redondeo: 59.999999" no puede imprimirse como 60.00000"
    if round(se, decimales) >= 60:
        se = 0.0
        mi += 1
    if mi >= 60:
        mi = 0
        g += 1
    # Los grados no se rellenan con ceros: asi los escriben los «Network
    # Adjustment Report» de las estaciones CORS (71d, no 071d), y conviene que
    # el texto que genera esta herramienta se pueda comparar de un vistazo
    # contra el reporte oficial. Minutos y segundos si van a dos digitos.
    return '%dd%02d\'%0*.*f"%s' % (g, mi, decimales + 3, decimales, se, letra)


# --- Conversion --------------------------------------------------------------

def geo_a_utm(lon, lat, zona=19):
    return _tr(zona, True).transform(lon, lat)


def utm_a_geo(este, norte, zona=19):
    return _tr(zona, False).transform(este, norte)


# --- Control de cordura -------------------------------------------------------

def fuera_del_pais(lat, lon):
    """Devuelve None si el punto cae en el pais, o el motivo si no.

    Existe porque los dos errores mas comunes —intercambiar Este con Norte, o
    latitud con longitud— no producen ningun error de calculo: producen un punto
    perfectamente valido a miles de kilometros. Este es el unico control que los
    atrapa, y por eso el aviso tiene que ser visible, no una nota al pie.
    """
    if not (LIMITES["lat_min"] <= lat <= LIMITES["lat_max"]
            and LIMITES["lon_min"] <= lon <= LIMITES["lon_max"]):
        return ("El punto cae fuera de la República Dominicana "
                "(lat %.5f, lon %.5f). Si no es un trabajo en el exterior, "
                "revise si intercambió Este con Norte, o latitud con longitud."
                % (lat, lon))
    return None


def convertir(lat, lon, zona=ZONA_PAIS, nombre=None):
    """Un punto en geograficas -> todas sus representaciones.

    Devuelve un diccionario con las claves que consumen la tabla, el KML y el
    DXF, de modo que los tres partan exactamente de los mismos numeros.
    """
    este, norte = geo_a_utm(lon, lat, zona)
    return {
        "nombre": nombre,
        "lat": lat,
        "lon": lon,
        "lat_dms": a_dms(lat, True),
        "lon_dms": a_dms(lon, False),
        "este": este,
        "norte": norte,
        "zona": zona,
        "aviso": fuera_del_pais(lat, lon),
    }


def convertir_utm(este, norte, zona=ZONA_PAIS, nombre=None):
    """Un punto en UTM -> todas sus representaciones."""
    lon, lat = utm_a_geo(este, norte, zona)
    d = convertir(lat, lon, zona, nombre)
    # Se devuelven el Este y el Norte que escribio el usuario, no los que
    # resultan de convertir y volver: reimprimir 278098.72299 donde el escribio
    # 278098.723 parece un error de la herramienta aunque sean el mismo punto.
    d["este"], d["norte"] = este, norte
    return d
