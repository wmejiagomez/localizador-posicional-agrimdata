# -*- coding: utf-8 -*-
"""La vitrina: que diga la verdad y que no se desincronice de su copia.

    python pruebas/test_vitrina.py

Tres cosas, y las tres han costado caro en el hub:

1. **Que `sitio/index.html` y `pagina_localizador.html` sean el mismo archivo.**
   La página se edita en un sitio y se sirve desde otro. Durante meses esa copia
   fue manual y olvidarla no daba ningún síntoma: la subida decía «ok» porque sí
   había subido un archivo, el anterior. Se descubrió con **doce de trece
   desincronizadas a la vez**.

2. **Que lo que la vitrina promete siga siendo cierto.** Un aviso de privacidad
   que describe otro sistema es una promesa que no se está cumpliendo, y no hay
   error de servidor que lo delate: el 2026-08-15 cinco vitrinas se quedaron
   describiendo un sistema de acceso que ya no existía, con las páginas
   respondiendo 200 y viéndose perfectas.

3. **Que el nivel declarado y el portero digan lo mismo.** Aquí la comprobación
   va en la dirección contraria a la de las PRO: ésta es gratuita, así que su
   router **no** puede llevar `acceso-pro@file`. Un portero de más le pediría una
   cuenta a un público que no la tiene y la herramienta parecería rota sin
   estarlo.
"""

import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from nucleo import marca, ri                                       # noqa: E402

fallos = []


def verificar(condicion, descripcion):
    if condicion:
        print("  ok    %s" % descripcion)
    else:
        print("  MAL   %s" % descripcion)
        fallos.append(descripcion)


# Las rutas se derivan de la de este archivo, nunca escritas a mano: una ruta a
# mano no falla cuando la carpeta cambia de nombre — sigue en verde comprobando
# algo que ya no existe.
VITRINA = os.path.join(RAIZ, "sitio", "index.html")
COPIA = os.path.join(RAIZ, "pagina_localizador.html")
COMPOSE = os.path.join(RAIZ, "docker-compose.yml")

for ruta in (VITRINA, COPIA, COMPOSE):
    if not os.path.exists(ruta):
        print("  MAL   falta %s" % ruta)
        sys.exit(1)


def leer(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return archivo.read()


HTML = leer(VITRINA)

# El texto que de verdad lee un visitante. Dos pasos, y los dos hacen falta:
#
# 1. **Fuera `<style>` y `<script>` enteros, con su contenido.** Quitar solo las
#    etiquetas deja dentro el CSS y el JavaScript, comentarios incluidos — y los
#    comentarios de esta vitrina explican por qué aquí NO va el portero, así que
#    contienen «las PRO» y «suscribirse». Sin este paso, las dos comprobaciones
#    de nivel de más abajo se ponían rojas leyendo un comentario del código.
#    Costó una vuelta el 2026-08-21, y es la misma trampa que el rastreo de fugas
#    de la Tabla CORS: la nota que decía que no se guardan claves contenía la
#    palabra «clave».
# 2. **Después, fuera las etiquetas.** Una frase partida por un `<strong>` no
#    contiene la cadena literal: en Colindancias eso dejó pasar tres aserciones
#    que decían comprobar la prosa y comprobaban el marcado.
SIN_ETIQUETAS = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", HTML,
                       flags=re.S | re.I)
SIN_ETIQUETAS = re.sub(r"<!--.*?-->", " ", SIN_ETIQUETAS, flags=re.S)
SIN_ETIQUETAS = re.sub(r"<[^>]+>", " ", SIN_ETIQUETAS)
SIN_ETIQUETAS = re.sub(r"\s+", " ", SIN_ETIQUETAS)


print("=" * 72)
print("LA VITRINA Y SU COPIA SON EL MISMO ARCHIVO")
print("=" * 72)

verificar(HTML == leer(COPIA),
          "sitio/index.html y pagina_localizador.html son idénticas byte a byte")


print()
print("=" * 72)
print("LO QUE LA VITRINA DICE ES LO QUE LA HERRAMIENTA HACE")
print("=" * 72)

