# -*- coding: utf-8 -*-
"""Lo único de esta herramienta que habla con el mundo exterior.

Va solo en su módulo para que todo lo demás pueda probarse con el cable
desenchufado, y para que quede a la vista qué sale de aquí hacia dónde.

Lo que viaja al servidor del Registro Inmobiliario es **un número posicional**
dentro de una consulta OGC estándar. Nada más: ni quién pregunta, ni desde dónde,
ni qué hizo antes.

El servidor es `atlas.ri.gob.do`, el mismo GeoServer del que se sirve el portal
oficial `servicios.ri.gob.do/ConsultaParcelario`, y el mismo que ya consulta el
Visor Parcelario del hub.

## Las tres cosas medidas el 2026-08-21 que explican el módulo entero

**1. El campo `Posicional` no está indexado, y se nota.** Buscar un posicional
tarda 11.1–11.5 s en la capa de aprobadas (730 084 registros), 4.6–7.7 s en
previo2017 (361 793) y 0.2–0.4 s en anuladas (11 746). Para comparar, una consulta
espacial sobre las mismas capas tarda de 0.06 a 0.22 s: dos órdenes de
diferencia.

**2. Hay que mirar las tres capas y no se pueden pedir de una vez.** El
posicional no dice en cuál está —el caso que originó la herramienta estaba en
previo2017, no en aprobadas—. WFS 2.0 admite varios `typeNames` con un
`CQL_FILTER` por tipo, y el GeoServer del RI responde **HTTP 500** a esa petición:
está probado, no es una mejora pendiente.

**3. Por eso las tres van EN PARALELO**: 15.9 s en serie contra 11.1 s a la vez.
Sigue siendo *una consulta por acción pedida a propósito* —el usuario pulsó un
botón una vez— y las tres capas son un detalle de cómo el RI reparte su dato.

## Y una regla que no es técnica

**Se consulta como consultaría una persona.** El portal oficial pone un reCAPTCHA
delante de cada consulta y este servicio no lo tiene; el límite se lo pone la
herramienta a sí misma. Un posicional por acción del usuario, identificación
honesta, y **nunca un barrido**: no se recorren números, no se resuelven listas y
no se cachea el parcelario.
"""

import concurrent.futures
import json
import re
import time

import requests

# ----------------------------------------------------------------- servicio --

BASE = "https://atlas.ri.gob.do/geoserver/ows"

# El WMS se declara aquí aunque este módulo no lo llame: las teselas del
# parcelario las pide el navegador del usuario, igual que en el portal oficial.
# Vive junto a su hermano para que quien busque «a dónde sale esta herramienta»
# lo encuentre todo en un sitio.
WMS = "https://atlas.ri.gob.do/geoserver/wms"

PORTAL_OFICIAL = "https://servicios.ri.gob.do/ConsultaParcelario"

# Honesto y con dónde reclamar. Si el RI quiere cortar esto algún día, tiene que
# poder identificarlo y saber a quién escribir. **Dice el nombre de ESTA
# herramienta y no el del Visor Parcelario**, aunque el módulo venga de allí: dos
# herramientas identificándose igual dejan al RI sin forma de distinguir cuál le
# está costando qué.
AGENTE = "Agrimensura-LocalizadorPosicional/1.0 (+https://agrimensura.com.do)"

# El sistema en el que el RI sirve y recibe.
EPSG = 32619
ZONA = 19
CRS_URN = "urn:ogc:def:crs:EPSG::%d" % EPSG

# Medido: la peor capa tarda 11.5 s. Un servidor que pase de esto ya está roto, y
# esperarle no lo arregla — solo se lo cobra al usuario, que además no es
# agrimensor y no sabe que el RI es lento.
ESPERA = 45

# Lo que se espera antes del único reintento. Es una constante del módulo, y no
# un número escrito dentro de `_consultar`, para que las pruebas puedan ponerla a
# cero: una batería que duerme de verdad tarda más y no comprueba nada mejor.
PAUSA_REINTENTO = 1.5

