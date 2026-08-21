# -*- coding: utf-8 -*-
"""El mapa: que enseñe el inmueble y que las trampas de folium sigan resueltas.

    python pruebas/test_mapa.py

**Las aserciones van sobre el HTML que folium genera, no sobre las constantes de
Python.** Es la lección del Visor Parcelario: con `tiles=None`, folium se traga
el `max_zoom` que se le pasa al constructor de `Map`, así que una prueba sobre
`mapa.ZOOM_MAXIMO_MAPA` habría dado verde con el fallo delante. Lo que hay que
mirar es el bloque `L.map(` del HTML.

Ninguna de estas pruebas ve si el mapa **se ve bien** —eso solo se comprueba
abriendo el navegador, y por eso la fase 6 del protocolo existe—. Lo que
comprueban es que las cuatro trampas que ya costaron caro en el hub no han
vuelto.
"""

import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

from nucleo import coordenadas, inmueble, mapa, ri                 # noqa: E402

FALLOS = []

with open(os.path.join(os.path.dirname(AQUI), "datos",
                       "inmuebles_ficticios.json"), encoding="utf-8") as f:
    CASOS = json.load(f)


def cierto(condicion, que):
    if not condicion:
        FALLOS.append(que)


def igual(a, b, que):
    if a != b:
        FALLOS.append("%s: esperaba %r, llegó %r" % (que, b, a))


def _ficha(caso="aprobada_simple", capa="aprobadas"):
    fichas, _ = inmueble.leer({capa: CASOS[caso]})
    return fichas[0]


def _geo(f):
    return [([coordenadas.utm_a_geo(e, n, ri.ZONA) for e, n in puntos], hueco)
            for puntos, hueco in f["anillos"]]


def _html(caso="aprobada_simple", capa="aprobadas"):
    f = _ficha(caso, capa)
    return mapa.construir(f, _geo(f)).get_root().render(), f


# ------------------------------------------------- las trampas de folium --

def prueba_el_tope_de_zoom_llega_al_html():
    """Trampa 3: con `tiles=None`, folium se traga el `max_zoom` del constructor.

    Se busca en el bloque `L.map(` del HTML generado, que es lo único que Leaflet
    va a leer. Una aserción sobre la constante de Python da verde con el fallo
    delante — pasó en el Visor Parcelario.
    """
    html, _ = _html()
    bloque = re.search(r"L\.map\(\s*['\"][^'\"]+['\"],\s*\{(.*?)\}\s*\)",
                       html, re.S)
    cierto(bloque is not None,
           "tiene que haber un bloque L.map( en el HTML generado")
    if bloque:
        cierto('"maxZoom": %d' % mapa.ZOOM_MAXIMO_MAPA in bloque.group(1)
               or "maxZoom: %d" % mapa.ZOOM_MAXIMO_MAPA in bloque.group(1),
               "el maxZoom del mapa tiene que estar en las opciones de L.map, "
               "y el bloque decía: %s" % bloque.group(1)[:200])


def prueba_el_parcelario_llega_mas_lejos_que_la_foto():
    """Trampas 1 y 2, que son la misma vista desde los dos lados.

    Si el parcelario no llega tan lejos como el zoom máximo del mapa, al
    ajustarse a una parcela pequeña quedan sus capas encendidas y con cero
    teselas: la parcela sobre el satélite y el parcelario ausente, sin un error
    en la consola.
    """
    cierto(mapa.ZOOM_MAXIMO_PARCELARIO > mapa.ZOOM_MAXIMO_FONDO,
           "el parcelario tiene que llegar más lejos que la foto (%d contra %d)"
           % (mapa.ZOOM_MAXIMO_PARCELARIO, mapa.ZOOM_MAXIMO_FONDO))
    igual(mapa.ZOOM_MAXIMO_MAPA, mapa.ZOOM_MAXIMO_FONDO,
          "y el mapa NO puede dejar acercarse más allá de donde llega la foto, "
          "o las parcelas quedan flotando sobre un fondo liso")


def prueba_solo_un_fondo_carga():
    """Trampa 4: sin `show=False`, los dos proveedores ven la zona mirada.

    El aviso legal promete que cada proveedor ve lo suyo; esto es lo que lo hace
    verdad. Se cuenta sobre el HTML: folium escribe un `map.addLayer` por cada
    capa que arranca encendida.
    """
    html, _ = _html()
    encendidos = 0
    for nombre, plantilla, _credito in mapa.FONDOS:
        # El identificador del `TileLayer` sale de su URL; se cuenta cuántos de
        # los dos fondos aparecen en una llamada a addLayer.
        trozo = plantilla.split("//")[1].split("/")[0].replace("{s}.", "")
        for identificador in re.findall(
                r'var (tile_layer_\w+) = L\.tileLayer\(\s*"([^"]+)"', html):
            if trozo in identificador[1] and \
                    re.search(r"%s\.addTo\(" % identificador[0], html):
                encendidos += 1
    igual(encendidos, 1,
          "solo UNO de los dos fondos puede arrancar encendido, y arrancaron %d"
          % encendidos)


