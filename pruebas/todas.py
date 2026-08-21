# -*- coding: utf-8 -*-
"""Lanza las ocho suites, una detrás de otra.

    python pruebas/todas.py

Cada suite corre en su propio proceso: si una se cuelga o revienta, las demás
siguen y el informe dice cuál fue.

`test_red_real.py` va la última y **sale de la red**. Es la única que lo hace, y
si no hay internet no se pone roja: informa de que no se comprobó. Este lanzador
recoge ese estado y lo repite al final, arriba del resumen — una comprobación que
no llegó a correr escondida entre líneas es igual de peligrosa que una que miente.
"""

import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    ("test_centroide.py", "el punto al que se manda al usuario"),
    ("test_ri.py", "la capa de red, con dobles y sin internet"),
    ("test_inmueble.py", "de la respuesta del RI a la ficha"),
    ("test_navegacion.py", "los dos enlaces de ir, leídos de vuelta"),
    ("test_mapa.py", "las trampas de folium y lo que se dibuja"),
    ("test_app.py", "la interfaz con AppTest"),
    ("test_vitrina.py", "que la vitrina diga la verdad y no se desincronice"),
    ("test_privacidad.py", "lo que no puede hacer nunca"),
    ("test_red_real.py", "el contrato del servicio del RI, salteable"),
]


def main():
    rojas = []
    sin_comprobar = []
    for archivo, que_cubre in SUITES:
        print("\n=== %s · %s" % (archivo, que_cubre))
        hecho = subprocess.run([sys.executable, os.path.join(AQUI, archivo)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        # El aviso de Streamlit sobre el ScriptRunContext sale en cada `run()` de
        # AppTest y llena la pantalla sin decir nada: se filtra aquí para que los
        # [FAIL] no queden enterrados. Cualquier otra línea pasa tal cual.
        for linea in (hecho.stdout or "").splitlines():
            if "missing ScriptRunContext" in linea:
                continue
            print(linea)
        if hecho.stderr:
            for linea in hecho.stderr.splitlines():
                if "missing ScriptRunContext" in linea:
                    continue
                print(linea, file=sys.stderr)
        if hecho.returncode != 0:
            rojas.append(archivo)
        for linea in (hecho.stdout or "").splitlines():
            if "[SIN COMPROBAR]" in linea:
                sin_comprobar.append("%s: %s"
                                     % (archivo, linea.split("]", 1)[1].strip()))

    print("\n" + "=" * 60)
    if sin_comprobar:
        print("%d COMPROBACIÓN(ES) SIN CORRER:" % len(sin_comprobar))
        for s in sin_comprobar:
            print("  -", s)
        print()
    if rojas:
        print("SUITES FALLIDAS: %s" % ", ".join(rojas))
        return 1
    print("Las %d suites pasaron." % len(SUITES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
