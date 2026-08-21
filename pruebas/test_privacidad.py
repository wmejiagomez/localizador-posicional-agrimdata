# -*- coding: utf-8 -*-
"""Lo que esta herramienta no puede hacer nunca.

    python pruebas/test_privacidad.py

Cinco cosas, y cada una está aquí porque su ausencia sería invisible:

1. **No escribe en disco.** Lo que se busca se procesa en memoria y se descarta.
2. **No habla con nadie salvo con quien está declarado.** El RI, los dos
   proveedores de teselas, el contador y —solo si el usuario pulsa— Google Maps
   y Waze.
3. **En el repositorio no hay ni un identificador de inmueble real.** El
   repositorio es público y la respuesta del RI trae posicionales y expedientes
   de verdad. Una fuga no se deshace cambiando la visibilidad después.
4. **El aviso legal dice la verdad**, incluida la parte que promete que es
   gratis y sin registro — que aquí sí se puede prometer, y por eso hay que
   comprobar que sigue siendo cierto.
5. **La herramienta no sabe generar archivos.** Es la línea que la separa del
   Visor Parcelario, y no es una promesa de la vitrina: es una propiedad del
   código.
"""

import ast
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from nucleo import marca, navegacion, ri                           # noqa: E402

fallos = []


def verificar(condicion, descripcion):
    if condicion:
        print("  ok    %s" % descripcion)
    else:
        print("  MAL   %s" % descripcion)
        fallos.append(descripcion)


def fuentes():
    """Todos los `.py` de la herramienta, salvo las propias pruebas.

    **Se buscan por patrón y la ausencia es un fallo.** En la Planilla,
    `test_privacidad.py` buscaba un archivo por su nombre dentro de un
    `if os.path.exists` y sus tres comprobaciones no se ejecutaron nunca, con la
    suite en verde toda la vida de la herramienta.
    """
    encontrados = []
    for carpeta, subcarpetas, archivos in os.walk(RAIZ):
        subcarpetas[:] = [s for s in subcarpetas
                          if s not in ("pruebas", "__pycache__", ".git",
                                       "venv", ".venv")]
        for archivo in archivos:
            if archivo.endswith(".py"):
                encontrados.append(os.path.join(carpeta, archivo))
    return encontrados


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


FUENTES = fuentes()

print("=" * 72)
print("LOS ARCHIVOS QUE SE INSPECCIONAN EXISTEN")
print("=" * 72)

# Si esta lista se queda corta, todo lo de abajo pasa sin mirar nada.
verificar(len(FUENTES) >= 10,
          "se encontraron %d archivos .py que inspeccionar" % len(FUENTES))
esperados = ("app.py", "ri.py", "centroide.py", "inmueble.py",
             "navegacion.py", "marca.py", "contador.py", "mapa.py",
             "coordenadas.py", "marco.py")
nombres = {os.path.basename(f) for f in FUENTES}
for esperado in esperados:
    verificar(esperado in nombres, "se inspecciona %s" % esperado)


print()
print("=" * 72)
print("NO SE ESCRIBE NADA EN DISCO")
print("=" * 72)

# `open(...)` en modo escritura, y las funciones que escriben sin pasar por él.
ESCRITURA = re.compile(
    r"""open\s*\([^)]*['"][waxr]\+?[bt]?['"]|"""
    r"""\b(?:os\.remove|os\.rename|os\.mkdir|os\.makedirs|shutil\.|"""
    r"""tempfile\.|pathlib\.Path\([^)]*\)\.write)""")

for ruta in sorted(FUENTES):
    texto = leer(ruta)
    # El generador de fixtures SÍ escribe, y tiene que hacerlo: corre a mano en
    # el escritorio de quien construye, nunca dentro del contenedor. Se excluye
    # nombrándolo, no por una regla que dejaría pasar cualquier otro.
    if os.path.basename(ruta) == "generar_fixtures.py":
        continue
    hallazgos = ESCRITURA.findall(texto)
    verificar(not hallazgos,
              "%s no escribe en disco%s"
              % (os.path.relpath(ruta, RAIZ),
                 "" if not hallazgos else " (encontrado: %s)" % hallazgos))


