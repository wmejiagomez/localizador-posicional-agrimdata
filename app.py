# -*- coding: utf-8 -*-
"""Localizador de inmuebles por posicional · Agrimensura.com.do

Se escribe el número posicional de un inmueble y la herramienta dice dónde queda:
lo sitúa sobre la foto aérea y ofrece abrir la ruta en Google Maps o en Waze.

Aquí solo está la pantalla: la consulta vive en `nucleo/ri.py`, el punto en
`nucleo/centroide.py`, la lectura de la respuesta en `nucleo/inmueble.py`, el mapa
en `nucleo/mapa.py` y los dos enlaces en `nucleo/navegacion.py`.

**Para quién está escrita esta pantalla.** No para un agrimensor: para el dueño de
un inmueble, que tiene un papel con un número y quiere saber dónde está el
terreno. Eso manda en cada decisión de aquí — dos pasos y no cinco, ninguna
casilla que elegir, ningún término del oficio sin explicar, y el resultado
—«dónde queda»— en letra grande antes que cualquier dato técnico.

**Por qué el resultado vive en `st.session_state`.** Streamlit reejecuta el script
entero en cada interacción, así que sin memoria cualquier clic volvería a
preguntarle al servidor del RI, que tarda once segundos.

**Por qué hay un botón y nada busca solo.** El portal oficial pone un reCAPTCHA
delante de cada consulta; el servicio OGC que hay detrás no lo tiene, y el límite
se lo pone esta herramienta a sí misma. Una búsqueda por acción pedida a
propósito.
"""

import datetime

import streamlit as st
from streamlit_folium import st_folium

from nucleo import (centroide, contador, coordenadas, inmueble, mapa, marca,
                    marco, navegacion, ri)

st.set_page_config(
    page_title="Localizador de inmuebles por posicional · Agrimensura.com.do",
    page_icon="assets/favicon.ico",
    layout="centered",
)

st.markdown(marca.CSS, unsafe_allow_html=True)

# Se publica la altura de esta página hacia la vitrina, para que el marco encaje
# sin barra de desplazamiento. Va aquí arriba y no al final **porque un
# `st.stop()` aborta el script**: con la llamada al final, la pantalla de partida
# —la que ve todo el mundo al llegar— no publicaría nada.
marco.publicar_alto()

INCRUSTADA = st.context.is_embedded

# El separador de millar del hub es el espacio fino U+202F, el mismo que usan las
# demás herramientas. Se escribe con su escape y no con el carácter suelto porque
# es invisible: en la Calculadora de área, un espacio normal colado aquí puso dos
# separadores distintos en la misma página y dejó una prueba fallando por un
# carácter que no se ve en el editor.
SEPARADOR_MILLAR = " "

# Lo que se enseña en el hueco del campo. **Es inventado y tiene que serlo**: un
# posicional real identifica el inmueble de alguien, y el texto de ayuda de un
# campo es exactamente donde nadie iría a buscarlo. Doce dígitos, empezando por
# nueves para que no pueda confundirse con uno de verdad.
EJEMPLO = "999999000001"


def con_millares(valor, decimales=0):
    return ("{:,.%df}" % decimales).format(valor).replace(",", SEPARADOR_MILLAR)


def pie_de_pagina():
    """El cierre de la página. Se llama desde cada salida, incluidas las cortas."""
    if not INCRUSTADA:
        st.divider()
        st.subheader(marca.CTA_TITULO)
        st.markdown(marca.CTA_TEXTO)
        st.link_button(marca.CTA_BOTON, marca.CTA_ENLACE)
        with st.expander("Aviso legal, privacidad y alcance"):
            st.markdown(marca.DESCARGO_LEGAL)
    st.markdown('<p class="pie">%s</p>' % marca.AVISO_PIE,
                unsafe_allow_html=True)


def olvidar_resultado():
    """Retira el resultado anterior.

    Sin esto queda en pantalla el inmueble de la búsqueda vieja debajo de un
    número nuevo, y nada lo delata: es la regla del protocolo del hub, y aquí
    muerde más fuerte porque el resultado es un mapa, y un mapa parece siempre
    actual.
    """
    for clave in ("fichas", "avisos", "momento", "buscado"):
        st.session_state.pop(clave, None)


# --------------------------------------------------------------- encabezado --

if not INCRUSTADA:
    st.markdown(
        '<p class="volver"><a href="%s">← Todas las herramientas</a></p>'
        % marca.URL_CATALOGO, unsafe_allow_html=True)

