# -*- coding: utf-8 -*-
"""Identidad, textos legales y llamado a la acción.

El hub vive bajo la marca **Agrimensura.com.do** (contenido público), no bajo
AgrimData (software de pago). Los colores y la tipografía salen del manual de
marca de Agrimensura.com.do; el llamado a la acción apunta hacia AgrimData.

Este archivo se REESCRIBE en cada herramienta, no se copia: su `DESCARGO_LEGAL`
habla de lo que hace y de lo que no hace *esta*. Copiarlo tal cual publica un
aviso legal que describe otra.

Y aquí tiene dos obligaciones más que las demás del hub:

1. **Decir que esto no es el Registro Inmobiliario.** Los datos son suyos y el
   nombre se le parece.
2. **Hablarle a alguien que no es agrimensor.** Es la primera herramienta del hub
   pensada para el dueño de un inmueble, no para quien lo mide. El aviso legal
   tiene que poder leerlo alguien que nunca ha visto un plano, y por eso está
   escrito en frases cortas y sin una sola palabra del oficio que no se explique.
"""

from urllib.parse import quote

__version__ = "1.0.0"

# **Gratuita.** No lleva el portero `acceso-pro@file` en su router, no tiene ficha
# en el catálogo del servicio de acceso, y su aplicación tiene que contestar
# **200** y no 302 — al revés que una PRO. Los dos errores son graves y ninguno da
# síntoma: una gratuita en 302 pide una cuenta que nadie tiene por qué tener.
#
# Por qué gratis, con el razonamiento completo, en `PLIEGO.md`: el público de esta
# herramienta no es el de la suscripción. Quien escribe un posicional para que
# Waze lo lleve al terreno no está armando ningún plano.
ES_PRO = False

SITIO_NOMBRE = "Agrimensura.com.do"
SITIO_WEB = "https://www.agrimensura.com.do"
EMPRESA = "Agrimdata & Servicios, SRL"
TELEFONO = "849-537-3857"

# Manual de marca de Agrimensura.com.do.
AZUL = "#126493"        # azul institucional
GRIS = "#59595B"        # gris pizarra
BLANCO = "#FFFFFF"      # fondo obligatorio
ROJO = "#C1272D"        # solo para lo anulado y la advertencia del RI
VERDE = "#1B7F3B"

URL_CATALOGO = "https://herramientas.agrimensura.com.do"
URL_PARCELARIO = "https://parcelario.agrimensura.com.do"
PORTAL_RI = "https://servicios.ri.gob.do/ConsultaParcelario"

DESCARGO_CORTO = (
    "Gratis y sin registro. Escriba el número posicional del inmueble y le "
    "decimos dónde queda. No es el Registro Inmobiliario y no certifica nada."
)

