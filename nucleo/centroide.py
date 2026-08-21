# -*- coding: utf-8 -*-
"""El punto al que se manda al usuario. Es la herramienta entera.

Todo lo demás de este proyecto —la consulta, el mapa, los dos enlaces— existe
para entregar un par de coordenadas. Si ese par está mal, no hay ningún síntoma:
el mapa se dibuja bien, Waze abre, y el usuario se entera al llegar.

## Por qué no basta con el centroide

El centroide de área de un polígono cóncavo **puede caer fuera del polígono**. Es
geometría elemental y no una rareza: una parcela en L, en U o en media luna tiene
su centro de masa en el aire.

Medido el 2026-08-21 sobre parcelas reales del Registro Inmobiliario, comparando
el centroide contra su propio polígono:

    zona urbana (Ensanche Naco, 1 km2) ...... 534 anillos ·  0 fuera  (0.00 %)
    zona rural (Cibao, Sur y Este) .......... 412 anillos ·  5 fuera  (1.21 %)
                                              peor alejamiento: 50.94 m

En la ciudad las parcelas son rectángulos y el defecto **no aparece nunca**. Por
eso hay que escribirlo aquí: quien construya o revise esto probando con una
manzana de Santo Domingo verá el 100 % de aciertos y concluirá que la
comprobación sobra.

## Qué se hace en su lugar

1. Se calcula el centroide de área, con los huecos restados.
2. Se comprueba que cae dentro.
3. Si no cae dentro, se sustituye por un **punto interior garantizado**: se corta
   la figura con la horizontal que pasa por el centroide y se toma el punto medio
   del tramo interior más largo. Es el criterio de `ST_PointOnSurface` de
   PostGIS. Se eligió por dos motivos: es determinista —el mismo polígono da
   siempre el mismo punto, y dos consultas del mismo inmueble no pueden dar
   destinos distintos— y no necesita ninguna dependencia nueva.
4. Se devuelve **si hubo que ajustar**, porque la pantalla tiene que decirlo.
   Quien va a conducir hasta allí tiene derecho a saber si el punto es el centro
   de su terreno o un punto interior elegido porque el centro caía fuera.

## La traslación al primer vértice no es un adorno

En UTM dominicano una coordenada ronda 400 000 en el este y 2 050 000 en el
norte; el producto cruzado llega a 8·10^11 y un `float` guarda 16 cifras. Sobre
una parcela de 200 m² —el tamaño del caso que originó esta herramienta— eso deja
el centroide con menos precisión de la que se imprime. Restando el primer vértice
los productos bajan a la escala de la parcela, y el centroide se devuelve sumando
la traslación de vuelta. Es la misma razón por la que `medir.py` del hub lo hace.

## Los anillos

Todo lo de aquí recibe `[(puntos, es_hueco)]`, la misma forma que usa el hub:
cada anillo es una lista de `(este, norte)` **sin repetir el primer vértice al
final**, y `es_hueco` distingue un patio interior de un contorno.
"""

import math

# Área por debajo de la cual un anillo no es una parcela sino un resto de la
# geometría del RI. El número está medido y viene del Visor Parcelario: sobre 934
# anillos de una manzana del Ensanche Naco, 43 estaban por debajo de 1 m² —el
# mayor de ellos 0.042 m²— y los 891 restantes por encima de 11.3 m². Entre los
# dos grupos hay un factor de 271 y ningún anillo en medio, así que el corte no
# es una frontera discutible: es un hueco.
AREA_MINIMA_ANILLO = 1.0

# Cuántas horizontales se prueban si la del centroide no da ningún tramo
# interior. Es una red de seguridad para figuras patológicas —una que se toque a
# sí misma justo a esa altura—, no el camino normal: en las 946 parcelas reales
# medidas no hizo falta ni una vez.
INTENTOS_DE_RESCATE = 21


class ErrorCentroide(ValueError):
    """La geometría no permite calcular un punto. Se dice, no se inventa."""


# ------------------------------------------------------------------ básicos --

