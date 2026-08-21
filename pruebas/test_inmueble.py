# -*- coding: utf-8 -*-
"""De la respuesta del RI a la ficha, sobre fixtures sintéticos.

Todos los casos vienen de `datos/inmuebles_ficticios.json`, que genera un script
versionado. Los identificadores son inventados y las geometrías son figuras con
área analítica conocida, así que aquí se puede exigir un número exacto en vez de
comparar el resultado consigo mismo.

**Ni un dato real del Registro Inmobiliario entra en este repositorio.** Su
respuesta trae posicionales y expedientes de inmuebles de verdad, y el repositorio
es público.
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

from nucleo import centroide, inmueble, ri                         # noqa: E402

FALLOS = []

with open(os.path.join(os.path.dirname(AQUI), "datos",
                       "inmuebles_ficticios.json"), encoding="utf-8") as f:
    CASOS = json.load(f)


def cierto(condicion, que):
    if not condicion:
        FALLOS.append(que)


def igual(a, b, que):
    if a != b:
        FALLOS.append("%s: esperaba %r, llegó %r" % (que, b, a))


def cerca(a, b, tolerancia, que):
    if abs(a - b) > tolerancia:
        FALLOS.append("%s: esperaba %.6f, llegó %.6f" % (que, b, a))


def una(caso, capa="aprobadas"):
    """La primera ficha de un caso del fixture."""
    fichas, avisos = inmueble.leer({capa: CASOS[caso]})
    return (fichas[0] if fichas else None), avisos


# ------------------------------------------------------------ lo corriente --

def prueba_un_solar_rectangular():
    f, avisos = una("aprobada_simple")
    igual(avisos, [], "un caso limpio no genera avisos")
    igual(f["posicional"], "999999000001", "el posicional")
    igual(f["expediente"], "669999900001", "el expediente")
    cerca(f["area_declarada"], 200.0, 1e-9, "el área declarada")
    cerca(f["area_medida"], 200.0, 1e-6, "el área medida, 20 x 10")
    igual(f["vertices"], 4,
          "el vértice repetido del cierre se quita al leer")
    cierto(not f["anulada"], "una aprobada no está anulada")


def prueba_el_punto_de_un_rectangulo_es_su_centro():
    f, _ = una("aprobada_simple")
    cerca(f["este"], 400010.0, 1e-6, "el este del centro")
    cerca(f["norte"], 2050005.0, 1e-6, "el norte del centro")
    cierto(not f["punto_ajustado"],
           "en un rectángulo el punto NO se ajusta, y decir lo contrario sería "
           "mentir en el 98.8 % de los casos")


def prueba_el_punto_se_convierte_a_grados_dentro_del_pais():
    f, _ = una("aprobada_simple")
    cierto(17.0 < f["lat"] < 20.0, "la latitud cae en el país: %.5f" % f["lat"])
    cierto(-72.5 < f["lon"] < -68.0,
           "la longitud cae en el país y es NEGATIVA: %.5f" % f["lon"])
    igual(f["aviso_pais"], None, "un punto en el país no lleva aviso")


def prueba_la_fecha_pierde_el_espacio_duro():
    """El RI mete U+00A0 en sus fechas. En una tabla se ve como un carácter raro
    y parece un fallo de la herramienta."""
    f, _ = una("aprobada_simple")
    fechas = [v for r, v in f["datos"] if r == "Inscrito el"]
    cierto(fechas, "la fecha de inscripción tiene que estar en la ficha")
    if fechas:
        cierto(" " not in fechas[0],
               "el espacio duro tiene que haberse cambiado por uno normal, y "
               "llegó %r" % fechas[0])


def prueba_los_rotulos_son_palabras_y_no_nombres_de_columna():
    """Esta pantalla la lee alguien que no es agrimensor."""
    f, _ = una("aprobada_simple")
    rotulos = [r for r, _ in f["datos"]]
    cierto("Número posicional" in rotulos,
           "«Posicional» a secas es un nombre de columna; llegó %s" % rotulos)
    cierto("Posicional" not in rotulos,
           "el nombre crudo de la columna no puede llegar a la pantalla")


def prueba_el_area_no_se_repite_en_la_ficha():
    """Tiene su renglón propio en la pantalla; en `datos` sobraría."""
    f, _ = una("aprobada_simple")
    igual([r for r, _ in f["datos"] if r.lower().startswith("area")], [],
          "el área no va dentro de «datos»")


# --------------------------------------------------- la L: el caso que importa --

def prueba_la_parcela_en_ele_ajusta_el_punto():
    f, _ = una("previo2017_en_ele", capa="previo2017")
    cerca(f["area_medida"], 2000.0, 1e-6, "el área de la L: 1200 + 800")
    cierto(f["punto_ajustado"],
           "el centroide de una L cae fuera de ella, así que el punto tiene "
           "que salir ajustado")
    cierto(centroide.dentro((f["este"], f["norte"]), f["anillos"]),
           "y el punto entregado tiene que estar DENTRO de la parcela; salió "
           "en E %.3f N %.3f" % (f["este"], f["norte"]))


def prueba_el_centroide_crudo_de_la_ele_cae_fuera():
    """La premisa. Si el fixture no ejercita el ajuste, la prueba de arriba no
    prueba nada."""
    f, _ = una("previo2017_en_ele", capa="previo2017")
    crudo = centroide.centroide_de_area(f["anillos"])
    cierto(not centroide.dentro(crudo, f["anillos"]),
           "el fixture de la L tiene que tener el centroide fuera; si cae "
           "dentro, la figura está mal construida")


# ------------------------------------------------------------- los avisados --

def prueba_una_anulada_se_marca_y_no_se_esconde():
    f, _ = una("anulada", capa="anuladas")
    cierto(f["anulada"], "la capa de anuladas marca la ficha")
    cierto(f["nota"],
           "una anulada tiene que traer su advertencia escrita: es lo que no "
           "se puede descubrir tarde")
    cierto("anulada" in f["nota"].lower(),
           "la advertencia tiene que decir la palabra «anulada»")


def prueba_el_area_cero_del_ri_no_es_un_area():
    """Medido en el Visor Parcelario: 1 de cada 85 aprobadas declara cero
    teniendo superficie. Tratarlo como número diría que no mide nada."""
    f, _ = una("area_declarada_cero")
    igual(f["area_declarada"], None,
          "un Area = 0 del RI se lee como «no la declara», no como cero")
    cerca(f["area_medida"], 200.0, 1e-6,
          "y la geometría sí mide: eso es justo lo que hay que enseñar")


def prueba_el_patio_interior_se_resta():
    f, _ = una("con_patio")
    cerca(f["area_medida"], 1500.0, 1e-6,
          "40x40 menos un patio de 10x10 son 1500 m², no 1700")
    igual(inmueble.diferencia_de_areas(f), None,
          "declarada y medida coinciden, así que no hay nada que avisar")


def prueba_dos_trozos_mandan_al_mayor():
    f, _ = una("dos_trozos")
    grande = [(p, h) for p, h in f["anillos"] if centroide.area(p) > 100]
    cierto(centroide.dentro((f["este"], f["norte"]), grande),
           "con la parcela partida en dos, el punto va al trozo GRANDE y no "
           "al medio de los dos, que es terreno de otro; salió en E %.2f N %.2f"
           % (f["este"], f["norte"]))


def prueba_fuera_del_pais_lleva_su_aviso():
    """El punto lo devuelve el RI, no lo escribe el usuario: que caiga fuera
    significa que el dato oficial está mal proyectado."""
    f, _ = una("fuera_del_pais")
    cierto(f["aviso_pais"],
           "un punto fuera del país tiene que traer aviso, y es lo único que "
           "impide que el enlace de Waze lo dé por bueno")


def prueba_una_geometria_rota_no_cancela_el_resultado():
    fichas, avisos = inmueble.leer({"aprobadas": CASOS["geometria_rota"]})
    igual(fichas, [], "un Point no produce ficha")
    cierto(avisos, "pero sí tiene que producir un aviso que diga cuál falló")


def prueba_lo_vacio_es_vacio_y_no_un_error():
    fichas, avisos = inmueble.leer({"aprobadas": CASOS["vacio"]})
    igual(fichas, [], "cero resultados es una lista vacía")
    igual(avisos, [], "y no es ningún aviso: «no existe» es una respuesta")


# ------------------------------------------------------------- varios a la vez --

def prueba_el_orden_pone_la_anulada_al_final():
    """El RI publica el mismo posicional en más de una capa. La vigente primero."""
    fichas, _ = inmueble.leer({
        "anuladas": CASOS["repetido_en_anuladas"],
        "aprobadas": CASOS["aprobada_simple"],
    })
    igual([f["capa"] for f in fichas], ["aprobadas", "anuladas"],
          "la aprobada va primero y la anulada al final, sea cual sea el orden "
          "en que contestaron las capas")


def prueba_se_leen_todas_las_capas_que_contestaron():
    fichas, _ = inmueble.leer({
        "aprobadas": CASOS["aprobada_simple"],
        "previo2017": CASOS["previo2017_en_ele"],
        "anuladas": CASOS["anulada"],
    })
    igual(len(fichas), 3, "los tres resultados tienen que estar")


def prueba_una_capa_que_falta_no_estorba():
    """`por_posicional` devuelve solo las capas que contestaron."""
    fichas, avisos = inmueble.leer({"previo2017": CASOS["previo2017_en_ele"]})
    igual(len(fichas), 1, "con una sola capa en la respuesta se lee esa")
    igual(avisos, [], "y no se avisa de las que no vinieron")


# --------------------------------------------------------------- lo que se ve --

def prueba_donde_junta_municipio_y_provincia():
    f, _ = una("aprobada_simple")
    igual(inmueble.donde(f), "Municipio De Prueba, Provincia De Prueba",
          "se enseña municipio y provincia")


def prueba_donde_no_repite_cuando_se_llaman_igual():
    """Santiago, Azua, Barahona: el municipio y la provincia coinciden."""
    f, _ = una("area_declarada_cero")
    igual(inmueble.donde(f), "Provincia De Prueba",
          "cuando municipio y provincia son el mismo nombre, se dice una vez")


def prueba_la_diferencia_de_areas_solo_sale_si_se_ve():
    """Pedirle a alguien que mire dos números idénticos y busque la diferencia
    no es un aviso, es ruido."""
    f, _ = una("aprobada_simple")
    f["area_medida"] = f["area_declarada"] + 0.001
    igual(inmueble.diferencia_de_areas(f), None,
          "una milésima de metro cuadrado no se enseña: redondea a 0.00")
    f["area_medida"] = f["area_declarada"] + 0.25
    cierto(inmueble.diferencia_de_areas(f) is not None,
           "un cuarto de metro cuadrado sí se enseña")


def prueba_no_hay_geometria_en_lo_que_se_entrega():
    """La línea con el Visor Parcelario.

    La ficha conserva `anillos` para dibujar el mapa, y eso está bien. Lo que no
    puede aparecer nunca es una función que los convierta en un archivo: el día
    que este módulo sepa escribir un DXF, esta herramienta dejó de ser un
    localizador.
    """
    prohibidas = [n for n in dir(inmueble)
                  if any(f in n.lower()
                         for f in ("dxf", "kml", "shp", "geojson", "csv",
                                   "descarga", "exportar"))]
    igual(prohibidas, [],
          "«inmueble.py» no puede tener nada que genere archivos; apareció: %s"
          % prohibidas)


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
    print("[OK] %d pruebas de la lectura de la respuesta del RI." % len(pruebas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