DESCARGO_LEGAL = f"""Esta es una herramienta gratuita de {EMPRESA} para **encontrar en el mapa un inmueble del que sólo se tiene su número posicional**. Es de uso libre, no pide registro y no pide correo ni contraseña.

**Qué hace**

Busca el número posicional en el parcelario que el Registro Inmobiliario publica en sus geoservicios abiertos. Si lo encuentra, calcula un punto dentro de la parcela, lo enseña sobre la foto aérea y le ofrece abrir la ruta hasta allí en Google Maps o en Waze.

**No es el Registro Inmobiliario**

Producto independiente. No está afiliado, patrocinado ni avalado por el Registro Inmobiliario ni por el Poder Judicial de la República Dominicana. Los datos se consultan en vivo en los geoservicios públicos del RI y son suyos; el portal oficial es [servicios.ri.gob.do]({PORTAL_RI}).

**No certifica nada, y esto importa antes de comprar**

Lo que ve es una copia de lo que el RI publica **en el momento en que se consultó**, y el parcelario cambia. Quien decide es el Registro Inmobiliario. **No compre, no venda y no firme nada basándose en esta pantalla**: pida la certificación del RI y contrate a un agrimensor para que le mida y le señale el terreno en el sitio.

**El punto es una referencia, no un lindero**

Se le da **un punto dentro de la parcela**, no sus esquinas. Sirve para llegar a la zona; no sirve para saber por dónde pasa la línea de su terreno, ni para colocar una verja, ni para discutir con un vecino. Marcar los linderos en el terreno es un trabajo de campo que hace un agrimensor con equipo, y no se puede hacer desde un mapa.

**Cuando la parcela tiene forma irregular, el punto se mueve**

El centro geométrico de una parcela en forma de L o de U cae **fuera de la propia parcela**. Medido sobre parcelas reales del RI: pasa en el 1.2 % de las rurales, y en el peor caso el centro quedaba a 51 metros del terreno. Cuando eso ocurre, esta herramienta mueve el punto a un lugar que sí está dentro **y se lo dice en pantalla**.

**No dice quién es el propietario**

Los geoservicios del RI **no publican titularidad**. Sus datos son el posicional, el expediente, el área, la provincia, el municipio y la fecha de inscripción: no hay nombres, ni cédulas, ni precios. Esta herramienta no puede mostrar lo que no recibe, y no lo busca por otro lado.

**No comprueba cargas ni gravámenes**

Que un inmueble aparezca aquí no dice nada sobre hipotecas, litis, oposiciones ni servidumbres inscritas.

**Si el inmueble está anulado, se lo decimos**

El posicional puede corresponder a una resultante que el RI **anuló**. Esas se buscan a propósito y se muestran con la advertencia encima, porque es justo lo que no se puede descubrir tarde.

**No entrega archivos**

Aquí no se descarga nada. Si lo que necesita es la parcela en DXF, KML o shapefile para llevarla a un programa de dibujo, con su cuadro de coordenadas y sus dos áreas contrastadas, eso lo hace el [Visor Parcelario]({URL_PARCELARIO}).

**Depende de un servicio ajeno**

Si el servidor del Registro Inmobiliario no responde, esta herramienta no puede responder tampoco. No es un fallo de su número, y cuando pasa se le dice.

**Privacidad**

El número que usted escribe se procesa en memoria: **no se guarda nada**. No se almacena la búsqueda ni el resultado, y desaparecen al cerrar la página. No se pide correo, no se crea ningún perfil y no hay forma de relacionar una consulta con una persona. Únicamente se lleva un conteo del total de búsquedas hechas, sin ningún dato asociado. Lo que usted envía viaja **cifrado** entre su navegador y la herramienta (HTTPS).

Tres cosas sí salen hacia fuera, y conviene saberlas. El **número posicional** viaja al servidor del Registro Inmobiliario, que ve qué se le pregunta, igual que si usted estuviera en su portal. Las **imágenes de fondo del mapa** las pide su navegador a CARTO y a Esri, que ven la zona que está mirando. Y si usted pulsa uno de los botones de ir, **Google Maps o Waze reciben las coordenadas del inmueble**, como en cualquier enlace que se abra en ellos — eso ocurre sólo si usted lo pulsa.

**Responsabilidad**

Esta herramienta no constituye asesoría técnica, legal ni certificación de ningún tipo. {EMPRESA} no se hace responsable por decisiones tomadas con base exclusiva en la información aquí presentada, ni por la exactitud, vigencia o disponibilidad de los datos que publica el Registro Inmobiliario.
"""

AVISO_PIE = (
    f"Herramienta gratuita de {EMPRESA}. Datos del Registro Inmobiliario, "
    "consultados en sus geoservicios públicos. No es el RI y no certifica nada."
)

# La advertencia que va destacada y arriba, no en la letra pequeña: es lo que
# impide que alguien tome esta pantalla por un documento del registro.
AVISO_RI_HTML = (
    "<strong>Esto no es el Registro Inmobiliario.</strong> Es una herramienta "
    "independiente de %s que consulta los datos que el RI publica abiertamente. "
    "No certifica nada: antes de comprar, vender o firmar, pida la certificación "
    "oficial en <a href=\"%s\" target=\"_blank\" rel=\"noopener\">el portal del "
    "RI</a>." % (EMPRESA, PORTAL_RI)
)