# Cuántos resultados se traen como mucho. Un posicional debería devolver uno, y
# el tope está por si el RI publicara varios con el mismo número — que pasa: el
# Visor Parcelario encontró dos parcelas distintas compartiendo `Posicional`.
# Sirve para no traerse una capa entera si algún día el filtro fallara.
TOPE = 20


# ------------------------------------------------------------------- capas --

# Las tres capas de resultantes. **Las parcelas históricas NO están aquí**: no
# tienen campo `Posicional`, y pedírselo devuelve un error del servidor en vez de
# una lista vacía.
#
# Los campos son los que declara `DescribeFeatureType`, leídos el 2026-08-21, y
# `Posicional` es `xsd:string` en las tres — de ahí que el filtro CQL vaya con
# comillas.
CAPAS = {
    "aprobadas": {
        "tipo": "Aprobados:Aprobados",
        "etiqueta": "Parcela aprobada",
        "nota": "",
        "campos": ("Posicional", "Expediente", "Operacion", "Provincia",
                   "Municipio", "FechaInsc", "Area"),
        "color": "#1B7F3B",
    },
    "previo2017": {
        "tipo": "ResultantesSicyp:AprobadosAnterior2017",
        "etiqueta": "Resultante aprobada antes de 2017",
        "nota": "",
        "campos": ("Posicional", "Expediente", "Provincia", "Municipio",
                   "Area"),
        "color": "#B08900",
    },
    "anuladas": {
        "tipo": "Anulados:Anulados",
        "etiqueta": "Parcela ANULADA",
        # **Las anuladas entran a propósito y se avisan a gritos.** Que el
        # posicional de alguien corresponda a una resultante anulada es justo lo
        # que no se puede descubrir tarde. Esconderla sería lo cómodo y lo peor.
        "nota": "Esta resultante fue **anulada** por el Registro Inmobiliario. "
                "El punto es donde estuvo, pero la parcela ya no está vigente: "
                "consulte al RI antes de tomar cualquier decisión.",
        "campos": ("Posicional", "Expediente", "Operacion", "FechaInsc",
                   "Area"),
        "color": "#C1272D",
    },
}

# El orden en que se consultan y en que se enseñan los resultados. Las aprobadas
# primero porque son las más y las que casi siempre aciertan; las anuladas al
# final porque son la excepción — pero cuando salen, salen con su aviso.
ORDEN = ("aprobadas", "previo2017", "anuladas")

CAMPO_POSICIONAL = "Posicional"
CAMPO_AREA = "Area"


# ------------------------------------------------------------------ errores --

class ErrorRI(Exception):
    """Raíz de los problemas de esta capa. No se lanza directamente."""


class PosicionalInvalido(ErrorRI):
    """Lo que se escribió no puede ser un posicional. Ni se sale a la red."""


class ServidorCaido(ErrorRI):
    """El servidor del RI no contestó. **El problema no es del usuario.**

    Existe como clase aparte a propósito: «el servidor no contesta» y «ese
    posicional no existe» son dos mensajes completamente distintos, y darle el
    equivocado manda a revisar un número que estaba bien escrito.
    """


# -------------------------------------------------------------- la entrada --

# Cuántos dígitos tiene un posicional. **Medido el 2026-08-21 sobre 2 088
# parcelas reales de cinco provincias: 2 087 tenían exactamente doce dígitos y
# ninguna otra longitud apareció.** La restante no traía posicional.
DIGITOS = 12

# Lo que se le quita a lo que el usuario pegue. Un posicional copiado de un PDF o
# de un WhatsApp llega con espacios, guiones o puntos de millar; rechazarlo por
# eso sería culpar al usuario de cómo lo copió.
_BASURA = re.compile(r"[\s\-\.  ,]")


