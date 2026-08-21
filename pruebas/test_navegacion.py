# -*- coding: utf-8 -*-
"""Los dos enlaces de ir. Es la mitad visible del producto.

**Estas pruebas leen las coordenadas de vuelta desde la URL**, en vez de comparar
la cadena generada contra otra cadena escrita a mano. La diferencia no es
estilística: una prueba escrita del segundo modo repite el mismo error que el
código si el error está en la plantilla, y aquí el error posible es que se pierda
el signo del oeste — que no da ninguna excepción y pone el inmueble a 7 500 km.
"""

import os
import re
import sys
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import navegacion                                      # noqa: E402

FALLOS = []


def cierto(condicion, que):
    if not condicion:
        FALLOS.append(que)


def cerca(a, b, tolerancia, que):
    if abs(a - b) > tolerancia:
        FALLOS.append("%s: esperaba %.8f, llegó %.8f" % (que, b, a))


# Un punto en Santo Domingo, inventado pero con la forma y el signo correctos:
# latitud norte positiva, longitud oeste NEGATIVA.
LAT, LON = 18.478123, -69.912456

# El mismo punto, cerca del límite del país, para que el redondeo se vea.
LAT_NORTE, LON_OESTE = 19.931000, -71.701000


def _par_de(url, parametro):
    """Saca `lat,lon` de la URL y los devuelve como dos números.

    Pasa por el parseo de verdad —`urlparse` y `parse_qs`— para que un cambio en
    la codificación de la coma o del signo se note aquí y no en el teléfono de
    alguien.
    """
    partes = urlparse(url)
    consulta = parse_qs(partes.query)
    cierto(parametro in consulta,
           "la URL tiene que llevar el parámetro «%s»: %s" % (parametro, url))
    if parametro not in consulta:
        return None, None
    crudo = unquote(consulta[parametro][0])
    lat, lon = crudo.split(",")
    return float(lat), float(lon)


# ---------------------------------------------------------------- el par --

def prueba_el_orden_es_lat_lon():
    """Los dos servicios piden `lat,lon`, al revés que UTM y que GeoJSON.

    Cambiarlos deja el punto en el mar, frente a Somalia, sin ningún error.
    """
    texto = navegacion.coordenadas_para_pegar(LAT, LON)
    primero, segundo = (float(x) for x in texto.split(","))
    cerca(primero, LAT, 1e-6, "el primero tiene que ser la LATITUD")
    cerca(segundo, LON, 1e-6, "el segundo tiene que ser la LONGITUD")


def prueba_el_signo_del_oeste_sobrevive():
    """La República Dominicana está en el oeste: su longitud es negativa.

    Sin el signo, el punto cae en Arabia Saudí y los dos servicios abren el mapa
    tan contentos. No hay coordenada inválida, solo una equivocada.
    """
    for nombre, url, parametro in (
            ("Google Maps", navegacion.google_maps(LAT, LON), "destination"),
            ("Waze", navegacion.waze(LAT, LON), "ll")):
        lat, lon = _par_de(url, parametro)
        if lon is None:
            continue
        cierto(lon < 0,
               "%s: la longitud tiene que ser NEGATIVA y llegó %.6f" % (nombre, lon))
        cerca(lat, LAT, 1e-6, "%s: la latitud" % nombre)
        cerca(lon, LON, 1e-6, "%s: la longitud" % nombre)


def prueba_los_dos_enlaces_llevan_el_mismo_punto():
    """El mapa de la página, Google Maps y Waze salen del mismo par.

    Que uno de los tres señale otro sitio sería invisible mirando la pantalla.
    """
    g_lat, g_lon = _par_de(navegacion.google_maps(LAT, LON), "destination")
    w_lat, w_lon = _par_de(navegacion.waze(LAT, LON), "ll")
    pegar = navegacion.coordenadas_para_pegar(LAT, LON)
    p_lat, p_lon = (float(x) for x in pegar.split(","))
    cerca(g_lat, w_lat, 0.0, "la latitud de Google y la de Waze")
    cerca(g_lon, w_lon, 0.0, "la longitud de Google y la de Waze")
    cerca(g_lat, p_lat, 0.0, "la latitud del enlace y la de copiar")
    cerca(g_lon, p_lon, 0.0, "la longitud del enlace y la de copiar")


