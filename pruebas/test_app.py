# -*- coding: utf-8 -*-
"""La interfaz, con `AppTest`. Sin navegador y sin tocar la red.

    python pruebas/test_app.py

`ri.por_posicional` y el contador se sustituyen por dobles, así que la pantalla
se ejercita entera sin preguntarle nada al Registro Inmobiliario y sin inflarle
la cifra de uso — en Consulta de Expedientes las propias pruebas la subieron a 82
antes de lanzar.

**Los widgets se buscan por su rótulo, nunca por índice.** Es lo que se rompió
dos veces seguidas en División de parcelas: añadir un control arriba desplaza
todos los índices y la prueba pasa a comprobar otro campo sin decir nada.

`AppTest` **no ve la pantalla**. Que el mapa esté en su sitio, que los botones se
lean en un teléfono y que el marco encaje son cosas de la fase 6 del protocolo,
mirando el navegador.
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from streamlit.testing.v1 import AppTest                           # noqa: E402

from nucleo import contador, ri                                    # noqa: E402

FALLOS = []

with open(os.path.join(RAIZ, "datos", "inmuebles_ficticios.json"),
          encoding="utf-8") as f:
    CASOS = json.load(f)

APP = os.path.join(RAIZ, "app.py")


def cierto(condicion, que):
    if not condicion:
        FALLOS.append(que)


def igual(a, b, que):
    if a != b:
        FALLOS.append("%s: esperaba %r, llegó %r" % (que, b, a))


# ------------------------------------------------------------------ dobles --

class ContadorFalso:
    """Un doble **con la misma firma que la función real**.

    `sumar` exige la cantidad, igual que `contador.sumar`. En División de
    parcelas el doble era `lambda n=1: None`, más permisivo que la función real:
    la aplicación llamaba `sumar()` sin argumento, la batería entera pasaba y el
    usuario veía la pantalla roja. Un doble así no prueba, tapa.
    """

    def __init__(self):
        self.sumas = []

    def sumar(self, cantidad):
        self.sumas.append(cantidad)

    def leer(self):
        return 1234


def arrancar(respuesta=None, falla=None):
    """Una aplicación lista para correr, con la red sustituida.

    `respuesta` es lo que devolverá `por_posicional`; `falla` una excepción que
    lanzará en su lugar.
    """
    prueba = AppTest.from_file(APP, default_timeout=60)

    falso = ContadorFalso()
    contador.sumar = falso.sumar
    contador.leer = falso.leer

    pedidos = []

    def por_posicional(posicional, **kwargs):
        pedidos.append(posicional)
        if falla is not None:
            raise falla
        return respuesta if respuesta is not None else {}

    ri.por_posicional = por_posicional
    prueba._pedidos = pedidos
    prueba._contador = falso
    return prueba


def campo(prueba, rotulo):
    """Un widget por su ROTULO, nunca por índice."""
    for elemento in prueba.text_input:
        if elemento.label == rotulo:
            return elemento
    FALLOS.append("no se encontró el campo «%s»; hay: %s"
                  % (rotulo, [e.label for e in prueba.text_input]))
    return None


def boton(prueba, texto):
    for elemento in list(prueba.button):
        if texto.lower() in (elemento.label or "").lower():
            return elemento
    FALLOS.append("no se encontró el botón «%s»; hay: %s"
                  % (texto, [e.label for e in prueba.button]))
    return None


def todo_el_texto(prueba):
    """Todo lo que la pantalla escribió, junto, sin etiquetas y con un solo
    espacio entre palabras.

    **Lo de los espacios no es cosmético.** El bloque de instrucciones es un
    `<ol>` escrito en varias líneas del fuente, así que «Son doce dígitos» llega
    con un salto de línea y ocho espacios en medio: buscar la frase literal
    fallaba sobre un texto que la contiene perfectamente. Normalizando, la
    aserción comprueba lo que el usuario lee y no cómo está indentado el HTML.
    """
    import re
    trozos = []
    for grupo in (prueba.markdown, prueba.warning, prueba.error, prueba.info,
                  prueba.success, prueba.caption, prueba.title,
                  prueba.subheader):
        for elemento in grupo:
            trozos.append(str(elemento.value))
    crudo = "\n".join(trozos)
    return re.sub(r"[ \t\r\n]+", " ", re.sub(r"<[^>]+>", " ", crudo))


def enlaces(prueba):
    """Los `st.link_button` de la pantalla.

    `AppTest` no expone `link_button` como atributo —solo los tiene `get`—, así
    que se piden por nombre. Cada uno trae `label` y `url`.
    """
    return list(prueba.get("link_button"))


def urls(prueba):
    return " ".join(str(getattr(e, "url", "") or "") for e in enlaces(prueba))


# --------------------------------------------------------- la pantalla base --

def prueba_arranca_sin_errores():
    prueba = arrancar().run()
    igual(list(prueba.exception), [],
          "la pantalla de partida no puede lanzar ninguna excepción")


def prueba_la_pantalla_de_partida_explica_que_hace():
    prueba = arrancar().run()
    texto = todo_el_texto(prueba)
    cierto("posicional" in texto.lower(), "dice qué número hay que escribir")
    cierto("doce dígitos" in texto, "dice cuántos dígitos son")
    cierto("Google Maps" in texto and "Waze" in texto,
           "dice a dónde va a poder ir")


def prueba_avisa_de_que_tarda_ANTES_de_buscar():
    """Once segundos de pantalla muda son una herramienta que parece rota, y
    este público no tiene paciencia de agrimensor."""
    prueba = arrancar().run()
    texto = todo_el_texto(prueba)
    cierto("diez segundos" in texto,
           "la espera tiene que anunciarse antes de pulsar, no después")


def prueba_dice_que_no_es_el_registro_inmobiliario():
    prueba = arrancar().run()
    texto = todo_el_texto(prueba)
    cierto("no es el Registro Inmobiliario" in texto,
           "la advertencia va en la pantalla de partida, no escondida en el "
           "aviso legal")


def prueba_manda_al_visor_parcelario_a_quien_tiene_otro_numero():
    prueba = arrancar().run()
    texto = todo_el_texto(prueba)
    cierto("Visor Parcelario" in texto,
           "quien tiene una designación catastral tiene que saber a dónde ir")


def prueba_no_se_consulta_nada_al_cargar():
    """Una consulta por acción pedida a propósito. Nada al abrir la página."""
    prueba = arrancar().run()
    igual(prueba._pedidos, [],
          "abrir la página no puede preguntarle nada al servidor del RI")


def prueba_no_hay_ningun_boton_de_descarga():
    """La línea con el Visor Parcelario, comprobada sobre la pantalla montada."""
    fichas = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]})
    fichas = fichas.run()
    campo(fichas, "Número posicional").set_value("999999000001")
    boton(fichas, "Buscar").click().run()
    igual(len(list(fichas.download_button)), 0,
          "esta herramienta no descarga nada, ni siquiera con un resultado en "
          "pantalla")


# ------------------------------------------------------------- la búsqueda --

def prueba_un_posicional_bueno_encuentra_el_inmueble():
    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()

    igual(list(prueba.exception), [], "buscar no puede reventar")
    igual(prueba._pedidos, ["999999000001"],
          "se le pide al RI exactamente lo que se escribió, ya limpio")
    texto = todo_el_texto(prueba)
    cierto("Municipio De Prueba" in texto,
           "se enseña dónde queda, que es lo primero que quiere leer alguien "
           "que solo tiene un número")


def prueba_se_cuenta_la_busqueda_respondida():
    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()
    igual(prueba._contador.sumas, [1],
          "una búsqueda respondida suma exactamente uno, y con el argumento "
          "puesto")


def prueba_salen_los_dos_enlaces_de_ir():
    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()

    juntos = urls(prueba)
    cierto("google.com/maps/dir" in juntos,
           "tiene que salir el enlace de Google Maps en modo ruta: %s" % juntos)
    cierto("waze.com/ul" in juntos and "navigate=yes" in juntos,
           "y el de Waze navegando: %s" % juntos)
    rotulos = [e.label for e in enlaces(prueba)]
    cierto(any("Google Maps" in (r or "") for r in rotulos)
           and any("Waze" in (r or "") for r in rotulos),
           "y los dos botones tienen que decir a dónde llevan: %s" % rotulos)


def prueba_los_enlaces_llevan_la_longitud_negativa():
    """Sin el signo, el inmueble aparece en Arabia Saudí y el mapa abre igual."""
    import re
    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()

    juntos = urls(prueba)
    pares = re.findall(r"(-?\d+\.\d+)(?:,|%2C)(-?\d+\.\d+)", juntos)
    cierto(pares, "los enlaces tienen que llevar un par de coordenadas: %s"
                  % juntos[:300])
    for lat, lon in pares:
        cierto(float(lon) < 0,
               "la longitud del enlace tiene que ser negativa y llegó %s" % lon)
        cierto(17.0 < float(lat) < 20.0,
               "y la latitud caer en el país, y llegó %s" % lat)


def prueba_una_parcela_en_ele_avisa_de_que_el_punto_se_movio():
    prueba = arrancar(
        respuesta={"previo2017": CASOS["previo2017_en_ele"]}).run()
    campo(prueba, "Número posicional").set_value("999999000002")
    boton(prueba, "Buscar").click().run()
    texto = todo_el_texto(prueba)
    cierto("se movió hacia dentro" in texto,
           "cuando el centro cae fuera, la pantalla tiene que decir que el "
           "punto se movió")
    cierto("no es el centro" in texto,
           "y dejar claro que ese punto no es el centro del terreno")


def prueba_una_anulada_se_avisa_a_gritos():
    prueba = arrancar(respuesta={"anuladas": CASOS["anulada"]}).run()
    campo(prueba, "Número posicional").set_value("999999000003")
    boton(prueba, "Buscar").click().run()
    texto = todo_el_texto(prueba)
    cierto("ANULADA" in texto,
           "una resultante anulada tiene que decirlo en mayúsculas y arriba: "
           "es lo que no se puede descubrir tarde")


def prueba_un_posicional_que_no_existe_da_un_mensaje_util():
    """Es el segundo resultado más frecuente: la gente teclea mal doce dígitos."""
    prueba = arrancar(respuesta={"aprobadas": CASOS["vacio"]}).run()
    campo(prueba, "Número posicional").set_value("999999000099")
    boton(prueba, "Buscar").click().run()
    texto = todo_el_texto(prueba)
    cierto("No encontramos" in texto, "se dice que no se encontró")
    cierto("dígito mal copiado" in texto,
           "y se da la causa más probable primero, en vez de dejar al usuario "
           "mirando una pantalla vacía")
    cierto("Visor Parcelario" in texto,
           "y a dónde ir si lo que tiene es otro tipo de número")


def prueba_el_servidor_caido_no_se_confunde_con_no_existe():
    prueba = arrancar(falla=ri.ServidorCaido("HTTP 504")).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()

    igual(list(prueba.exception), [],
          "una caída del RI no puede reventar la pantalla")
    texto = todo_el_texto(prueba)
    cierto("Registro Inmobiliario" in texto and "no respondió" in texto,
           "tiene que decir que el servidor del RI no respondió")
    cierto("no es un problema de su número" in texto.lower(),
           "y que no es culpa del usuario, que es lo que evita que se ponga a "
           "revisar un número que estaba bien")


def prueba_un_numero_invalido_no_sale_a_la_red():
    prueba = arrancar().run()
    campo(prueba, "Número posicional").set_value("999-X-1-B-18")
    boton(prueba, "Buscar").click().run()

    igual(prueba._pedidos, [],
          "una designación catastral no puede llegar al servidor del RI")
    texto = todo_el_texto(prueba)
    cierto("Visor Parcelario" in texto,
           "y hay que decirle a dónde ir con ese número")


def prueba_buscar_vacio_no_sale_a_la_red():
    prueba = arrancar().run()
    boton(prueba, "Buscar").click().run()
    igual(prueba._pedidos, [],
          "pulsar buscar con el campo vacío no consulta nada")
    igual(list(prueba.exception), [], "y no revienta")


def prueba_un_numero_de_longitud_rara_avisa_pero_se_consulta():
    """Rechazarlo dejaría la herramienta inservible para ese inmueble y le
    echaría la culpa a quien lo escribió bien."""
    prueba = arrancar(respuesta={"aprobadas": CASOS["vacio"]}).run()
    campo(prueba, "Número posicional").set_value("99999900001")
    boton(prueba, "Buscar").click().run()
    igual(prueba._pedidos, ["99999900001"],
          "un número de once dígitos se consulta igual")
    texto = todo_el_texto(prueba)
    cierto("12 dígitos" in texto or "doce dígitos" in texto.lower(),
           "pero se avisa de que la longitud no es la habitual")


def prueba_una_busqueda_nueva_retira_el_resultado_viejo():
    """Sin esto queda en pantalla el inmueble anterior debajo de un número
    nuevo, y un mapa parece siempre actual."""
    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()
    cierto("Municipio De Prueba" in todo_el_texto(prueba),
           "primero se encuentra algo")

    # Ahora el servidor se cae: lo que estaba en pantalla no puede quedarse.
    def se_cae(posicional, **kwargs):
        raise ri.ServidorCaido("HTTP 504")

    ri.por_posicional = se_cae
    campo(prueba, "Número posicional").set_value("999999000077")
    boton(prueba, "Buscar").click().run()
    texto = todo_el_texto(prueba)
    cierto("no respondió" in texto, "se enseña la caída")
    cierto("Municipio De Prueba" not in texto,
           "y NO puede quedar en pantalla el inmueble de la búsqueda anterior")


def prueba_varios_resultados_se_enseñan_todos():
    """El RI publica el mismo posicional en más de una capa."""
    prueba = arrancar(respuesta={
        "aprobadas": CASOS["aprobada_simple"],
        "anuladas": CASOS["repetido_en_anuladas"],
    }).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()
    texto = todo_el_texto(prueba)
    cierto("2 resultados" in texto,
           "se avisa de que hay más de uno")
    cierto("ANULADA" in texto,
           "y el anulado no se esconde detrás del vigente")


def prueba_fuera_del_pais_no_ofrece_navegacion():
    """El punto lo devolvió el RI mal proyectado: no se puede mandar a nadie."""
    prueba = arrancar(respuesta={"aprobadas": CASOS["fuera_del_pais"]}).run()
    campo(prueba, "Número posicional").set_value("999999000009")
    boton(prueba, "Buscar").click().run()
    texto = todo_el_texto(prueba)
    cierto("fuera de la República Dominicana" in texto,
           "se avisa de que el punto cae fuera del país")
    cierto("waze.com" not in urls(prueba),
           "y NO se ofrece la ruta a un punto que el propio RI publicó mal")


def prueba_una_geometria_rota_avisa_y_no_revienta():
    prueba = arrancar(respuesta={"aprobadas": CASOS["geometria_rota"]}).run()
    campo(prueba, "Número posicional").set_value("999999000008")
    boton(prueba, "Buscar").click().run()
    igual(list(prueba.exception), [],
          "una geometría rota del RI no puede tumbar la pantalla")
    cierto("geometría rota" in todo_el_texto(prueba),
           "y se dice qué pasó")


def prueba_el_aviso_del_ri_no_sale_dos_veces_palabra_por_palabra():
    """Se vio mirando la pantalla montada, no en ninguna prueba de contenido.

    La primera versión pintaba el mismo párrafo arriba y al cerrar el resultado.
    Dos apariciones idénticas en un solo desplazamiento no se leen como énfasis:
    se leen como un fallo de la página, y hacen que se salte también la de
    arriba. Abajo va ahora la advertencia que solo tiene sentido con un resultado
    delante — que el punto sirve para llegar y no para medir.
    """
    from nucleo import marca

    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()

    import re
    limpio = re.sub(r"<[^>]+>", " ", marca.AVISO_RI_HTML)
    limpio = re.sub(r"[ \t\r\n]+", " ", limpio).strip()
    texto = todo_el_texto(prueba)
    igual(texto.count(limpio), 1,
          "el aviso del RI tiene que aparecer UNA sola vez en la pantalla con "
          "resultado, y apareció %d" % texto.count(limpio))

    cierto("no para medir" in texto,
           "y el cierre tiene que ser el recordatorio propio de esta "
           "herramienta: el punto sirve para llegar, no para medir")


def prueba_los_botones_de_ir_son_los_principales():
    """Son el final del camino y tienen que leerse como tal.

    Con el estilo secundario de Streamlit —borde gris sobre blanco— quedaban
    como un control más de la página, al lado de «Escribir por WhatsApp». Se vio
    mirando la pantalla montada.
    """
    prueba = arrancar(respuesta={"aprobadas": CASOS["aprobada_simple"]}).run()
    campo(prueba, "Número posicional").set_value("999999000001")
    boton(prueba, "Buscar").click().run()

    de_ir = [e for e in enlaces(prueba) if "Ir con" in (e.label or "")]
    igual(len(de_ir), 2, "salen los dos botones de ir")
    for elemento in de_ir:
        tipo = getattr(getattr(elemento, "proto", None), "type", None)
        cierto(tipo == "primary",
               "«%s» tiene que ser un botón primario y es %r"
               % (elemento.label, tipo))


def prueba_el_ejemplo_del_campo_es_inventado():
    """El hueco de un campo es exactamente donde nadie iría a buscar el
    identificador del inmueble de alguien."""
    prueba = arrancar().run()
    entrada = campo(prueba, "Número posicional")
    hueco = getattr(entrada, "placeholder", "") or ""
    cierto(hueco.startswith("999"),
           "el ejemplo del campo tiene que empezar por nueves para que no pueda "
           "confundirse con un posicional real, y es «%s»" % hueco)


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
    print("[OK] %d pruebas de la interfaz." % len(pruebas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
