# -*- coding: utf-8 -*-
"""El mapa: dónde está el inmueble, sobre la foto de lo que hay en el terreno.

**Aquí el mapa solo enseña.** No se dibuja, no se pincha y no devuelve nada: la
consulta la hizo un campo de texto. Eso lo separa del Visor Parcelario y del
Extractor de calles, donde el mapa es la entrada.

Y por eso mismo el mapa de aquí tiene un trabajo distinto: **convencer**. Quien
llega con un número y sin conocer el sitio necesita reconocer el terreno para
creerse el resultado — el techo de la casa, el río, la curva de la carretera. Por
eso el fondo que se abre es el **satélite** y no el callejero, y por eso el punto
va sobre el contorno de la parcela y no solo.

## Las tres trampas que ya costaron caro en el hub, y que aquí están resueltas

1. **`folium` pone `maxZoom: 18` por defecto** en cualquier capa de teselas. Al
   ajustarse a una parcela pequeña el mapa llega a 19, y ahí las capas del RI
   quedaban encendidas y **con cero teselas dibujadas**: la parcela sobre el
   satélite y el parcelario de alrededor ausente, sin un error en la consola.
2. Al subir ese tope, **Leaflet toma el zoom máximo del mapa de la capa que más
   lejos llega** y dejaba acercarse hasta 20, donde la foto de satélite
   desaparece. El mismo fallo desde el otro lado.
3. Con `tiles=None`, folium **se traga** el `max_zoom` del constructor de `Map`:
   hay que ponerlo en `options["maxZoom"]` y comprobarlo en el bloque `L.map(`
   del HTML, porque una aserción sobre la constante de Python da verde con el
   fallo delante.

Los tres se descubrieron **mirando el mapa**, no leyendo el código, y los tres
tienen su prueba de regresión en `pruebas/test_mapa.py`.

## Y una cuarta, del Extractor de calles

`show=False` en el fondo que no está seleccionado **no es estética**. Sin él,
folium añade los dos y el navegador pide las teselas de los dos a la vez: los dos
proveedores viendo la zona que se está mirando aunque el usuario esté en uno
solo. El aviso legal promete que cada proveedor ve lo suyo; esto es lo que lo
hace verdad.
"""

import folium

from . import ri

# Más bajo que los 560 del Visor Parcelario. Allí el mapa es la herramienta y hay
# que poder moverse por él; aquí solo enseña un punto, y la página tiene que caber
# entera —resultado, coordenadas y los dos botones de ir— sin que el usuario
# tenga que desplazarse para encontrar el botón que ha venido a pulsar.
ALTO = 460

MAGENTA = "#A6318F"
GRIS = "#59595B"

# Los dos fondos de imagen, sin cuenta ni clave y con su crédito. Ninguno es el
# servidor de teselas de openstreetmap.org: su política de uso desaconseja
# expresamente que un producto se apoye en él.
#
# **El orden importa:** folium enseña el ÚLTIMO que se añade. El satélite va el
# último y es el que se ve al abrir; ver la cabecera.
FONDOS = (
    ("Calles",
     "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
     '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">'
     'OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'),
    ("Satélite",
     "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
     "MapServer/tile/{z}/{y}/{x}",
     "Imagen: Esri, Maxar, Earthstar Geographics"),
)

CREDITO_RI = ('Parcelario &copy; <a href="https://ri.gob.do" target="_blank" '
              'rel="noopener">Registro Inmobiliario</a>')

# Encuadre de partida cuando todavía no hay nada que enseñar: la República
# Dominicana entera. Sin esto, folium abre el mapa en el golfo de Guinea —el
# (0, 0)— y quien llega a buscar su inmueble tiene que encontrar el país a mano.
CENTRO_PAIS = (18.75, -70.16)
ZOOM_PAIS = 8

# A partir de este zoom el WMS del RI tiene sentido: por debajo, un país entero de
# polígonos catastrales es una mancha negra y una petición cara para su servidor.
ZOOM_MINIMO_PARCELARIO = 14

# Ver la trampa 1 de la cabecera. El WMS dibuja a la escala que se le pida, así
# que el tope solo tiene que ser mayor que el zoom máximo al que se pueda llegar.
ZOOM_MAXIMO_PARCELARIO = 22

# Hasta dónde llegan los fondos de imagen, y por tanto hasta dónde el mapa deja
# acercarse. Ver la trampa 2.
ZOOM_MAXIMO_FONDO = 19
ZOOM_MAXIMO_MAPA = ZOOM_MAXIMO_FONDO

# Zoom al que se abre sobre el inmueble encontrado. 18 enseña la manzana entera
# con su contexto —la calle, los vecinos—, que es lo que permite reconocer el
# sitio. A 19 se ve el techo y nada más, y quien no conoce la zona se pierde.
ZOOM_INMUEBLE = 18