def prueba_hay_seis_decimales():
    """Seis decimales de grado son 11 cm. Cinco son 1.1 m.

    El punto se calculó con precisión de milímetros; truncarlo aquí sería tirar
    la única parte del trabajo que el usuario va a usar de verdad.
    """
    texto = navegacion.coordenadas_para_pegar(LAT_NORTE, LON_OESTE)
    for trozo in texto.split(","):
        decimales = len(trozo.split(".")[1])
        cierto(decimales == navegacion.DECIMALES,
               "cada coordenada tiene que llevar %d decimales y «%s» lleva %d"
               % (navegacion.DECIMALES, trozo, decimales))


def prueba_no_se_pierde_precision_al_ir_y_volver():
    for lat, lon in ((LAT, LON), (LAT_NORTE, LON_OESTE), (17.5, -71.99999)):
        vuelta_lat, vuelta_lon = _par_de(
            navegacion.google_maps(lat, lon), "destination")
        # 1e-6 grados es el paso del propio formato: no se puede exigir más.
        cerca(vuelta_lat, lat, 1e-6, "ida y vuelta de la latitud")
        cerca(vuelta_lon, lon, 1e-6, "ida y vuelta de la longitud")


# -------------------------------------------------------------- los enlaces --

def prueba_google_maps_va_en_modo_navegacion():
    """`dir` traza la ruta; `search` solo enseña el punto. Se pidió ir allá."""
    url = navegacion.google_maps(LAT, LON)
    cierto("/maps/dir/" in url,
           "Google Maps tiene que abrirse en modo ruta y llegó: %s" % url)
    cierto("api=1" in url,
           "hay que usar la forma documentada y estable de Maps URLs (api=1)")


def prueba_waze_va_en_modo_navegacion():
    """Sin `navigate=yes` deja el mapa centrado y hay que pulsar «Ir» a mano."""
    url = navegacion.waze(LAT, LON)
    cierto("navigate=yes" in url,
           "Waze tiene que abrirse navegando y llegó: %s" % url)
    cierto("waze.com/ul" in url,
           "hay que usar el enlace universal de Waze y llegó: %s" % url)


def prueba_los_dos_van_por_https():
    for url in (navegacion.google_maps(LAT, LON), navegacion.waze(LAT, LON)):
        cierto(url.startswith("https://"),
               "los enlaces van por HTTPS y llegó: %s" % url)


def prueba_no_se_cuela_nada_mas_en_la_url():
    """Solo la coordenada. Ni el posicional, ni el expediente, ni nada del RI.

    Google y Waze son terceros: lo que se les manda es lo que se les promete en
    el aviso legal, que es un par de coordenadas y nada más.
    """
    for url in (navegacion.google_maps(LAT, LON), navegacion.waze(LAT, LON)):
        consulta = parse_qs(urlparse(url).query)
        sobrantes = set(consulta) - {"api", "destination", "ll", "navigate"}
        cierto(not sobrantes,
               "en la URL solo puede ir la coordenada, y sobraban: %s"
               % sorted(sobrantes))
        cierto(not re.search(r"\d{12}", unquote(url)),
               "no puede viajar nada con forma de posicional en la URL: %s"
               % url)


def prueba_hay_dos_enlaces_con_su_rotulo():
    lista = navegacion.enlaces(LAT, LON)
    cierto(len(lista) == 2, "son dos enlaces, y llegaron %d" % len(lista))
    nombres = [e["nombre"] for e in lista]
    cierto(nombres == ["Google Maps", "Waze"],
           "Google Maps va primero porque lo tiene todo el mundo; llegó %s"
           % nombres)
    for e in lista:
        for clave in ("nombre", "url", "icono", "ayuda"):
            cierto(e.get(clave), "cada enlace necesita «%s»" % clave)


def prueba_el_ecuador_y_el_meridiano_no_rompen_el_signo():
    """Un cero no puede escribirse como «-0.000000» ni perder el signo del otro.

    No pasa en el país, pero el formateo se prueba donde se rompe.
    """
    lat, lon = _par_de(navegacion.google_maps(0.0, -69.5), "destination")
    cerca(lat, 0.0, 1e-9, "latitud cero")
    cierto(lon < 0, "con latitud cero la longitud sigue siendo negativa")


# ------------------------------------------------------------------- lanzar --

def main():
    pruebas = [v for k, v in sorted(globals().items()) if k.startswith("prueba_")]
    for prueba in pruebas:
        try:
            prueba()
        except Exception as ex:                                   # noqa: BLE001
            FALLOS.append("%s reventó: %s: %s"
                          % (prueba.__name__, ex.__class__.__name__, ex))
    if FALLOS:
        for f in FALLOS:
            print("[FAIL]", f)
        print("\n%d de %d comprobaciones fallaron." % (len(FALLOS), len(pruebas)))
        return 1
    print("[OK] %d pruebas de los enlaces de navegación." % len(pruebas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
