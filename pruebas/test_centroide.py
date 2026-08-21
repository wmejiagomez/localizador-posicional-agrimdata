# -*- coding: utf-8 -*-
"""El punto al que se manda al usuario. Es toda la herramienta.

Estas pruebas existen por una medición del 2026-08-21: sobre 412 anillos
exteriores de parcelas rurales reales, **5 tenían el centroide de área fuera de
su propio polígono**, el peor a 50.94 m del vértice más cercano. En zona urbana
fueron 0 de 534, y por eso el defecto no se ve construyendo con ejemplos de
ciudad.

Un punto 51 m fuera manda al usuario al terreno del vecino y **no produce ningún
error**: el mapa se ve perfecto, el enlace de Waze abre, y la única forma de
enterarse es llegar allí. De ahí que la comprobación más importante de este
archivo no sea que el punto esté bien puesto, sino que **esté dentro**.

Los polígonos de aquí son figuras geométricas con centroide conocido de
antemano. No hay ni un dato del Registro Inmobiliario: el que se usó para medir
identifica un inmueble real y no entra en el repositorio.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import centroide                                       # noqa: E402

FALLOS = []


def igual(a, b, tolerancia, que):
    if abs(a - b) > tolerancia:
        FALLOS.append("%s: esperaba %.6f, llegó %.6f (tolerancia %g)"
                      % (que, b, a, tolerancia))


def cierto(condicion, que):
    if not condicion:
        FALLOS.append(que)


# --------------------------------------------------------------- las figuras --

# Un rectángulo de 10 x 4 con la esquina en el origen. Centroide en (5, 2).
RECTANGULO = [(0, 0), (10, 0), (10, 4), (0, 4)]

# Un triángulo rectángulo de catetos 6 y 3. El centroide de un triángulo es la
# media de sus vértices: (2, 1).
TRIANGULO = [(0, 0), (6, 0), (0, 3)]

# Una L. **Es el caso que da nombre a este archivo.** Se descompone en dos
# rectángulos: uno de 6x2 (área 12, centro en 3,1) y otro de 2x4 (área 8, centro
# en 1,4). El centroide compuesto cae en (2.2, 2.2) — que es justo el hueco de la
# L, donde no hay parcela.
#
#     6 +---+
#       | B |
#     2 +---+-------+
#       |     A     |
#     0 +-----------+
#       0   2       6
ELE = [(0, 0), (6, 0), (6, 2), (2, 2), (2, 6), (0, 6)]
ELE_CENTROIDE = (2.2, 2.2)

# Una U: dos brazos verticales unidos por abajo. El centroide cae en el aire,
# entre los dos brazos.
U = [(0, 0), (6, 0), (6, 6), (4, 6), (4, 2), (2, 2), (2, 6), (0, 6)]

# Un cuadrado de 20x20 con un hueco de 16x16 en el medio: un anillo estrecho.
# El centroide compuesto cae en el centro exacto, que es el hueco.
ANILLO_EXTERIOR = [(0, 0), (20, 0), (20, 20), (0, 20)]
ANILLO_HUECO = [(2, 2), (18, 2), (18, 18), (2, 18)]

# Coordenadas de verdad, del tamaño que tienen en UTM 19N dominicano. Sirven para
# comprobar que la traslación al primer vértice hace su trabajo: sin ella, los
# productos cruzados llegan a 8·10^11 y el centroide de una parcela de 200 m²
# pierde precisión donde más se nota.
DESPLAZADO = [(421900.0, 2043300.0), (421920.0, 2043300.0),
              (421920.0, 2043310.0), (421900.0, 2043310.0)]


# ------------------------------------------------------- centroide de área --

def prueba_rectangulo():
    c = centroide.centroide_de_area([(RECTANGULO, False)])
    igual(c[0], 5.0, 1e-9, "centroide del rectángulo, este")
    igual(c[1], 2.0, 1e-9, "centroide del rectángulo, norte")


def prueba_triangulo():
    c = centroide.centroide_de_area([(TRIANGULO, False)])
    igual(c[0], 2.0, 1e-9, "centroide del triángulo, este")
    igual(c[1], 1.0, 1e-9, "centroide del triángulo, norte")


def prueba_el_sentido_de_giro_no_cambia_el_centroide():
    """Un anillo al revés es el mismo terreno.

    El RI no garantiza el sentido de giro de sus polígonos, y el área de Gauss
    cambia de signo con él. Si el centroide se calculara sin cuidar eso, la mitad
    de las parcelas del país saldrían con el punto en otro sitio.
    """
    derecho = centroide.centroide_de_area([(RECTANGULO, False)])
    revés = centroide.centroide_de_area([(list(reversed(RECTANGULO)), False)])
    igual(revés[0], derecho[0], 1e-9, "centroide invertido, este")
    igual(revés[1], derecho[1], 1e-9, "centroide invertido, norte")


def prueba_traslacion_en_coordenadas_utm():
    c = centroide.centroide_de_area([(DESPLAZADO, False)])
    igual(c[0], 421910.0, 1e-6, "centroide en UTM, este")
    igual(c[1], 2043305.0, 1e-6, "centroide en UTM, norte")


def prueba_el_hueco_se_resta():
    """Un patio interior no aporta al centroide: lo quita.

    Con el hueco centrado, el centroide sigue en el centro; lo que comprueba esta
    prueba es que el hueco **entra en el cálculo con área negativa** y no como un
    polígono más. Se descentra el hueco para que la diferencia se vea: si se
    sumara en vez de restarse, el centroide se iría hacia el hueco en lugar de
    huir de él.
    """
    hueco_a_la_derecha = [(12, 8), (18, 8), (18, 12), (12, 12)]
    c = centroide.centroide_de_area([(ANILLO_EXTERIOR, False),
                                     (hueco_a_la_derecha, True)])
    cierto(c[0] < 10.0,
           "con un hueco a la derecha el centroide tiene que irse a la "
           "izquierda del centro, y salió en este %.4f" % c[0])


# ------------------------------------------------- dentro y fuera del polígono --

def prueba_dentro_de_una_figura_simple():
    cierto(centroide.dentro((5, 2), [(RECTANGULO, False)]),
           "el centro del rectángulo tiene que estar dentro")
    cierto(not centroide.dentro((15, 2), [(RECTANGULO, False)]),
           "un punto a la derecha del rectángulo está fuera")
    cierto(not centroide.dentro((5, 9), [(RECTANGULO, False)]),
           "un punto por encima del rectángulo está fuera")


def prueba_el_hueco_es_fuera():
    cierto(centroide.dentro((1, 10), [(ANILLO_EXTERIOR, False),
                                      (ANILLO_HUECO, True)]),
           "el borde del anillo es dentro")
    cierto(not centroide.dentro((10, 10), [(ANILLO_EXTERIOR, False),
                                           (ANILLO_HUECO, True)]),
           "el patio interior NO es dentro: es un hueco")


def prueba_la_ele_tiene_el_centroide_fuera():
    """La premisa de todo lo demás. Si esto falla, el resto no prueba nada.

    Se comprueba a propósito que el centroide de área cae FUERA, además de dónde
    cae. Una prueba del punto interior sobre una figura cuyo centroide ya estaba
    dentro pasaría siempre sin ejercitar nada.
    """
    c = centroide.centroide_de_area([(ELE, False)])
    igual(c[0], ELE_CENTROIDE[0], 1e-9, "centroide de la L, este")
    igual(c[1], ELE_CENTROIDE[1], 1e-9, "centroide de la L, norte")
    cierto(not centroide.dentro(c, [(ELE, False)]),
           "el centroide de una L tiene que caer FUERA de la L; si cae dentro, "
           "la figura de prueba está mal construida y el punto interior no se "
           "está ejercitando")


# ------------------------------------------------------- el punto entregado --

def prueba_figura_simple_entrega_el_centroide():
    punto, ajustado = centroide.punto_para_ir([(RECTANGULO, False)])
    igual(punto[0], 5.0, 1e-9, "punto del rectángulo, este")
    igual(punto[1], 2.0, 1e-9, "punto del rectángulo, norte")
    cierto(not ajustado,
           "en un rectángulo el punto NO se ajusta: es el centroide tal cual, y "
           "decir lo contrario en pantalla sería mentir en el 98.8 % de los casos")


def prueba_la_ele_entrega_un_punto_dentro():
    punto, ajustado = centroide.punto_para_ir([(ELE, False)])
    cierto(centroide.dentro(punto, [(ELE, False)]),
           "el punto entregado para una L tiene que estar DENTRO de la L, y "
           "salió en (%.4f, %.4f)" % punto)
    cierto(ajustado,
           "en una L el punto SÍ se ajusta, y la pantalla tiene que poder "
           "decirlo")


def prueba_la_u_entrega_un_punto_dentro():
    punto, ajustado = centroide.punto_para_ir([(U, False)])
    cierto(centroide.dentro(punto, [(U, False)]),
           "el punto entregado para una U tiene que estar DENTRO, y salió en "
           "(%.4f, %.4f)" % punto)
    cierto(ajustado, "en una U el punto se ajusta")


def prueba_el_anillo_con_hueco_entrega_un_punto_dentro():
    anillos = [(ANILLO_EXTERIOR, False), (ANILLO_HUECO, True)]
    punto, ajustado = centroide.punto_para_ir(anillos)
    cierto(centroide.dentro(punto, anillos),
           "el punto de un anillo con patio no puede caer en el patio, y salió "
           "en (%.4f, %.4f)" % punto)
    cierto(ajustado, "en un anillo con patio centrado el punto se ajusta")


def prueba_el_punto_ajustado_es_determinista():
    """El mismo inmueble tiene que dar siempre el mismo punto.

    Si no, dos personas consultando el mismo posicional reciben destinos
    distintos, y la misma persona consultando dos veces cree que la herramienta
    se equivocó una de las dos.
    """
    a, _ = centroide.punto_para_ir([(ELE, False)])
    b, _ = centroide.punto_para_ir([(ELE, False)])
    igual(a[0], b[0], 0.0, "el punto ajustado tiene que ser idéntico, este")
    igual(a[1], b[1], 0.0, "el punto ajustado tiene que ser idéntico, norte")


def prueba_varios_exteriores_toma_el_mayor():
    """Dos polígonos sueltos bajo un mismo posicional: se va al grande.

    El RI publica `MultiPolygon`, así que un inmueble puede llegar partido en
    dos. Mandar al usuario al punto medio entre los dos trozos lo mandaría al
    terreno de en medio, que no es suyo.
    """
    lejano_pequeno = [(1000, 1000), (1002, 1000), (1002, 1002), (1000, 1002)]
    punto, _ = centroide.punto_para_ir([(RECTANGULO, False),
                                        (lejano_pequeno, False)])
    cierto(centroide.dentro(punto, [(RECTANGULO, False)]),
           "con dos trozos, el punto va al MAYOR y no al medio de los dos; "
           "salió en (%.4f, %.4f)" % punto)


def prueba_un_poligono_degenerado_no_revienta():
    """Tres puntos en línea recta no encierran nada. Se dice, no se calcula."""
    try:
        centroide.punto_para_ir([([(0, 0), (5, 0), (10, 0)], False)])
    except centroide.ErrorCentroide:
        pass
    else:
        FALLOS.append("un polígono de área cero tiene que dar ErrorCentroide, "
                      "no un punto cualquiera")


def prueba_sin_anillos_da_error():
    try:
        centroide.punto_para_ir([])
    except centroide.ErrorCentroide:
        pass
    else:
        FALLOS.append("sin anillos tiene que dar ErrorCentroide")


# ----------------------------------------------- el caso que se midió de verdad --

def prueba_una_parcela_estrecha_y_larga():
    """Una franja de 200 m x 3 m, que es la forma de un solar de callejón.

    Es donde el punto interior puede salir mal por poco: el tramo horizontal
    interior es cortísimo comparado con la figura.
    """
    franja = [(0, 0), (200, 0), (200, 3), (0, 3)]
    punto, _ = centroide.punto_para_ir([(franja, False)])
    cierto(centroide.dentro(punto, [(franja, False)]),
           "el punto de una franja larga tiene que caer dentro")


def prueba_media_luna():
    """Cóncava de verdad, sin ángulos rectos: el caso rural que se midió."""
    import math
    fuera = [(50 * math.cos(math.radians(g)), 50 * math.sin(math.radians(g)))
             for g in range(0, 181, 10)]
    dentro_arco = [(40 * math.cos(math.radians(g)), 40 * math.sin(math.radians(g)))
                   for g in range(180, -1, -10)]
    luna = fuera + dentro_arco
    c = centroide.centroide_de_area([(luna, False)])
    cierto(not centroide.dentro(c, [(luna, False)]),
           "el centroide de una media luna cae en el hueco; si no, la figura "
           "está mal construida")
    punto, ajustado = centroide.punto_para_ir([(luna, False)])
    cierto(centroide.dentro(punto, [(luna, False)]),
           "el punto de una media luna tiene que caer dentro, y salió en "
           "(%.4f, %.4f)" % punto)
    cierto(ajustado, "en una media luna el punto se ajusta")


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
    print("[OK] %d pruebas del centroide y del punto interior." % len(pruebas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