st.title("¿Dónde queda mi inmueble?")
st.caption(marca.DESCARGO_CORTO)


@st.cache_data(ttl=300, show_spinner=False)
def _leer_total():
    """El contador, una vez cada cinco minutos y no en cada interacción.

    `contador.leer()` pregunta a un servicio de fuera y tarda 0.75–0.87 s medidos.
    Streamlit reejecuta este script entero en cada interacción, así que sin esta
    caché cada una pagaba ese tiempo en serie **antes de pintar nada**. Ninguna
    prueba lo vería: el número que sale es correcto, solo tarde.
    """
    return contador.leer()


_total = _leer_total()
if _total:
    # El singular importa: la primera semana de una herramienta nueva el contador
    # está en uno o en dos, y «1 inmuebles localizados» es lo primero que ve
    # quien llega. Se vio en el navegador con el contador a 1, no en ninguna
    # prueba — las pruebas anulan el contador y nunca pintan este bloque.
    st.markdown(
        '<div class="contador"><span class="contador-numero">%s</span>'
        '<span class="contador-texto">%s</span></div>'
        % (con_millares(_total),
           "inmueble localizado" if _total == 1 else "inmuebles localizados"),
        unsafe_allow_html=True)

st.markdown(
    """<ol class="pasos">
    <li><strong>Escriba el número posicional</strong> del inmueble. Son doce
        dígitos y aparece en la certificación, en el plano o en el título que le
        dio el Registro Inmobiliario.</li>
    <li><strong>Pulse buscar</strong> y espere unos diez segundos. Le diremos en
        qué municipio está, se lo enseñaremos sobre la foto aérea y podrá abrir
        la ruta en Google Maps o en Waze.</li>
    </ol>""",
    unsafe_allow_html=True)

st.markdown('<div class="aviso-ri">%s</div>' % marca.AVISO_RI_HTML,
            unsafe_allow_html=True)


# ------------------------------------------------------------------ entrada --

st.markdown('<p class="paso">1 · El número posicional</p>',
            unsafe_allow_html=True)

with st.form("buscar"):
    escrito = st.text_input(
        "Número posicional",
        placeholder=EJEMPLO,
        max_chars=30,
        label_visibility="collapsed",
        help="Los doce dígitos, tal como aparecen en su documento. Puede "
             "pegarlos con espacios o guiones: se limpian solos.",
    )
    # `st.info` y no `st.caption`: once segundos de pantalla muda son una
    # herramienta que parece rota, y este público no tiene paciencia de
    # agrimensor. Medido el 2026-08-21 contra el servidor del RI: la capa de
    # aprobadas tarda 11.1–11.5 s ella sola, porque el campo no está indexado.
    st.info("La búsqueda tarda unos **diez segundos**. No es su conexión: el "
            "buscador del Registro Inmobiliario es lento cuando se le pregunta "
            "por un número.")
    pedir = st.form_submit_button("Buscar el inmueble", type="primary",
                                  width="stretch")

st.caption(
    "¿Lo que tiene es una designación catastral del tipo **999-X-1-B-18**, o un "
    "número de expediente? Esos se buscan en el "
    "[Visor Parcelario](%s), que además le entrega la parcela en DXF y KML."
    % marca.URL_PARCELARIO)


# ----------------------------------------------------------------- consulta --

if pedir:
    olvidar_resultado()
    momento = datetime.datetime.now()
    try:
        limpio = ri.limpiar(escrito)
    except ri.PosicionalInvalido as ex:
        st.warning(str(ex))
    else:
        # **El aviso de longitud NO se pinta aquí.** Se guarda y se pinta con el
        # resultado, después del `st.rerun()` de abajo: un `st.warning` escrito
        # en esta pasada desaparece con la reejecución, y el usuario nunca
        # llegaría a verlo. Lo cazó `test_app.py` en su primera ejecución —desde
        # fuera, un aviso que se pinta y se borra en el mismo segundo es
        # indistinguible de uno que no se escribió nunca.
        avisos_previos = []
        aviso_longitud = ri.longitud_rara(limpio)
        if aviso_longitud:
            avisos_previos.append(aviso_longitud)
        try:
            with st.spinner("Preguntándole al Registro Inmobiliario… "
                            "esto tarda unos diez segundos."):
                documentos = ri.por_posicional(limpio)
        except ri.ServidorCaido as ex:
            # **No es un fallo del usuario y no se puede decir de otra manera.**
            # Un «error al buscar» manda a revisar el número, que está bien.
            for aviso in avisos_previos:
                st.warning(aviso)
            st.error(ri.mensaje_de_caida(str(ex)))
        else:
            fichas, avisos = inmueble.leer(documentos)
            st.session_state["fichas"] = fichas
            st.session_state["avisos"] = avisos_previos + avisos
            st.session_state["momento"] = momento
            st.session_state["buscado"] = limpio
            # Se cuenta la búsqueda que se respondió, con o sin resultado: «ese
            # posicional no existe» es una respuesta, y le costó lo mismo al RI.
            contador.sumar(1)
            st.rerun()