print()
print("=" * 72)
print("SOLO SE HABLA CON QUIEN ESTÁ DECLARADO")
print("=" * 72)

# Los dominios a los que esta herramienta puede dirigirse, y quién los alcanza.
# Cualquiera que aparezca en el código y no esté aquí es una fuga o una
# dependencia nueva que nadie declaró en el aviso legal.
PERMITIDOS = {
    "atlas.ri.gob.do": "el GeoServer del RI (la consulta y las teselas)",
    "servicios.ri.gob.do": "el portal oficial, al que se enlaza",
    "ri.gob.do": "el RI, en los créditos",
    "countapi.mileshilliard.com": "el contador de uso",
    "basemaps.cartocdn.com": "el fondo de calles (lo pide el navegador)",
    "server.arcgisonline.com": "la foto aérea (la pide el navegador)",
    "www.google.com": "el enlace de Google Maps (solo si se pulsa)",
    "www.waze.com": "el enlace de Waze (solo si se pulsa)",
    "fonts.googleapis.com": "la tipografía de marca",
    "fonts.gstatic.com": "la tipografía de marca",
    "www.agrimensura.com.do": "el sitio de la casa",
    "herramientas.agrimensura.com.do": "el catálogo",
    "parcelario.agrimensura.com.do": "el Visor Parcelario, al que se manda",
    "localizador.agrimensura.com.do": "la vitrina de esta herramienta",
    "localizador.app.agrimensura.com.do": "esta aplicación",
    "wa.me": "el WhatsApp del llamado a la acción",
    "agrimensura.com.do": "la casa, en el User-Agent con el que se identifica",
    "www.openstreetmap.org": "la licencia de OSM, en los créditos",
    "carto.com": "la atribución de CARTO",
    "localhost": "la comprobación de salud del contenedor",
    "127.0.0.1": "la comprobación de salud del contenedor",
}

DOMINIO = re.compile(r"https?://([A-Za-z0-9.\-]+)")

for ruta in sorted(FUENTES):
    for dominio in set(DOMINIO.findall(leer(ruta))):
        verificar(dominio in PERMITIDOS,
                  "%s solo habla con destinos declarados (apareció «%s»)"
                  % (os.path.relpath(ruta, RAIZ), dominio))


print()
print("=" * 72)
print("EN EL REPOSITORIO NO HAY NI UN INMUEBLE REAL")
print("=" * 72)

# **Doce dígitos seguidos son la forma de un posicional.** Se busca esa forma en
# todo el repositorio —código, fixtures, vitrina, documentación— y se exige que
# todo lo que aparezca empiece por nueves, que es la convención de lo inventado.
#
# Se comprueba que la comprobación sirve: más abajo se le mete un número con
# forma real y se exige que lo cace. Sin eso, un patrón mal escrito da salida
# vacía, que es exactamente lo que significa «está limpio».
FORMA_POSICIONAL = re.compile(r"(?<!\d)(\d{12})(?!\d)")

INVENTADO = re.compile(r"^(999|669)")


def sospechosos(texto):
    return [n for n in FORMA_POSICIONAL.findall(texto)
            if not INVENTADO.match(n)]


REVISABLES = []
for carpeta, subcarpetas, archivos in os.walk(RAIZ):
    subcarpetas[:] = [s for s in subcarpetas
                      if s not in ("__pycache__", ".git", "venv", ".venv")]
    for archivo in archivos:
        if archivo.endswith((".py", ".json", ".html", ".md", ".txt", ".yml")):
            REVISABLES.append(os.path.join(carpeta, archivo))

verificar(len(REVISABLES) >= 15,
          "se revisan %d archivos en busca de identificadores reales"
          % len(REVISABLES))

