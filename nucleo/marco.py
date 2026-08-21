# -*- coding: utf-8 -*-
"""Decirle a la vitrina cuánto mide esta herramienta, para que el marco encaje.

El problema, en una línea: la vitrina vive en `localizador.agrimensura.com.do` y
la aplicación en `localizador.app.agrimensura.com.do`. Son orígenes distintos, así
que **la página de fuera no puede leer la altura de la de dentro** —
`iframe.contentDocument` lanza `TypeError`—. De ahí venían las alturas escritas a
mano en el CSS de cada vitrina, y de ahí la barra de desplazamiento lateral
cuando el contenido pasaba de esa cifra.

Si el de fuera no puede preguntar, el de dentro tiene que hablar. Eso es todo lo
que hace este módulo: `window.postMessage` con la altura, al cargar y cada vez que
el contenido cambia.

**Por qué no se usa el iframe-resizer que Streamlit ya trae.** Sí lo trae, y
funciona al cargar — pero **solo informa una vez**. En cuanto el usuario busca
algo y la página crece con el mapa y los botones, el marco **corta** el contenido,
que es peor que la barra que se quería quitar. Aquí eso muerde más que en ninguna
otra herramienta del hub: la página de partida es un campo y un botón, y la de
resultado trae un mapa de 460 px. Es el mayor salto de altura del hub.

Este módulo está en las quince herramientas y es idéntico en todas. Su historia
completa —los tres fallos que costó, con las mediciones— está en `PROGRAMA.md`.
"""

import streamlit as st
import streamlit.components.v1 as componentes

# El mensaje lleva nombre propio para que la vitrina no confunda esto con los que
# manda el propio Streamlit —`SCRIPT_RUN_STATE_CHANGED`, `SET_THEME_CONFIG` y
# compañía—, que viajan por el mismo canal.
TIPO = "agrimensura:alto"


_GUION = """
<script>
(function () {
  // Este bloque corre dentro de un iframe que Streamlit crea para el
  // componente. Su padre es el documento de la aplicación, y el padre de ese es
  // la vitrina. Se mide el de en medio y se le habla al de arriba.
  var doc = null, motivo = "";
  try { doc = window.parent.document; }
  catch (e) { doc = null; motivo = e.name; }

  // Diagnóstico: se avisa SIEMPRE, aunque no se pueda medir. Un bloque que calla
  // no distingue «no corrí» de «corrí y no pude», y esas dos se arreglan en
  // sitios distintos.
  try {
    window.parent.parent.postMessage(
      {tipo: "TIPO_MENSAJE:diagnostico", puedo: !!doc, motivo: motivo,
       profundidad: (window.parent === window.top ? 1 : (window.parent.parent === window.top ? 2 : 3))}, "*");
  } catch (e) { /* nada que hacer */ }

  if (!doc) { return; }

  // QUÉ se mide, que es donde estuvo el error. `documentElement.scrollHeight`
  // devolvía exactamente la altura del marco —1000 px pedidos, 1000 px
  // medidos—: el `<html>` se estira a su contenedor, así que preguntarle cuánto
  // ocupa es preguntarle al marco por sí mismo. Lo que ocupa de verdad es el
  // bloque de contenido, medido por su borde inferior.
  function contenedor() {
    return doc.querySelector(".block-container")
        || doc.querySelector('[data-testid="stVerticalBlock"]')
        || doc.querySelector('[data-testid="stMain"]');
  }

  var ultimo = 0;
  var MARGEN = 8;

  function publicar() {
    var c = contenedor();
    if (!c || !c.children.length) { return; }

    var caja = c.getBoundingClientRect();
    var alto = Math.ceil(caja.bottom + (window.parent.scrollY || 0)) + MARGEN;
    // Un umbral pequeño evita un ir y venir de mensajes por diferencias de un
    // píxel al redondear.
    if (Math.abs(alto - ultimo) < 8) { return; }
    ultimo = alto;
    try {
      window.parent.parent.postMessage(
        {tipo: "TIPO_MENSAJE", alto: alto}, "*");
    } catch (e) { /* la vitrina decide si escucha */ }
  }

  publicar();
  // El contenido crece cuando aparece el resultado con su mapa.
  if (window.ResizeObserver) {
    new ResizeObserver(publicar).observe(contenedor());
  }
  // Y por si acaso: al terminar de cargar fuentes e imágenes, y un par de
  // repasos tardíos para lo que Streamlit pinta después del primer cuadro. El
  // mapa de folium tarda en montarse y es lo que más altura añade.
  window.parent.addEventListener("load", publicar);
  setTimeout(publicar, 400);
  setTimeout(publicar, 1500);
})();
</script>
"""


def publicar_alto():
    """Publica la altura hacia la vitrina. No pinta nada visible.

    Se llama **arriba** de `app.py`, detrás del CSS, y no al final: un `st.stop()`
    aborta el script, y la pantalla de partida —la que ve todo el mundo al
    llegar— no publicaría nada. Quien mide es el JavaScript del navegador, sobre
    el DOM ya pintado, así que llamar pronto no adelanta la medición.
    """
    if not st.context.is_embedded:
        # Fuera del marco no hay a quién decírselo.
        return
    # Altura 1 y no 0: con 0, Streamlit no llega a montar el componente y el
    # guion nunca corre. Costó dos despliegues descubrirlo, porque un bloque que
    # no corre y uno que corre sin poder medir se ven exactamente igual desde
    # fuera — de ahí el mensaje de diagnóstico que va más arriba.
    componentes.html(_GUION.replace("TIPO_MENSAJE", TIPO), height=1)