# --------------------------------------------------------------- resultados --

fichas = st.session_state.get("fichas")
if fichas is None:
    pie_de_pagina()
    st.stop()

momento = st.session_state.get("momento")
buscado = st.session_state.get("buscado", "")

for aviso in st.session_state.get("avisos") or []:
    st.warning(aviso)

st.divider()

if not fichas:
    st.warning(
        "**No encontramos ningún inmueble con ese número posicional.**\n\n"
        "El Registro Inmobiliario respondió y no tiene nada inscrito con el "
        "número **%s** en ninguna de sus tres capas de resultantes. Las causas "
        "más frecuentes, por orden:\n\n"
        "1. **Un dígito mal copiado.** Son doce y es fácil bailar uno; "
        "compruébelo contra su documento.\n"
        "2. **No es un posicional.** Si su número tiene letras o guiones "
        "—como 999-X-1-B-18— es una designación catastral, y esa se busca en "
        "el [Visor Parcelario](%s).\n"
        "3. **El inmueble no está en el parcelario publicado.** El RI no publica "
        "todo: hay huecos, sobre todo en terrenos que nunca pasaron por una "
        "mensura moderna.\n\n"
        "Consultado el %s."
        % (buscado, marca.URL_PARCELARIO,
           momento.strftime("%d/%m/%Y a las %H:%M") if momento else "—"))
    pie_de_pagina()
    st.stop()

# **Con varios resultados se enseñan todos, y el anulado no se esconde.** El RI
# publica el mismo posicional en más de una capa y hasta repetido dentro de una
# —el Visor Parcelario encontró dos parcelas distintas con el mismo número—. Aquí
# se ordena por `ri.ORDEN`, así que la aprobada sale primero y la anulada al
# final, con su advertencia.
if len(fichas) > 1:
    st.info(
        "El Registro Inmobiliario devolvió **%d resultados** para ese número. "
        "Se muestran todos, empezando por el vigente. Si alguno figura anulado, "
        "va marcado." % len(fichas))