for ruta in sorted(REVISABLES):
    encontrados = sospechosos(leer(ruta))
    verificar(not encontrados,
              "%s no lleva ningún número con forma de posicional real%s"
              % (os.path.relpath(ruta, RAIZ),
                 "" if not encontrados
                 else " (encontrado: %s)" % sorted(set(encontrados))))

# **Que la comprobación sepa ponerse roja.** Se le pasa un número con la forma de
# un posicional real —doce dígitos que no empiezan por nueves— y tiene que
# cazarlo. Si no, la salida vacía de arriba no significaba nada.
#
# El señuelo se **construye** en vez de escribirse literal, y eso no es un
# adorno: escrito, el barrido de arriba lo encontraría en este mismo archivo y la
# prueba se cazaría a sí misma. Así queda un número de doce dígitos en memoria y
# ninguno en el código fuente.
#
# La primera versión de esta prueba sí lo escribía literal, **y era el posicional
# real del caso que originó la herramienta**. La comprobación lo cazó en su
# primera ejecución, junto con otro que se había colado en `test_ri.py`. Es la
# demostración de que sirve, y la razón de que se quede.
SENUELO = "1" + "2" * 11
INVENTADO_DE_PRUEBA = "9" * 6 + "000001"

verificar(len(SENUELO) == 12 and not INVENTADO.match(SENUELO),
          "el señuelo tiene forma de posicional real (12 dígitos, no empieza "
          "por nueves)")
verificar(sospechosos("el numero %s dentro de una frase" % SENUELO),
          "y la comprobación LO CAZA cuando se le pone delante")
verificar(not sospechosos("el numero %s es inventado" % INVENTADO_DE_PRUEBA),
          "y deja pasar los inventados, que empiezan por nueves")
verificar(not sospechosos("de 1234567890123456 caracteres"),
          "y no se dispara con una cifra larga que no es un posicional")


print()
print("=" * 72)
print("EL AVISO LEGAL DICE LA VERDAD")
print("=" * 72)

TEXTO_LEGAL = marca.DESCARGO_LEGAL

verificar("gratuita" in TEXTO_LEGAL,
          "dice que es gratuita, que aquí SÍ se puede prometer")
verificar(marca.ES_PRO is False,
          "y el módulo lo declara: ES_PRO es False")
verificar("no pide registro" in TEXTO_LEGAL,
          "dice que no pide registro")
verificar("no pide correo ni contraseña" in TEXTO_LEGAL,
          "y que no pide correo ni contraseña")

verificar("no se guarda nada" in TEXTO_LEGAL,
          "promete que no se guarda nada")
verificar("No es el Registro Inmobiliario" in TEXTO_LEGAL,
          "dice que no es el RI")
verificar("No certifica nada" in TEXTO_LEGAL, "dice que no certifica nada")
verificar("no publican titularidad" in TEXTO_LEGAL,
          "dice que el RI no publica titularidad")
verificar("no un lindero" in TEXTO_LEGAL,
          "dice que el punto NO es un lindero")
verificar("no sirve para saber por dónde pasa la línea" in TEXTO_LEGAL,
          "y lo explica, en vez de dejarlo en una frase que se puede pasar por "
          "alto")

# Los tres terceros que reciben algo. El aviso legal los nombra a los tres, y
# esta comprobación es lo que impide que se añada un cuarto sin decirlo.
for tercero in ("Registro Inmobiliario", "CARTO", "Esri", "Google Maps",
                "Waze"):
    verificar(tercero in TEXTO_LEGAL,
              "el aviso legal nombra a «%s» como destinatario de algo"
              % tercero)

verificar("No entrega archivos" in TEXTO_LEGAL,
          "y dice que no entrega archivos")


print()
print("=" * 72)
print("LA HERRAMIENTA NO SABE GENERAR ARCHIVOS")
print("=" * 72)

# **La línea con el Visor Parcelario, comprobada sobre el código y no sobre una
# promesa.** El día que alguien añada un escritor de DXF, esta herramienta deja
# de ser un localizador y pasa a ser un Visor Parcelario gratis. Eso no es un
# fallo que se vea: es una decisión de producto que se tomaría sin darse cuenta.
PAQUETES_DE_ARCHIVO = ("ezdxf", "shapefile", "pyshp", "fiona", "openpyxl",
                       "xlsxwriter", "reportlab")