def prueba_el_satelite_es_el_que_se_ve_al_abrir():
    """Quien busca su inmueble lo reconoce por la foto, no por el callejero."""
    igual(mapa.FONDOS[-1][0], "Satélite",
          "el último fondo de la lista es el que folium enseña, y tiene que "
          "ser el satélite")


def prueba_el_parcelario_es_transparente():
    """Sin `transparent=True`, GeoServer devuelve un PNG con fondo blanco opaco
    y la capa tapa el satélite entero."""
    html, _ = _html()
    cierto('"transparent": true' in html or "'transparent': true" in html,
           "la capa WMS del RI tiene que pedirse transparente")


def prueba_el_parcelario_no_tapa_la_foto():
    cierto(0 < mapa.OPACIDAD_PARCELARIO < 0.6,
           "el estilo por defecto del GeoServer del RI RELLENA los polígonos: "
           "a opacidad alta tapa la foto y se pierde lo que se venía a ver "
           "(está en %.2f)" % mapa.OPACIDAD_PARCELARIO)


# ------------------------------------------------------- lo que se dibuja --

def prueba_el_punto_esta_en_el_mapa():
    html, f = _html()
    # Folium escribe las coordenadas del marcador en el HTML. Se buscan con
    # menos decimales de los que escribe, para no atarse a su formato.
    aguja = "%.4f" % f["lat"]
    cierto(aguja in html,
           "la latitud del punto tiene que aparecer en el mapa generado (%s)"
           % aguja)
    cierto("L.marker" in html, "hay una chincheta")
    cierto("circle_marker" in html or "L.circleMarker" in html,
           "y un círculo debajo, que en el móvil es lo que la distingue de "
           "cualquier otro marcador del fondo")


def prueba_el_contorno_de_la_parcela_esta_dibujado():
    html, _ = _html()
    cierto("L.polygon" in html,
           "el contorno de la parcela tiene que dibujarse: el punto solo, sin "
           "la figura, no deja comprobar que es el terreno correcto")


def prueba_el_color_es_el_de_su_capa():
    """El rojo de las anuladas no es decorativo: una anulada que parece vigente
    es el error caro de esta herramienta."""
    html, f = _html("anulada", "anuladas")
    igual(f["color"], ri.CAPAS["anuladas"]["color"],
          "la ficha lleva el color de su capa")
    cierto(f["color"].lower() in html.lower(),
           "y ese color llega al mapa")


def prueba_solo_se_enciende_la_capa_del_ri_donde_se_encontro():
    """Un selector de cuatro capas catastrales delante de alguien que no sabe
    qué es una capa catastral es ruido."""
    html, _ = _html("previo2017_en_ele", "previo2017")
    cierto(ri.CAPAS["previo2017"]["tipo"] in html,
           "la capa donde se encontró tiene que estar de fondo")
    for otra in ("aprobadas", "anuladas"):
        cierto(ri.CAPAS[otra]["tipo"] not in html,
               "y la capa «%s», que no es la suya, NO" % otra)


def prueba_el_globo_avisa_cuando_el_punto_se_movio():
    html, f = _html("previo2017_en_ele", "previo2017")
    cierto(f["punto_ajustado"], "el fixture de la L tiene el punto ajustado")
    cierto("Punto movido" in html,
           "y el globo del mapa tiene que decirlo: quien va a conducir hasta "
           "allí tiene derecho a saber que el punto no es el centro")


def prueba_el_mapa_se_ajusta_a_la_parcela():
    html, _ = _html()
    cierto("fitBounds" in html,
           "el mapa tiene que encuadrarse sobre la parcela encontrada")


def prueba_una_parcela_sin_extension_no_deja_el_zoom_al_maximo():
    """`fit_bounds` sobre una figura sin tamaño deja mirando un tejado."""
    f = _ficha()
    lienzo = mapa.construir(f, [])
    igual(lienzo.options.get("zoom"), mapa.ZOOM_INMUEBLE,
          "sin geometría se centra en el punto con un zoom razonable")


def prueba_el_credito_del_ri_va_en_el_mapa():
    html, _ = _html()
    cierto("Registro Inmobiliario" in html,
           "el crédito del RI tiene que ir en el mapa: sus datos, su crédito")


def prueba_el_mapa_no_devuelve_nada_al_servidor():
    """Aquí el mapa solo enseña. Si algún día devolviera clics, cada interacción
    de la página podría lanzar otra consulta de once segundos al RI."""
    texto = open(os.path.join(os.path.dirname(AQUI), "app.py"),
                 encoding="utf-8").read()
    cierto("returned_objects=[]" in texto,
           "st_folium tiene que llamarse con returned_objects=[]: el mapa de "
           "esta herramienta no recoge nada")
    cierto("Draw" not in texto and "Draw" not in open(
               os.path.join(os.path.dirname(AQUI), "nucleo", "mapa.py"),
               encoding="utf-8").read(),
           "y no lleva control de dibujo: no se pide nada señalando")


def prueba_el_alto_cabe_con_los_botones_debajo():
    cierto(mapa.ALTO <= 500,
           "el mapa no puede ser tan alto que el botón de ir quede fuera de la "
           "pantalla de un teléfono: está en %d px" % mapa.ALTO)


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
    print("[OK] %d pruebas del mapa." % len(pruebas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