verificar("no es el Registro Inmobiliario" in SIN_ETIQUETAS,
          "DICE QUE NO ES EL REGISTRO INMOBILIARIO")
verificar("no certifica nada" in SIN_ETIQUETAS, "DICE QUE NO CERTIFICA NADA")
verificar("No está afiliado" in SIN_ETIQUETAS,
          "y lo repite en el pie, que es lo que se lee al final")
verificar("no publican titularidad" in SIN_ETIQUETAS,
          "DICE QUE EL RI NO PUBLICA TITULARIDAD")
verificar(ri.PORTAL_OFICIAL in HTML, "ofrece el portal oficial del RI")

# **La promesa propia de esta herramienta.** No es un matiz: quien llega puede
# estar a punto de comprar un terreno, y si toma este punto por un lindero, el
# error se descubre con una verja levantada.
verificar("no es un lindero" in SIN_ETIQUETAS.lower()
          or "no delimita la propiedad" in SIN_ETIQUETAS.lower(),
          "DICE QUE EL PUNTO NO ES UN LINDERO")
verificar("no compre" in SIN_ETIQUETAS.lower(),
          "y dice explícitamente que no se compre nada con esta pantalla")

# El hallazgo que gobierna el módulo del centroide, contado en la vitrina.
verificar("51 metros" in SIN_ETIQUETAS or "51 m" in SIN_ETIQUETAS,
          "cuenta cuánto puede alejarse el centro en una parcela irregular")
verificar("1.2 %" in SIN_ETIQUETAS or "1.2%" in SIN_ETIQUETAS,
          "y con qué frecuencia pasa, con la cifra medida")


print()
print("=" * 72)
print("COHERENCIA CON EL NIVEL: ESTA ES GRATUITA")
print("=" * 72)

verificar(marca.ES_PRO is False, "el módulo declara que NO es PRO")
verificar("ratis" in HTML, "y la vitrina dice que es gratis")
verificar("PRO" not in SIN_ETIQUETAS,
          "y NO se anuncia como PRO en ningún sitio")
verificar("US$" not in HTML and "al mes" not in SIN_ETIQUETAS,
          "y no promete ningún cobro")
verificar("suscri" not in SIN_ETIQUETAS.lower(),
          "y no habla de suscripción")

# **Que el filtro de arriba sirva.** Las dos comprobaciones anteriores dependen
# de que `SIN_ETIQUETAS` no traiga el contenido de `<script>`, y una prueba que
# se apoya en un filtro sin comprobar el filtro da verde cuando el filtro se
# rompe. Se busca una cadena que SOLO existe dentro del guion del marco: si
# aparece en el texto, el filtro dejó de funcionar y lo de arriba no vale nada.
verificar("addEventListener" in HTML,
          "el guion del marco sigue en la página (si no, no hay nada que filtrar)")
verificar("addEventListener" not in SIN_ETIQUETAS,
          "y el filtro de <script> funciona: su contenido no cuenta como texto")
verificar("box-sizing" in HTML and "box-sizing" not in SIN_ETIQUETAS,
          "y el de <style> también")


print()
print("=" * 72)
print("LO QUE NO HACE, DICHO EN LA VITRINA")
print("=" * 72)

# La línea con el Visor Parcelario. Si la vitrina empieza a prometer descargas,
# lo que cambió no es la vitrina: es lo que esta herramienta es.
verificar("No entrega archivos" in SIN_ETIQUETAS,
          "dice que no entrega archivos")
verificar("Visor Parcelario" in SIN_ETIQUETAS,
          "y manda al Visor Parcelario a quien necesite el DXF")
verificar("https://parcelario.agrimensura.com.do" in HTML,
          "con su enlace de verdad")
verificar("No busca por designación catastral" in SIN_ETIQUETAS,
          "dice que solo busca por posicional")
verificar("No admite listas" in SIN_ETIQUETAS, "dice que no admite lotes")

# Lo que sí tiene que prometer, porque es el producto.
verificar("Waze" in SIN_ETIQUETAS and "Google Maps" in SIN_ETIQUETAS,
          "nombra los dos servicios de navegación")
verificar("doce dígitos" in SIN_ETIQUETAS,
          "dice cuántos dígitos tiene un posicional")