# Lo que cierra la pantalla **después** de que el usuario ya tiene su punto.
#
# **No repite el aviso de arriba, y eso es deliberado.** La primera versión
# pintaba `AVISO_RI_HTML` en los dos sitios: mirando la pantalla montada, el
# mismo párrafo aparecía dos veces palabra por palabra en el mismo desplazamiento
# — que no se lee como énfasis, se lee como un fallo de la página, y hace que se
# salte también el de arriba.
#
# Aquí abajo va la advertencia que **solo tiene sentido cuando ya hay un
# resultado**: el usuario acaba de ver un punto y dos botones para conducir hasta
# él, y ese es el momento exacto en que hay que decirle qué no es ese punto.
RECORDATORIO_FINAL_HTML = (
    "<strong>El punto es para llegar, no para medir.</strong> Le dice a qué "
    "terreno ir; <strong>no dice por dónde pasan sus linderos</strong>, ni "
    "cuánto mide realmente, ni si lo construido está dentro. Para eso hace falta "
    "una mensura en el sitio. Y recuerde que esto no es el Registro "
    "Inmobiliario: para cualquier trámite, su documento."
)

CTA_TITULO = "¿Ya sabe dónde está? Lo siguiente es medirlo"
CTA_TEXTO = """Un punto en el mapa le dice a qué zona ir. **No le dice por dónde
pasan los linderos de su terreno**, ni cuánto mide de verdad, ni si lo que hay
construido está dentro.

Eso es un trabajo de campo: un agrimensor con equipo va al sitio, mide, y levanta
el plano que vale ante el Registro Inmobiliario.

Escríbanos por WhatsApp y le decimos cómo se hace y qué cuesta.
"""

CTA_BOTON = "Escribir por WhatsApp"

# wa.me pide el número en formato internacional sin signos. República Dominicana
# es +1, así que 849-537-3857 queda como 1 849 537 3857.
_WHATSAPP_NUMERO = "1" + TELEFONO.replace("-", "")
_WHATSAPP_MENSAJE = (
    "Hola, localicé mi inmueble en el buscador de posicionales de "
    f"{SITIO_NOMBRE} y quisiera información sobre una mensura."
)
CTA_ENLACE = (f"https://wa.me/{_WHATSAPP_NUMERO}"
              f"?text={quote(_WHATSAPP_MENSAJE)}")

CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&family=Open+Sans:wght@400;600&display=swap');

  .stApp {{ background: {BLANCO}; }}

  .stApp, .stApp p, .stApp li, .stApp label, .stApp div[data-testid="stMarkdownContainer"] {{
      font-family: "Open Sans", "Segoe UI", Roboto, sans-serif;
  }}

  .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
      font-family: Montserrat, "Segoe UI", sans-serif !important;
      color: {AZUL} !important;
      font-weight: 600;
  }}
  .stApp h1 {{ font-weight: 700; letter-spacing: -.01em; }}

  .pie {{ color: {GRIS}; font-size: 0.8rem; line-height: 1.5; }}

  .volver {{ margin: 0 0 .35rem; font-size: .9rem; }}
  .volver a {{ color: {GRIS}; text-decoration: none; }}
  .volver a:hover {{ color: {AZUL}; text-decoration: underline; }}

  /* Contador de uso acumulado. */
  .contador {{
      display: inline-flex; align-items: baseline; gap: .55rem;
      margin: .1rem 0 1.1rem; padding: .5rem 1rem;
      background: #F4F8FB; border-left: 4px solid {AZUL}; border-radius: 4px;
  }}
  .contador-numero {{
      font-family: Montserrat, "Segoe UI", sans-serif;
      font-weight: 700; font-size: 1.75rem; color: {AZUL}; line-height: 1;
      font-variant-numeric: tabular-nums;
  }}
  .contador-texto {{ font-size: .92rem; color: {GRIS}; }}

  /* Instrucciones de arranque. Aquí son DOS pasos y no tres: la herramienta
     tiene un campo y un botón, y una lista larga sobre una pantalla simple la
     hace parecer complicada. */
  .pasos {{
      margin: .2rem 0 1.4rem; padding: .8rem 1rem .8rem 2.4rem;
      background: #F4F8FB; border-left: 4px solid {AZUL}; border-radius: 4px;
      font-size: .93rem; line-height: 1.75;
  }}
  .pasos li {{ padding-left: .15rem; }}
  .pasos strong {{ color: {AZUL}; }}

  .paso {{
      margin: 1.5rem 0 .45rem; font-family: Montserrat, "Segoe UI", sans-serif;
      font-weight: 600; font-size: .82rem; letter-spacing: .04em;
      text-transform: uppercase; color: {AZUL};
  }}

  /* El botón de buscar es la acción principal de la página. */
  .stApp button[kind="primaryFormSubmit"] {{
      font-family: Montserrat, "Segoe UI", sans-serif;
      font-weight: 600; font-size: 1.02rem; padding: .6rem 1rem;
      margin-top: .4rem;
  }}

  /* La advertencia de que esto no es el Registro Inmobiliario. */
  .aviso-ri {{
      border-left: 4px solid {ROJO}; background: #FDF4F4;
      border-radius: 4px; padding: .7rem 1rem; margin: .2rem 0 1.1rem;
      font-size: .9rem; line-height: 1.6; color: #4a3234;
  }}
  .aviso-ri a {{ color: {AZUL}; }}

  /* Una resultante ANULADA. Es la advertencia más fuerte de la pantalla y tiene
     que verse antes que el mapa: llegar a un terreno cuyo registro está anulado
     es el peor resultado posible de esta herramienta. */
  .anulada {{
      border-left: 5px solid {ROJO}; background: #FBE9E9;
      border-radius: 4px; padding: .9rem 1.1rem; margin: .3rem 0 1.2rem;
      font-size: .95rem; line-height: 1.65; color: #4a2020;
  }}

  /* La ficha del inmueble: monoespaciada para que los números queden
     alineados. */
  .ficha {{
      background: #F4F8FB; border-left: 4px solid {AZUL}; border-radius: 4px;
      padding: .85rem 1rem; margin: .2rem 0 1rem;
  }}
  .ficha dl {{ margin: 0; display: grid; grid-template-columns: auto 1fr;
               gap: .3rem 1rem; }}
  .ficha dt {{ color: {GRIS}; font-size: .85rem; white-space: nowrap; }}
  .ficha dd {{ margin: 0; font-family: Consolas, "Courier New", monospace;
               font-size: .95rem; color: #1a1a1a;
               font-variant-numeric: tabular-nums; }}

  /* Dónde queda, en grande. Es lo primero que quiere leer alguien que sólo
     tiene un número: antes de mirar el mapa ya sabe si acertó. */
  .donde {{
      font-family: Montserrat, "Segoe UI", sans-serif; font-weight: 600;
      font-size: 1.35rem; color: {AZUL}; margin: .1rem 0 .2rem;
      line-height: 1.3;
  }}
  .donde-nota {{ color: {GRIS}; font-size: .9rem; margin: 0 0 1rem; }}

  /* Cuando el punto tuvo que moverse porque el centro caía fuera. Ámbar y no
     rojo: no es un fallo, es una propiedad de la forma de la parcela — pero
     quien va a conducir hasta allí tiene que saberlo. */
  .ajustado {{
      border-left: 4px solid #B08900; background: #FDF9EC;
      border-radius: 4px; padding: .6rem .9rem; margin: .4rem 0 1rem;
      font-size: .89rem; color: #4a4326;
  }}

  .nota {{
      border-left: 4px solid #b9c4cc; background: #f7f8f9;
      border-radius: 4px; padding: .6rem .9rem; margin: .6rem 0 1rem;
      font-size: .89rem; color: {GRIS};
  }}

  /* Los dos botones de ir. Son el final del camino y tienen que verse como tal:
     grandes, con su icono, y ocupando el ancho en un teléfono — que es donde se
     van a pulsar, con el carro encendido. */
  .stApp a[data-testid="stBaseLinkButton-secondary"],
  .stApp a[data-testid="stBaseLinkButton-primary"] {{
      font-family: Montserrat, "Segoe UI", sans-serif;
      font-weight: 600; font-size: 1.05rem; padding: .7rem 1rem;
  }}

  /* El mapa es un componente de terceros con su propio iframe: sin este tope
     empuja la página a lo ancho en pantallas estrechas. */
  iframe {{ max-width: 100%; }}

  /* Sin páginas que listar, la barra lateral solo ocupa espacio. */
  section[data-testid="stSidebar"] {{ display: none; }}
</style>
"""