# El estilo por defecto del GeoServer del RI **rellena** los polígonos. A opacidad
# 1 el parcelario tapa el satélite entero y se pierde justo lo que hace falta ver.
OPACIDAD_PARCELARIO = 0.30


def _lienzo():
    mapa = folium.Map(location=CENTRO_PAIS, zoom_start=ZOOM_PAIS,
                      tiles=None, control_scale=True)
    # El tope se pone aquí y no en el constructor: ver la trampa 3.
    mapa.options["maxZoom"] = ZOOM_MAXIMO_MAPA
    return mapa


def _con_fondos(mapa):
    for indice, (nombre, plantilla, credito) in enumerate(FONDOS):
        folium.TileLayer(tiles=plantilla, attr=credito, name=nombre,
                         max_zoom=ZOOM_MAXIMO_FONDO, control=True,
                         show=(indice == len(FONDOS) - 1)).add_to(mapa)
    return mapa


def _con_parcelario(mapa, capa):
    """El parcelario del RI de fondo, **solo la capa donde se encontró**.

    El Visor Parcelario enciende las cuatro y deja al usuario apagarlas. Aquí eso
    sería un selector de capas catastrales delante de alguien que no sabe qué es
    una capa catastral: se enseña la del inmueble encontrado, apagable, y ya.
    """
    definicion = ri.CAPAS[capa]
    folium.raster_layers.WmsTileLayer(
        url=ri.WMS,
        layers=definicion["tipo"],
        name="Parcelario del RI",
        fmt="image/png",
        # Sin `transparent=True`, GeoServer devuelve un PNG con fondo blanco
        # opaco y la capa tapa el satélite entero.
        transparent=True,
        version="1.1.1",
        attr=CREDITO_RI,
        overlay=True,
        control=True,
        show=True,
        min_zoom=ZOOM_MINIMO_PARCELARIO,
        max_zoom=ZOOM_MAXIMO_PARCELARIO,
        opacity=OPACIDAD_PARCELARIO,
    ).add_to(mapa)
    return mapa


def _globo(f):
    lineas = ["<b>Posicional %s</b>" % f["posicional"], f["etiqueta"]]
    if f["area_declarada"] is not None:
        lineas.append("%.2f m²" % f["area_declarada"])
    if f["punto_ajustado"]:
        lineas.append("<i>Punto movido al interior de la parcela</i>")
    return "<br>".join(lineas)


def construir(ficha, anillos_geo):
    """El mapa del inmueble encontrado, listo para `st_folium`.

    `anillos_geo` es `[(puntos_en_grados, es_hueco)]`, ya proyectado por quien
    llama: la proyección se hace **una sola vez y fuera**, para que el contorno
    del mapa y el punto de los enlaces de navegación no puedan salir de dos
    cálculos distintos.
    """
    mapa = _con_parcelario(_con_fondos(_lienzo()), ficha["capa"])

    # El contorno primero, el punto encima: el punto es lo que se ha venido a ver
    # y ninguna línea puede taparlo.
    for puntos, hueco in anillos_geo:
        grados = [(lat, lon) for lon, lat in puntos]
        folium.Polygon(
            grados,
            color=ficha["color"], weight=3,
            fill=True, fill_opacity=0.10 if hueco else 0.22,
            dash_array="5 5" if hueco else None,
            tooltip="Parcela del posicional %s" % ficha["posicional"],
        ).add_to(mapa)

    folium.Marker(
        (ficha["lat"], ficha["lon"]),
        tooltip="Aquí está el inmueble",
        popup=folium.Popup(_globo(ficha), max_width=260),
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
    ).add_to(mapa)

    # Un círculo debajo de la chincheta: en el móvil el icono se confunde con
    # cualquier otro marcador del fondo, y esto deja claro cuál es el punto.
    folium.CircleMarker(
        (ficha["lat"], ficha["lon"]), radius=7,
        color=MAGENTA, weight=2, fill=True, fill_opacity=0.85,
    ).add_to(mapa)

    folium.LayerControl(collapsed=True).add_to(mapa)
    _encajar(mapa, anillos_geo, ficha)
    return mapa


def _encajar(mapa, anillos_geo, ficha):
    """Ajusta el encuadre a la parcela, o al punto si la parcela no tiene tamaño.

    `fit_bounds` sobre una figura sin extensión deja el zoom al máximo mirando un
    tejado, así que el caso degenerado se trata aparte.
    """
    puntos = [(lat, lon) for anillo, _ in anillos_geo for lon, lat in anillo]
    if not puntos:
        mapa.location = [ficha["lat"], ficha["lon"]]
        mapa.options["zoom"] = ZOOM_INMUEBLE
        return mapa

    lats = [p[0] for p in puntos]
    lons = [p[1] for p in puntos]
    if max(lats) - min(lats) < 1e-9 and max(lons) - min(lons) < 1e-9:
        mapa.location = [lats[0], lons[0]]
        mapa.options["zoom"] = ZOOM_INMUEBLE
        return mapa
    mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    return mapa