requisitos = leer(os.path.join(RAIZ, "requirements.txt"))
for paquete in PAQUETES_DE_ARCHIVO:
    # Se miran las líneas efectivas: el propio `requirements.txt` explica en un
    # comentario por qué `ezdxf` y `pyshp` NO están, así que buscarlos en el
    # archivo entero los encontraría en la prosa.
    lineas = [l.split("#", 1)[0].strip() for l in requisitos.splitlines()]
    efectivas = [l for l in lineas if l]
    verificar(not any(l.lower().startswith(paquete) for l in efectivas),
              "«%s» no es una dependencia de esta herramienta" % paquete)

for ruta in sorted(FUENTES):
    arbol = ast.parse(leer(ruta), filename=ruta)
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
    colados = importados & set(PAQUETES_DE_ARCHIVO)
    verificar(not colados,
              "%s no importa ningún escritor de archivos%s"
              % (os.path.relpath(ruta, RAIZ),
                 "" if not colados else " (encontrado: %s)" % sorted(colados)))

# Y `st.download_button` es la otra puerta: sin dependencia nueva, bastaría con
# entregar el texto de un KML a mano.
verificar("download_button" not in leer(os.path.join(RAIZ, "app.py")),
          "la pantalla no tiene ningún botón de descarga")


print()
print("=" * 72)
print("LO QUE SALE HACIA GOOGLE Y WAZE ES SOLO LA COORDENADA")
print("=" * 72)

# Se construye un enlace y se mira qué lleva. El aviso legal promete que reciben
# «las coordenadas del inmueble» y nada más.
for url in (navegacion.google_maps(18.478, -69.912),
            navegacion.waze(18.478, -69.912)):
    verificar(not FORMA_POSICIONAL.search(url),
              "el enlace no lleva ningún posicional: %s" % url)
    verificar("Expediente" not in url and "expediente" not in url,
              "ni el expediente")


print()
print("=" * 72)
print("EL CONTADOR ES SUYO Y NO EL DE OTRA HERRAMIENTA")
print("=" * 72)

# Registro 6 de las nueve listas del protocolo del hub, y de los dos que fallan
# apuntando al contador ajeno en vez de faltar. Dos herramientas sumando al mismo
# sitio dan una cifra que parece sana.
from nucleo import contador                                        # noqa: E402

verificar("localizador" in contador.CLAVE,
          "la clave del contador nombra a esta herramienta: %s"
          % contador.CLAVE)
for ajena in ("parcelario", "calles", "area", "division", "colindancias",
              "grilla"):
    verificar(ajena not in contador.CLAVE,
              "y no es la de «%s», del molde que se copió" % ajena)


print()
print("=" * 72)
print("EL BUEN VECINO CON EL SERVIDOR DEL RI")
print("=" * 72)

verificar("agrimensura.com.do" in ri.AGENTE,
          "el User-Agent dice dónde reclamar")
verificar("Localizador" in ri.AGENTE,
          "y nombra a esta herramienta, no a la que se copió")
verificar(ri.TOPE <= 100,
          "hay tope de resultados por consulta (%d)" % ri.TOPE)
verificar("historicas" not in ri.CAPAS,
          "no se le pide a la capa histórica un campo que no tiene")

# Nada que huela a recorrer el parcelario. Un bucle sobre números posicionales
# sería un barrido con otro nombre, y es justo lo que el pliego promete no hacer.
for ruta in sorted(FUENTES):
    texto = leer(ruta)
    verificar("startIndex" not in texto,
              "%s no pagina resultados (pedir páginas es como se construye una "
              "descarga masiva sin darse cuenta)"
              % os.path.relpath(ruta, RAIZ))


print()
print("=" * 72)
if fallos:
    print("%d FALLO(S):" % len(fallos))
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("Todo bien.")