def area_con_signo(puntos):
    """Área de Gauss. Positiva si los vértices van en sentido antihorario.

    Trasladada al primer vértice; ver la cabecera del módulo.
    """
    n = len(puntos)
    if n < 3:
        return 0.0
    x0, y0 = puntos[0]
    suma = 0.0
    for i in range(n):
        x1, y1 = puntos[i]
        x2, y2 = puntos[(i + 1) % n]
        suma += (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    return suma / 2.0


def area(puntos):
    """Superficie en metros cuadrados, siempre positiva."""
    return abs(area_con_signo(puntos))


def _centroide_de_anillo(puntos):
    """`(este, norte, area_con_signo)` de un anillo suelto.

    Devuelve el área junto al punto porque quien compone varios anillos la
    necesita como peso, y calcularla dos veces es pedirle a dos funciones que
    coincidan.
    """
    a = area_con_signo(puntos)
    if abs(a) < 1e-12:
        return None
    x0, y0 = puntos[0]
    cx = cy = 0.0
    n = len(puntos)
    for i in range(n):
        x1, y1 = puntos[i][0] - x0, puntos[i][1] - y0
        x2, y2 = puntos[(i + 1) % n][0] - x0, puntos[(i + 1) % n][1] - y0
        cruz = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cruz
        cy += (y1 + y2) * cruz
    return (x0 + cx / (6.0 * a), y0 + cy / (6.0 * a), a)


def utiles(anillos):
    """Los anillos que son geometría de verdad, con el resto descartado.

    Se quitan los que tienen menos de tres vértices y las astillas de menos de
    un metro cuadrado, que el RI adjunta a parcelas normales como si fueran un
    polígono suyo.
    """
    return [(p, hueco) for p, hueco in anillos
            if len(p) >= 3 and area(p) >= AREA_MINIMA_ANILLO]


# ------------------------------------------------------- centroide de área --

def centroide_de_area(anillos):
    """El centro de masa de la figura, con los huecos restados.

    **El sentido de giro no importa y eso hay que forzarlo.** El RI no garantiza
    en qué sentido publica sus anillos, y el área de Gauss cambia de signo con
    él: si el peso de cada anillo fuera el área con signo tal cual, la mitad de
    las parcelas del país saldrían con el punto en otro sitio. Se toma el valor
    absoluto y el signo lo pone la condición de hueco, que es lo que de verdad
    decide si un anillo suma o resta.
    """
    limpios = utiles(anillos)
    if not limpios:
        raise ErrorCentroide(
            "La geometría llegó sin ningún anillo utilizable.")

    peso_total = 0.0
    suma_x = suma_y = 0.0
    for puntos, hueco in limpios:
        parcial = _centroide_de_anillo(puntos)
        if parcial is None:
            continue
        cx, cy, con_signo = parcial
        peso = abs(con_signo) * (-1.0 if hueco else 1.0)
        suma_x += cx * peso
        suma_y += cy * peso
        peso_total += peso

    if abs(peso_total) < 1e-12:
        raise ErrorCentroide(
            "Los vértices no encierran ninguna superficie: puede que el "
            "Registro Inmobiliario haya publicado la parcela con la geometría "
            "incompleta.")
    return (suma_x / peso_total, suma_y / peso_total)


# --------------------------------------------------------- dentro del sitio --

def _dentro_de_anillo(punto, puntos):
    """Ray casting horizontal. El borde cuenta como dentro por el lado de abajo.

    La condición `(y1 > y) != (y2 > y)` es media abierta a propósito: trata cada
    vértice una sola vez, así que una horizontal que pase exactamente por uno no
    cuenta dos cruces y no invierte el resultado. Es el detalle que hace que esto
    funcione sobre polígonos reales, donde los vértices caen en números redondos
    mucho más a menudo de lo que uno esperaría.
    """
    x, y = punto
    adentro = False
    n = len(puntos)
    for i in range(n):
        x1, y1 = puntos[i]
        x2, y2 = puntos[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            corte = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < corte:
                adentro = not adentro
    return adentro


def dentro(punto, anillos):
    """¿El punto está en la parcela? Un patio interior **no** es la parcela."""
    limpios = utiles(anillos)
    en_exterior = any(_dentro_de_anillo(punto, p)
                      for p, hueco in limpios if not hueco)
    if not en_exterior:
        return False
    return not any(_dentro_de_anillo(punto, p)
                   for p, hueco in limpios if hueco)


# ------------------------------------------------- el punto interior seguro --

def _cortes_horizontales(anillos, y):
    """Las abscisas donde la horizontal `y` cruza cualquier lado de la figura."""
    cortes = []
    for puntos, _ in anillos:
        n = len(puntos)
        for i in range(n):
            x1, y1 = puntos[i]
            x2, y2 = puntos[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                cortes.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return sorted(cortes)


def _tramo_interior_mas_largo(anillos, y):
    """`(x_medio, longitud)` del tramo interior más ancho a esa altura, o None.

    Se comprueba tramo por tramo si su punto medio está dentro, en vez de suponer
    que los cortes se alternan dentro/fuera. Con huecos y con polígonos que se
    tocan, esa suposición falla — y falla en silencio, devolviendo un punto en el
    patio.
    """
    cortes = _cortes_horizontales(anillos, y)
    mejor = None
    for izquierda, derecha in zip(cortes, cortes[1:]):
        ancho = derecha - izquierda
        if ancho <= 0:
            continue
        medio = (izquierda + derecha) / 2.0
        if not dentro((medio, y), anillos):
            continue
        if mejor is None or ancho > mejor[1]:
            mejor = (medio, ancho)
    return mejor


def punto_interior(anillos):
    """Un punto garantizado dentro de la figura. Determinista.

    Se prueba primero la horizontal del centroide, que es la que da el punto más
    natural —el más «centrado» de los que se pueden justificar—. Si esa altura no
    produce ningún tramo interior, se barre la figura con horizontales repartidas
    entre sus extremos y se toma el tramo más ancho de todos: el punto más
    holgado, que es el que menos se acerca a un lindero.
    """
    limpios = utiles(anillos)
    if not limpios:
        raise ErrorCentroide("La geometría llegó sin ningún anillo utilizable.")

    try:
        _, cy = centroide_de_area(limpios)
        mejor = _tramo_interior_mas_largo(limpios, cy)
        if mejor is not None:
            return (mejor[0], cy)
    except ErrorCentroide:
        pass

    todos = [p for puntos, _ in limpios for p in puntos]
    y_min = min(y for _, y in todos)
    y_max = max(y for _, y in todos)
    if y_max - y_min <= 0:
        raise ErrorCentroide(
            "La parcela llegó plana: todos sus vértices están en la misma "
            "línea, así que no encierra ninguna superficie.")

    mejor_global = None
    for i in range(1, INTENTOS_DE_RESCATE + 1):
        y = y_min + (y_max - y_min) * i / (INTENTOS_DE_RESCATE + 1.0)
        tramo = _tramo_interior_mas_largo(limpios, y)
        if tramo is None:
            continue
        if mejor_global is None or tramo[1] > mejor_global[1]:
            mejor_global = (tramo[0], tramo[1], y)

    if mejor_global is None:
        raise ErrorCentroide(
            "No se pudo situar un punto dentro de la parcela: la geometría que "
            "publicó el Registro Inmobiliario no encierra un área utilizable.")
    return (mejor_global[0], mejor_global[2])


# --------------------------------------------------------------- la entrada --

def punto_para_ir(anillos):
    """`((este, norte), ajustado)` — el punto al que mandar al usuario.

    `ajustado` es `False` cuando el punto es el centroide tal cual, que es el
    98.8 % de los casos rurales y el 100 % de los urbanos, y `True` cuando hubo
    que moverlo porque el centroide caía fuera. **La pantalla enseña esa
    diferencia**: decir «se ajustó» siempre sería mentir casi siempre, y no
    decirlo nunca escondería justo el caso en que el punto no es el centro.

    **Con varios contornos se va al mayor.** El RI publica `MultiPolygon`, así
    que un inmueble puede llegar partido en dos trozos separados; el centroide
    conjunto caería entre los dos, en terreno de otro. Se elige el trozo de más
    superficie y se sitúa el punto dentro de él, con sus propios huecos.
    """
    limpios = utiles(anillos)
    if not limpios:
        raise ErrorCentroide(
            "El Registro Inmobiliario devolvió la parcela sin geometría "
            "utilizable, así que no se puede decir dónde está.")

    exteriores = [(p, h) for p, h in limpios if not h]
    if not exteriores:
        raise ErrorCentroide(
            "La geometría llegó con huecos y sin contorno.")

    if len(exteriores) > 1:
        mayor = max(exteriores, key=lambda par: area(par[0]))
        limpios = [(mayor[0], False)] + [
            (p, True) for p, h in limpios
            if h and _dentro_de_anillo(p[0], mayor[0])]

    punto = centroide_de_area(limpios)
    if dentro(punto, limpios):
        return punto, False
    return punto_interior(limpios), True


# ------------------------------------------------------------------- extras --

def perimetro(puntos):
    n = len(puntos)
    return sum(math.dist(puntos[i], puntos[(i + 1) % n]) for i in range(n))


def superficie(anillos):
    """El área de la figura en metros cuadrados, con los huecos restados."""
    limpios = utiles(anillos)
    return (sum(area(p) for p, hueco in limpios if not hueco)
            - sum(area(p) for p, hueco in limpios if hueco))