for numero, f in enumerate(fichas, 1):
    if len(fichas) > 1:
        st.subheader("Resultado %d de %d" % (numero, len(fichas)))

    if f["anulada"]:
        st.markdown('<div class="anulada"><strong>⚠ Esta resultante está '
                    'ANULADA en el Registro Inmobiliario.</strong><br>%s</div>'
                    % f["nota"], unsafe_allow_html=True)

    if f["aviso_pais"]:
        # El punto no lo escribió el usuario: lo devolvió el RI. Que caiga fuera
        # del país significa que el dato oficial está mal proyectado, y entonces
        # los enlaces de navegación no se pueden ofrecer.
        st.error(f["aviso_pais"])

    donde = inmueble.donde(f)
    st.markdown('<p class="donde">%s</p>'
                % (donde or "Ubicación no declarada por el RI"),
                unsafe_allow_html=True)
    st.markdown('<p class="donde-nota">%s · consultado el %s</p>'
                % (f["etiqueta"],
                   momento.strftime("%d/%m/%Y a las %H:%M") if momento else "—"),
                unsafe_allow_html=True)

    # ------------------------------------------------------------- el mapa --

    # La proyección a grados se hace **una sola vez y aquí**, y el punto ya venía
    # calculado de `inmueble.ficha`. Así el contorno del mapa, la chincheta y los
    # dos enlaces de navegación salen todos del mismo cálculo: el fallo de que el
    # mapa señale un sitio y Waze lleve a otro sería invisible en cualquier
    # prueba de contenido.
    anillos_geo = [
        ([coordenadas.utm_a_geo(e, n, ri.ZONA) for e, n in puntos], hueco)
        for puntos, hueco in f["anillos"]
    ]
    st_folium(mapa.construir(f, anillos_geo), height=mapa.ALTO,
              use_container_width=True, returned_objects=[],
              key="mapa_%d" % numero)

    if f["punto_ajustado"]:
        st.markdown(
            '<div class="ajustado"><strong>El punto se movió hacia dentro de '
            'la parcela.</strong> Su terreno tiene una forma irregular —una L, '
            'una U o parecido— y su centro geométrico caía fuera de él. El '
            'punto que le damos sí está dentro, pero <strong>no es el centro'
            '</strong>: úselo para llegar a la zona, no para situarse respecto '
            'a los linderos.</div>',
            unsafe_allow_html=True)

    # -------------------------------------------------------- cómo llegar --

    st.markdown('<p class="paso">2 · Cómo llegar</p>', unsafe_allow_html=True)

    if f["aviso_pais"]:
        st.caption("No se ofrecen enlaces de navegación: las coordenadas que "
                   "devolvió el Registro Inmobiliario no caen en el país.")
    else:
        izquierda, derecha = st.columns(2)
        for columna, enlace in zip((izquierda, derecha),
                                   navegacion.enlaces(f["lat"], f["lon"])):
            with columna:
                # `type="primary"` y no el secundario por defecto: estos dos
                # botones son el final del camino —lo que el usuario vino a
                # pulsar— y con el borde gris de Streamlit se leían como un
                # control más de la página. Se vio mirando la pantalla montada,
                # no en ninguna prueba.
                st.link_button("%s  Ir con %s"
                               % (enlace["icono"], enlace["nombre"]),
                               enlace["url"], width="stretch",
                               type="primary", help=enlace["ayuda"])

        st.caption(
            "Coordenadas para copiar y pegar en cualquier otra aplicación: "
            "`%s`" % navegacion.coordenadas_para_pegar(f["lat"], f["lon"]))

    # ------------------------------------------------------------- la ficha --

    with st.expander("Los datos que publica el Registro Inmobiliario"):
        lineas = ['<div class="ficha"><dl>']
        for rotulo, valor in f["datos"]:
            lineas.append("<dt>%s</dt><dd>%s</dd>" % (rotulo, valor))
        lineas.append(
            "<dt>Superficie</dt><dd>%s</dd>"
            % ("el RI no la declara" if f["area_declarada"] is None
               else con_millares(f["area_declarada"], 2) + " m²"))
        lineas.append("<dt>Coordenadas UTM 19N</dt><dd>E %s · N %s</dd>"
                      % (con_millares(f["este"], 2),
                         con_millares(f["norte"], 2)))
        lineas.append("<dt>Coordenadas geográficas</dt><dd>%s · %s</dd>"
                      % (coordenadas.a_dms(f["lat"], True),
                         coordenadas.a_dms(f["lon"], False)))
        lineas.append("</dl></div>")
        st.markdown("".join(lineas), unsafe_allow_html=True)

        diferencia = inmueble.diferencia_de_areas(f)
        if diferencia is not None:
            st.markdown(
                '<div class="nota">La superficie que <strong>declara</strong> '
                'el RI (%s m²) y la que resulta de <strong>medir</strong> la '
                'figura que él mismo entrega (%s m²) no coinciden exactamente: '
                'se separan en %s m². No es un error de esta herramienta — son '
                'dos números del registro que no cuadran entre sí. Para '
                'contrastarlos en serio está el <a href="%s" target="_blank" '
                'rel="noopener">Visor Parcelario</a>.</div>'
                % (con_millares(f["area_declarada"], 2),
                   con_millares(f["area_medida"], 2),
                   con_millares(diferencia, 2), marca.URL_PARCELARIO),
                unsafe_allow_html=True)

        st.caption(
            "El punto que se le da es %s de la parcela, calculado sobre la "
            "figura que publica el RI. **No son los linderos**: para saber por "
            "dónde pasa la línea de su terreno hace falta una mensura en el "
            "sitio."
            % ("un punto interior" if f["punto_ajustado"] else "el centro"))

    if numero < len(fichas):
        st.divider()

# **No se repite el aviso de arriba.** Ver `marca.RECORDATORIO_FINAL_HTML`: aquí
# va la advertencia que solo tiene sentido con un resultado delante, que es que
# el punto sirve para llegar y no para medir.
st.markdown('<div class="nota">%s</div>' % marca.RECORDATORIO_FINAL_HTML,
            unsafe_allow_html=True)

pie_de_pagina()