verificar("anulad" in SIN_ETIQUETAS.lower(),
          "avisa de que puede salir un inmueble anulado")


print()
print("=" * 72)
print("EL MARCO APUNTA A ESTA APLICACIÓN")
print("=" * 72)

# Un `<iframe>` copiado del molde con el subdominio de la herramienta anterior se
# ve perfecto y enseña otra herramienta.
verificar("localizador.app.agrimensura.com.do/?embed=true" in HTML,
          "el marco apunta a la aplicación de esta herramienta")
for ajena in ("parcelario.app.", "calles.app.", "area.app.", "division.app.",
              "grilla.app."):
    verificar(ajena not in HTML,
              "y no quedó ningún «%s» del molde del que se copió" % ajena)


print()
print("=" * 72)
print("LA CLAVE DE VISITAS ES LA SUYA")
print("=" * 72)

# Es una de las nueve listas del protocolo del hub, y de las que no dan la cara:
# con la clave del molde, esta herramienta sumaría sus visitas al contador de
# otra y las dos cifras quedarían mal para siempre sin que nada avisara.
claves = set(re.findall(r"agrimensura-[a-z0-9-]*-pagevisits", HTML))
verificar(claves == {"agrimensura-localizador-pagevisits"},
          "hay exactamente una clave de visitas y es la de localizador: %s"
          % sorted(claves))


print()
print("=" * 72)
print("EL DESPLIEGUE DICE LO MISMO QUE EL PLIEGO")
print("=" * 72)

compose = leer(COMPOSE)

# **Se miran las líneas que valen, no el archivo entero.** Los comentarios de
# este `docker-compose.yml` explican qué hace el portero y por qué aquí no va,
# así que la palabra «acceso-pro» aparece en la prosa: buscarla en el archivo
# completo la encontraría y esta prueba se pondría roja sin motivo — o peor,
# encontraría la etiqueta de verdad y la daría por comentario.
efectivas = [l.split("#", 1)[0] for l in compose.splitlines()]
efectivas = "\n".join(l for l in efectivas if l.strip())

# **La comprobación que aquí falla hacia el otro lado.** En una PRO el peligro es
# que falte el portero y quede abierta; en una gratuita el peligro es que sobre y
# le pida una cuenta a quien no tiene por qué tenerla.
verificar("acceso-pro@file" not in efectivas,
          "el router NO lleva portero: esta herramienta es gratuita")
verificar("routers.localizador-app-https.middlewares=gzip" in efectivas,
          "y su router de HTTPS lleva gzip y nada más")
verificar("localizador.app.agrimensura.com.do" in efectivas,
          "sirve la aplicación en su subdominio")
verificar("localizador.agrimensura.com.do" in efectivas,
          "y la vitrina en el suyo")
verificar("letsencrypt" in efectivas, "con certificado de Let's Encrypt")


print()
print("=" * 72)
print("EL ORIGEN QUE ESCUCHA EL MARCO ES EL DE ESTA APLICACIÓN")
print("=" * 72)

# Sin esto el mensaje de altura llega y se descarta en silencio, y el marco se
# queda clavado en la cifra del CSS. Medido en la Planilla el 2026-08-16:
# publicaba 568 px y el marco seguía en los 930 escritos a mano.
origenes = re.search(r"var ORIGENES = \[(.*?)\];", HTML, re.S)
verificar(origenes is not None, "el guion del marco declara sus orígenes")
if origenes:
    lista = re.findall(r"'([^']+)'", origenes.group(1))
    # **UNO y no dos, y eso es lo correcto en una gratuita.** El segundo origen
    # de las PRO es el del portero, que sirve la invitación a suscribirse dentro
    # del marco. Aquí no hay portero: declararlo sería anunciar una pantalla que
    # no puede aparecer.
    verificar(lista == ["https://localizador.app.agrimensura.com.do"],
              "y es solo el de esta aplicación, sin el del portero, porque no "
              "hay portero: %s" % lista)


print()
print("=" * 72)
if fallos:
    print("%d FALLO(S):" % len(fallos))
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("Todo bien.")