def limpiar(texto):
    """Lo que escribió el usuario -> el número con el que se puede consultar.

    Lanza `PosicionalInvalido` si no queda nada con lo que buscar. **No rechaza
    por longitud**, y eso es deliberado: los 2 087 medidos tenían doce dígitos,
    pero el país tiene 155 municipios y la muestra fueron cinco provincias.
    Rechazar de plano un número de once dígitos dejaría la herramienta inservible
    para ese inmueble y le echaría la culpa a quien lo escribió bien; consultarlo
    cuesta once segundos y devuelve «no existe», que es información. Quien llame
    puede preguntar por `longitud_rara` para avisar sin bloquear.
    """
    limpio = _BASURA.sub("", str(texto or ""))
    if not limpio:
        raise PosicionalInvalido(
            "Escriba el número posicional del inmueble. Son doce dígitos, y "
            "aparece en la certificación o en el plano del Registro "
            "Inmobiliario.")
    if not limpio.isdigit():
        raise PosicionalInvalido(
            "El número posicional son **solo dígitos** y llegó «%s». Si lo que "
            "tiene es una designación catastral del tipo 999-X-1-B-18 o un "
            "número de expediente, esta herramienta no los busca: use el Visor "
            "Parcelario." % str(texto).strip()[:40])
    return limpio


def longitud_rara(limpio):
    """Un aviso, no un bloqueo. `None` si la longitud es la esperada."""
    if len(limpio) == DIGITOS:
        return None
    return ("Un número posicional suele tener **%d dígitos** y éste tiene %d. "
            "Se va a consultar igual, pero revise que no falte o sobre alguno."
            % (DIGITOS, len(limpio)))


# -------------------------------------------------------------- la consulta --

def _comillas(valor):
    """Un literal para CQL. La comilla simple se escapa duplicándola.

    `Posicional` es `xsd:string` en las tres capas, así que el valor va
    entrecomillado. El escape no es paranoia de inyección SQL: CQL se interpreta
    en el servidor ajeno y lo que se le mande tiene que ser lo que se quiso
    mandar.
    """
    return "'%s'" % str(valor).replace("'", "''")


def _pedir_http(url, parametros, espera):
    """Una petición de verdad. Devuelve `(codigo, texto)`.

    Es la única función del proyecto que toca la red, y se recibe como argumento
    para que las pruebas puedan sustituirla por un doble. No lanza por un código
    de error: devolver el 500 en vez de levantarlo deja que quien llama decida
    qué decir.
    """
    r = requests.get(url, params=parametros, timeout=espera,
                     headers={"User-Agent": AGENTE})
    return r.status_code, r.text


def parametros_de(capa, posicional, tope=TOPE):
    """Los parámetros de un `GetFeature`. Se expone para poder probarlos."""
    return {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": CAPAS[capa]["tipo"],
        "outputFormat": "application/json",
        "count": str(tope),
        "srsName": CRS_URN,
        "CQL_FILTER": "%s = %s" % (CAMPO_POSICIONAL, _comillas(posicional)),
    }


def _consultar(parametros, pedir=None, espera=ESPERA, url=BASE,
               pausa=None):
    """Una consulta WFS -> el `FeatureCollection` ya interpretado.

    Un solo reintento, y solo cuando el fallo fue de red o de servidor: contra un
    servidor único —no hay espejos del parcelario dominicano y no debería
    haberlos— insistir sobre un 4xx es pedirle otra vez lo que acaba de decir que
    no puede dar.
    """
    pedir = pedir or _pedir_http
    pausa = PAUSA_REINTENTO if pausa is None else pausa
    fallos = []

    for intento in (1, 2):
        arranque = time.time()
        try:
            codigo, texto = pedir(url, parametros, espera)
        except Exception as ex:                                   # noqa: BLE001
            # Tiempo agotado, DNS, certificado, conexión cortada a la mitad.
            # Todas significan lo mismo aquí y ninguna puede escapar como traza.
            fallos.append("%s" % ex.__class__.__name__)
            if intento == 1:
                time.sleep(pausa)
            continue

        if codigo != 200:
            fallos.append("HTTP %s" % codigo)
            if codigo < 500 or intento == 2:
                break
            time.sleep(pausa)
            continue

        try:
            documento = json.loads(texto)
        except ValueError:
            # GeoServer devuelve 200 con un `ServiceExceptionReport` en XML
            # cuando la consulta le parece mal formada. Un 200 no garantiza
            # JSON, y ese XML es la pista de un error nuestro, no suyo.
            fallos.append("respuesta ilegible (¿excepción del servicio?)")
            break

        if not isinstance(documento, dict) or "features" not in documento:
            fallos.append("respuesta sin «features»")
            break

        documento["_segundos"] = time.time() - arranque
        return documento

    raise ServidorCaido("; ".join(fallos))


