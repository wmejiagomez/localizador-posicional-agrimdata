# -*- coding: utf-8 -*-
"""La capa de red, con dobles y **sin tocar internet**.

Todo lo de aquí corre con el cable desenchufado: `_pedir_http` se sustituye por
un doble que devuelve lo que la prueba decida. Eso permite comprobar lo que de
verdad importa y que contra el servidor real sería imposible provocar a
voluntad — un 504, un XML donde se esperaba JSON, una capa caída y las otras dos
en pie.

La única prueba que sale a la red es `test_red_real.py`, va aparte y es
salteable.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import ri                                              # noqa: E402

FALLOS = []


def cierto(condicion, que):
    if not condicion:
        FALLOS.append(que)


def igual(a, b, que):
    if a != b:
        FALLOS.append("%s: esperaba %r, llegó %r" % (que, b, a))


VACIO = '{"type":"FeatureCollection","features":[]}'
UNO = ('{"type":"FeatureCollection","features":[{"type":"Feature",'
       '"id":"Aprobados.1","geometry":{"type":"Polygon","coordinates":'
       '[[[400000,2050000],[400020,2050000],[400020,2050010],'
       '[400000,2050010],[400000,2050000]]]},'
       '"properties":{"Posicional":"999999000001","Area":200.0}}]}')


class Doble:
    """Un `pedir` de mentira que apunta lo que se le pidió.

    Guarda cada llamada para que las pruebas puedan comprobar **qué** se le
    mandó al servidor, no solo qué se hizo con la respuesta.
    """

    def __init__(self, respuestas=None, por_defecto=(200, VACIO)):
        self.respuestas = respuestas or {}
        self.por_defecto = por_defecto
        self.llamadas = []

    def __call__(self, url, parametros, espera):
        self.llamadas.append({"url": url, "parametros": dict(parametros),
                              "espera": espera, "cuando": time.time()})
        tipo = parametros.get("typeNames")
        respuesta = self.respuestas.get(tipo, self.por_defecto)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def _tipo(capa):
    return ri.CAPAS[capa]["tipo"]


# --------------------------------------------------------------- la entrada --

def prueba_limpiar_quita_la_basura_de_copiar_y_pegar():
    # Los números de aquí son **inventados** y empiezan por nueves, que es la
    # convención de este repositorio. La primera versión de esta prueba usaba el
    # posicional real del caso que originó la herramienta, copiado del Excel: lo
    # cazó `test_privacidad.py`, que es exactamente para lo que existe.
    igual(ri.limpiar(" 9999 9900-0001 "), "999999000001",
          "un posicional pegado con espacios y guiones se limpia")
    igual(ri.limpiar("999.999.000.002"), "999999000002",
          "los puntos de millar se quitan")


def prueba_vacio_no_sale_a_la_red():
    for entrada in ("", "   ", None):
        try:
            ri.limpiar(entrada)
        except ri.PosicionalInvalido:
            pass
        else:
            FALLOS.append("%r tenía que dar PosicionalInvalido" % (entrada,))


def prueba_una_designacion_catastral_se_rechaza_diciendo_donde_ir():
    try:
        ri.limpiar("999-X-1-B-18")
    except ri.PosicionalInvalido as ex:
        cierto("Visor Parcelario" in str(ex),
               "al rechazar una designación catastral hay que decir a qué "
               "herramienta ir, y el mensaje fue: %s" % ex)
    else:
        FALLOS.append("una designación catastral tenía que rechazarse")


def prueba_la_longitud_rara_avisa_pero_no_bloquea():
    igual(ri.longitud_rara("999999000001"), None,
          "doce dígitos no llevan aviso")
    cierto(ri.longitud_rara("99999900001") is not None,
           "once dígitos tienen que avisar")
    # Y lo importante: avisar, no impedir. `limpiar` no lanza por longitud.
    igual(ri.limpiar("99999900001"), "99999900001",
          "un número de longitud rara se limpia igual y se puede consultar: "
          "rechazarlo dejaría la herramienta inservible para ese inmueble")


# ---------------------------------------------------------- los parámetros --

def prueba_el_filtro_lleva_comillas():
    """`Posicional` es `xsd:string` en las tres capas, medido el 2026-08-21."""
    p = ri.parametros_de("aprobadas", "999999000001")
    igual(p["CQL_FILTER"], "Posicional = '999999000001'",
          "el filtro CQL de un campo de texto va entrecomillado")


def prueba_la_comilla_simple_se_escapa():
    p = ri.parametros_de("aprobadas", "12'34")
    cierto("''" in p["CQL_FILTER"],
           "una comilla simple se escapa duplicándola, y salió: %s"
           % p["CQL_FILTER"])


def prueba_se_pide_json_y_el_sistema_del_ri():
    p = ri.parametros_de("aprobadas", "999999000001")
    igual(p["outputFormat"], "application/json", "se pide JSON")
    igual(p["srsName"], ri.CRS_URN, "se pide en UTM 19N, como sirve el RI")
    igual(p["service"], "WFS", "es una consulta WFS")


def prueba_las_historicas_no_estan_en_las_capas():
    """No tienen campo `Posicional`: pedírselo da un error del servidor.

    Es un error que se vería como «ese posicional no existe» y mandaría al
    usuario a revisar un número correcto.
    """
    cierto("historicas" not in ri.CAPAS,
           "las parcelas históricas no pueden estar en CAPAS: no tienen "
           "campo Posicional")
    for clave, definicion in ri.CAPAS.items():
        cierto(ri.CAMPO_POSICIONAL in definicion["campos"],
               "la capa «%s» tiene que declarar el campo Posicional" % clave)


# -------------------------------------------------------------- la consulta --

def prueba_se_consultan_las_tres_capas():
    doble = Doble()
    ri.por_posicional("999999000001", pedir=doble, pausa=0)
    pedidos = {ll["parametros"]["typeNames"] for ll in doble.llamadas}
    igual(pedidos, {_tipo(c) for c in ri.ORDEN},
          "hay que preguntarle a las tres capas: el posicional no dice en cuál "
          "está, y el caso que originó la herramienta estaba en previo2017")


def prueba_van_en_paralelo_y_no_en_fila():
    """15.9 s en serie contra 11.1 s a la vez, medido el 2026-08-21.

    Se comprueba con dobles que duermen: en serie el total sería la suma, en
    paralelo el máximo. Es la única forma de probarlo sin cronometrar el
    servidor del RI, que ni se puede repetir ni se debe.
    """
    demora = 0.30

    def lento(url, parametros, espera):
        time.sleep(demora)
        return 200, VACIO

    arranque = time.time()
    ri.por_posicional("999999000001", pedir=lento, pausa=0)
    tardo = time.time() - arranque

    en_serie = demora * len(ri.ORDEN)
    cierto(tardo < en_serie * 0.75,
           "las tres capas tienen que consultarse a la vez: en serie serían "
           "%.2f s y tardó %.2f s" % (en_serie, tardo))


def prueba_en_serie_cuando_se_pide():
    """El modo de las pruebas existe y hace lo que dice."""
    doble = Doble()
    ri.por_posicional("999999000001", pedir=doble, pausa=0, en_paralelo=False)
    orden = [ll["parametros"]["typeNames"] for ll in doble.llamadas]
    igual(orden, [_tipo(c) for c in ri.ORDEN],
          "en serie el orden tiene que ser el de ri.ORDEN")


def prueba_una_capa_caida_no_cancela_el_resultado():
    """Que aprobadas se caiga no puede negarle su parcela a quien la tiene en
    previo2017. Es un fallo parcial, no un fracaso."""
    doble = Doble({
        _tipo("aprobadas"): (503, "se cayó"),
        _tipo("previo2017"): (200, UNO),
        _tipo("anuladas"): (200, VACIO),
    })
    salida = ri.por_posicional("999999000001", pedir=doble, pausa=0)
    cierto("previo2017" in salida,
           "la capa que sí contestó tiene que estar en el resultado")
    cierto("aprobadas" not in salida,
           "la capa caída no aparece, y por su ausencia se sabe cuál falló")


def prueba_si_se_caen_las_tres_es_servidor_caido():
    doble = Doble(por_defecto=(500, "roto"))
    try:
        ri.por_posicional("999999000001", pedir=doble, pausa=0)
    except ri.ServidorCaido:
        pass
    else:
        FALLOS.append("con las tres capas caídas hay que lanzar ServidorCaido")


def prueba_cero_resultados_NO_es_un_fallo():
    """Un 200 con cero rasgos es una respuesta legítima: «ese número no existe».

    Confundirlo con una caída le diría al usuario que vuelva más tarde cuando lo
    que tiene que hacer es revisar el número.
    """
    doble = Doble()
    salida = ri.por_posicional("999999000001", pedir=doble, pausa=0)
    igual(len(salida), len(ri.ORDEN),
          "las tres contestaron, aunque ninguna traiga nada")
    for capa, documento in salida.items():
        igual(documento["features"], [], "«%s» vino vacía" % capa)


def prueba_un_200_con_xml_no_se_traga():
    """GeoServer devuelve 200 con un `ServiceExceptionReport` en XML cuando la
    consulta le parece mal formada. Un 200 no garantiza JSON."""
    doble = Doble(por_defecto=(200, "<ServiceExceptionReport/>"))
    try:
        ri.por_posicional("999999000001", pedir=doble, pausa=0)
    except ri.ServidorCaido as ex:
        cierto("ilegible" in str(ex),
               "el motivo tiene que decir que la respuesta era ilegible")
    else:
        FALLOS.append("un 200 con XML tiene que tratarse como fallo")


def prueba_un_200_sin_features_no_se_traga():
    doble = Doble(por_defecto=(200, '{"type":"Algo"}'))
    try:
        ri.por_posicional("999999000001", pedir=doble, pausa=0)
    except ri.ServidorCaido:
        pass
    else:
        FALLOS.append("un JSON sin «features» tiene que tratarse como fallo")


def prueba_un_4xx_no_se_reintenta():
    """Repetir un 4xx da el mismo 4xx y le cuesta al servidor del RI lo mismo."""
    doble = Doble(por_defecto=(400, "no me gusta"))
    try:
        ri.por_posicional("999999000001", pedir=doble, pausa=0,
                          en_paralelo=False)
    except ri.ServidorCaido:
        pass
    igual(len(doble.llamadas), len(ri.ORDEN),
          "con un 4xx se llama UNA vez por capa, sin reintento")


def prueba_un_5xx_se_reintenta_una_vez():
    doble = Doble(por_defecto=(503, "vuelva luego"))
    try:
        ri.por_posicional("999999000001", pedir=doble, pausa=0,
                          en_paralelo=False)
    except ri.ServidorCaido:
        pass
    igual(len(doble.llamadas), len(ri.ORDEN) * 2,
          "un 5xx se reintenta una sola vez por capa")


def prueba_una_excepcion_de_red_se_reintenta_y_no_escapa():
    doble = Doble(por_defecto=TimeoutError("se agotó"))
    try:
        ri.por_posicional("999999000001", pedir=doble, pausa=0,
                          en_paralelo=False)
    except ri.ServidorCaido as ex:
        cierto("TimeoutError" in str(ex),
               "el motivo tiene que nombrar el tipo de fallo, y fue: %s" % ex)
    except Exception as ex:                                       # noqa: BLE001
        FALLOS.append("una excepción de red se escapó tal cual: %r" % ex)
    else:
        FALLOS.append("una excepción de red tiene que dar ServidorCaido")


def prueba_el_mensaje_de_caida_dice_de_quien_es_el_problema():
    mensaje = ri.mensaje_de_caida("HTTP 504")
    cierto("Registro Inmobiliario" in mensaje,
           "el mensaje tiene que nombrar a quién se le cayó el servidor")
    cierto("no es un problema de su número" in mensaje.lower(),
           "tiene que decir que no es culpa del usuario")
    cierto(ri.PORTAL_OFICIAL in mensaje,
           "tiene que ofrecer el portal oficial como salida")


# ------------------------------------------------------------ el buen vecino --

def prueba_el_agente_se_identifica_y_es_el_de_esta_herramienta():
    cierto("agrimensura.com.do" in ri.AGENTE,
           "el User-Agent tiene que decir dónde reclamar")
    cierto("Localizador" in ri.AGENTE,
           "el User-Agent tiene que nombrar ESTA herramienta y no la que se "
           "copió, o el RI no puede distinguir cuál le cuesta qué; llegó: %s"
           % ri.AGENTE)


def prueba_una_busqueda_es_una_peticion_por_capa():
    """Nada de paginar. Pedir la página siguiente es como se construye una
    descarga masiva sin darse cuenta."""
    doble = Doble()
    ri.por_posicional("999999000001", pedir=doble, pausa=0)
    igual(len(doble.llamadas), len(ri.ORDEN),
          "una búsqueda son exactamente tres peticiones, ni una más")


def prueba_hay_tope_de_resultados():
    p = ri.parametros_de("aprobadas", "999999000001")
    cierto(int(p["count"]) <= 100,
           "tiene que haber un tope pequeño: si el filtro fallara, sin tope se "
           "traería una capa entera del RI")


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
    print("[OK] %d pruebas de la capa de red, sin tocar internet." % len(pruebas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
