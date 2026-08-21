# -*- coding: utf-8 -*-
"""Los dos enlaces para ir hasta el inmueble: Google Maps y Waze.

Es la mitad visible del producto. Todo lo demás —la consulta al Registro
Inmobiliario, el centroide, el mapa— existe para que estos dos enlaces apunten al
sitio correcto.

## Lo que puede salir mal aquí, y no da ningún error

**El signo de la longitud.** La República Dominicana está en el oeste, así que su
longitud es negativa. Una longitud sin signo pone el inmueble en Arabia Saudí, a
7 500 km, y los dos servicios abren el mapa tan contentos: no hay ninguna
coordenada inválida, solo una equivocada. Por eso las pruebas de este módulo leen
el número **de vuelta desde la URL** en vez de comparar la cadena con otra cadena
que se escribió igual.

**El orden.** Los dos servicios piden `lat,lon`, que es el orden contrario al de
`(este, norte)` de UTM y al de `(lon, lat)` de GeoJSON. Cambiarlos deja el punto
en el mar, frente a la costa de Somalia.

**Los decimales.** Cinco decimales de grado son 1.1 m en esta latitud y seis son
11 cm. Se dan seis: el punto ya se calculó con precisión de milímetros y
truncarlo aquí sería tirar la única parte del trabajo que el usuario va a usar de
verdad. Más de seis no aporta nada — ningún GPS de teléfono los distingue.

## Por qué modo navegación y no modo mapa

Lo que se pidió es «ir allá». Los dos servicios tienen una forma de enseñar un
punto y otra de trazar la ruta hasta él; se usa la segunda. Quien solo quiera
mirar tiene el mapa de la propia página encima.
"""

from urllib.parse import quote

# Cuántos decimales de grado llevan los enlaces. Ver la cabecera: seis son 11 cm.
DECIMALES = 6

# Los dos servicios, con la forma de URL que cada uno documenta para navegación.
#
# Google Maps usa su «Maps URLs» con `api=1`, que es la forma estable y
# documentada: `dir` con `destination` abre la ruta hacia el punto. La variante
# antigua `maps?q=` sigue funcionando pero enseña el punto en vez de trazar hacia
# él.
#
# Waze usa `waze.com/ul` con `navigate=yes`, que en un teléfono abre la
# aplicación y en un escritorio abre su mapa en vivo. Sin `navigate=yes` deja el
# mapa centrado y el usuario tiene que pulsar «Ir» a mano.
GOOGLE = "https://www.google.com/maps/dir/?api=1&destination=%s"
WAZE = "https://www.waze.com/ul?ll=%s&navigate=yes"


def _par(lat, lon):
    """`lat,lon` con los decimales fijados. El signo del oeste va dentro."""
    return "%.*f,%.*f" % (DECIMALES, lat, DECIMALES, lon)


def coordenadas_para_pegar(lat, lon):
    """El par tal cual, para copiarlo a mano en cualquier otra aplicación.

    Se ofrece además de los dos botones porque no todo el mundo usa Google Maps o
    Waze: hay quien tiene Organic Maps, un GPS de mano o simplemente quiere
    pegarlo en un mensaje. Es el mismo texto que llevan los dos enlaces dentro, y
    sale de la misma función para que no puedan separarse.
    """
    return _par(lat, lon)


def google_maps(lat, lon):
    """La ruta hasta el punto en Google Maps."""
    return GOOGLE % quote(_par(lat, lon), safe="")


def waze(lat, lon):
    """La ruta hasta el punto en Waze."""
    return WAZE % quote(_par(lat, lon), safe="")


def enlaces(lat, lon):
    """Los dos, con su rótulo. En el orden en que se pintan.

    Google Maps va primero porque es el que todo el mundo tiene; Waze segundo
    porque es el que usa quien conduce a diario en Santo Domingo.
    """
    return (
        {"nombre": "Google Maps", "url": google_maps(lat, lon),
         "icono": "🗺️",
         "ayuda": "Abre la ruta hasta el inmueble en Google Maps."},
        {"nombre": "Waze", "url": waze(lat, lon),
         "icono": "🚗",
         "ayuda": "Abre la ruta hasta el inmueble en Waze."},
    )