def mensaje_de_caida(detalle=""):
    """Lo que se le enseña al usuario cuando el RI no contesta.

    Vive aquí, junto a la excepción, y no en `app.py`: es la única salida que le
    queda a quien no consiguió su respuesta, y tiene que decir tres cosas — que
    no es culpa suya, que puede volver a intentarlo, y a dónde ir mientras tanto.
    """
    return ("El servidor del **Registro Inmobiliario** no respondió%s. No es un "
            "problema de su número ni de su conexión: es el servicio del RI, que "
            "a veces tarda o se cae. Espere unos minutos y vuelva a intentarlo, "
            "o consulte el portal oficial: %s"
            % (" (%s)" % detalle if detalle else "", PORTAL_OFICIAL))


def por_posicional(posicional, capas=ORDEN, pedir=None, tope=TOPE,
                   en_paralelo=True, pausa=None):
    """Busca el posicional en las capas de resultantes. **A la vez, no en fila.**

    Devuelve `{clave_de_capa: documento}` con las que contestaron, y lanza
    `ServidorCaido` solo si **ninguna** contestó: que una capa falle mientras otra
    trae la parcela no es motivo para negarle el resultado al usuario. Cuáles
    fallaron se puede saber por las que faltan en el diccionario.

    Medido el 2026-08-21: 15.9 s en serie contra 11.1 s en paralelo, porque la
    capa de aprobadas tarda ella sola once segundos y las otras dos caben dentro
    de esa espera.

    `en_paralelo=False` existe para las pruebas, que necesitan un orden
    determinista al comprobar qué se le pidió a quién.
    """
    limpio = limpiar(posicional)
    trabajos = {c: parametros_de(c, limpio, tope=tope) for c in capas}
    salida, caidas = {}, []

    def una(capa):
        return _consultar(trabajos[capa], pedir=pedir, pausa=pausa)

    if not en_paralelo:
        for capa in capas:
            try:
                salida[capa] = una(capa)
            except ServidorCaido as ex:
                caidas.append("%s: %s" % (CAPAS[capa]["etiqueta"], ex))
    else:
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, len(trabajos)),
                thread_name_prefix="ri") as grupo:
            lanzados = {grupo.submit(una, capa): capa for capa in capas}
            for hecho in concurrent.futures.as_completed(lanzados):
                capa = lanzados[hecho]
                try:
                    salida[capa] = hecho.result()
                except ServidorCaido as ex:
                    caidas.append("%s: %s" % (CAPAS[capa]["etiqueta"], ex))

    if not salida:
        raise ServidorCaido("; ".join(caidas) or "sin respuesta")
    return salida


# --------------------------------------------------------------- el contrato --

_CAMPO_XSD = re.compile(r'<xsd:element[^>]*name="([^"]+)"')


def campos_declarados(capa, pedir=None):
    """Los nombres de campo que el servidor dice tener en esa capa.

    Es un `DescribeFeatureType`: el servidor devuelve su esquema y **ni una sola
    parcela**. Existe para que la prueba de red pueda comprobar que las tres
    capas siguen sirviendo el campo `Posicional` **sin traerse el identificador
    de ningún inmueble real** — que es justo lo que no puede entrar en este
    repositorio.
    """
    pedir = pedir or _pedir_http
    parametros = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "DescribeFeatureType",
        "typeNames": CAPAS[capa]["tipo"],
    }
    try:
        codigo, texto = pedir(BASE, parametros, ESPERA)
    except Exception as ex:                                       # noqa: BLE001
        raise ServidorCaido(
            "No se pudo pedir el esquema de «%s» (%s)."
            % (CAPAS[capa]["etiqueta"], ex.__class__.__name__))
    if codigo != 200:
        raise ServidorCaido(
            "El RI devolvió HTTP %s al pedirle el esquema de «%s»."
            % (codigo, CAPAS[capa]["etiqueta"]))
    return _CAMPO_XSD.findall(texto)
