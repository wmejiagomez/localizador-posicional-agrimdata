# -*- coding: utf-8 -*-
"""La única que sale a internet. Salteable, y va la última.

    python pruebas/test_red_real.py

Comprueba **el contrato del servicio**, no un resultado concreto: que las tres
capas de resultantes del Registro Inmobiliario sigan existiendo y sigan sirviendo
el campo `Posicional`. El día que el RI renombre un campo o retire una capa,
alguien se entera aquí en vez de por un usuario que no encuentra su inmueble.

**Por qué el contrato y no una búsqueda de verdad.** Buscar un posicional exige
tener uno, y un posicional real identifica el inmueble de una persona: meterlo en
este repositorio —que además es público— es justo lo que el pliego promete no
hacer. `DescribeFeatureType` devuelve el esquema de la capa y **ni una sola
parcela**, así que se comprueba lo que hay que comprobar sin traerse el
identificador de nadie.

**Si no hay internet no se pone roja**: informa de que no se comprobó, con la
marca `[SIN COMPROBAR]` que el lanzador recoge y repite al final. Una
comprobación que no llegó a correr, escondida entre líneas, es igual de peligrosa
que una que miente.
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from nucleo import ri                                              # noqa: E402

fallos = []
sin_comprobar = []


def verificar(condicion, descripcion):
    if condicion:
        print("  ok    %s" % descripcion)
    else:
        print("  MAL   %s" % descripcion)
        fallos.append(descripcion)


def no_comprobado(descripcion):
    print("  [SIN COMPROBAR] %s" % descripcion)
    sin_comprobar.append(descripcion)


print("=" * 72)
print("EL CONTRATO DEL SERVICIO DEL REGISTRO INMOBILIARIO")
print("=" * 72)
print("  (sale a la red; con el cable desenchufado informa y no falla)")
print()

hubo_red = False

for capa in ri.ORDEN:
    try:
        campos = ri.campos_declarados(capa)
    except ri.ServidorCaido as ex:
        no_comprobado("«%s»: no se pudo pedir el esquema (%s)"
                      % (ri.CAPAS[capa]["etiqueta"], ex))
        continue
    except Exception as ex:                                       # noqa: BLE001
        no_comprobado("«%s»: %s" % (ri.CAPAS[capa]["etiqueta"],
                                    ex.__class__.__name__))
        continue

    hubo_red = True
    verificar(ri.CAMPO_POSICIONAL in campos,
              "«%s» sigue sirviendo el campo «%s»"
              % (ri.CAPAS[capa]["etiqueta"], ri.CAMPO_POSICIONAL))
    verificar(ri.CAMPO_AREA in campos,
              "«%s» sigue sirviendo el campo «%s»"
              % (ri.CAPAS[capa]["etiqueta"], ri.CAMPO_AREA))

    # Los campos que la ficha enseña. Que falte uno no rompe la herramienta —el
    # renglón se queda vacío— pero sí empobrece la pantalla sin que nadie lo
    # note, y es la clase de cambio que conviene saber el día que pasa.
    for campo in ri.CAPAS[capa]["campos"]:
        verificar(campo in campos,
                  "«%s» sigue trayendo «%s»"
                  % (ri.CAPAS[capa]["etiqueta"], campo))

if not hubo_red:
    print()
    print("  Ninguna capa contestó. Si es falta de internet, no es un fallo de")
    print("  la herramienta; si el servicio del RI cambió, lo dirá al volver.")


print()
print("=" * 72)
print("LO QUE ESTA PRUEBA NO HACE, Y ES A PROPÓSITO")
print("=" * 72)
print("  - No busca ningún posicional real: identificaría un inmueble de")
print("    alguien, y este repositorio es público.")
print("  - No mide tiempos: las cifras del pliego (11.1 s en aprobadas, 4.6 s")
print("    en previo2017) se midieron a mano el 2026-08-21 y repetirlas en cada")
print("    batería sería golpear el servidor del RI sin aprender nada nuevo.")
print("  - No recorre la lista de capas del servidor: solo pregunta por las")
print("    tres que esta herramienta usa.")


print()
print("=" * 72)
if fallos:
    print("%d FALLO(S) DE CONTRATO:" % len(fallos))
    for f in fallos:
        print("  -", f)
    print()
    print("El servicio del Registro Inmobiliario cambió. Antes de tocar nada,")
    print("compruebe qué campos sirve ahora y actualice `nucleo/ri.py`.")
    sys.exit(1)
if sin_comprobar:
    print("%d comprobación(es) SIN CORRER (¿sin internet?)." % len(sin_comprobar))
    sys.exit(0)
print("El contrato del servicio del RI se cumple.")
