# -*- coding: utf-8 -*-
"""Genera los fixtures con los que corre la batería. Nada de esto es real.

    python datos/generar_fixtures.py

**Por qué un script versionado y no un JSON escrito a mano.** Aquí se ve qué
forma tiene cada caso y de dónde sale cada número, y se audita sin leer 300
líneas de coordenadas. Es la misma regla que el protocolo del hub aplica a los
datos derivados de una fuente ajena.

**Y por qué son sintéticos.** La respuesta del GeoServer del Registro
Inmobiliario trae posicionales, expedientes y superficies de **inmuebles
reales**: guardar una respuesta cruda como fixture mete todo eso en un
repositorio que además es público. Los identificadores de aquí son inventados y
empiezan por nueves para que no puedan confundirse con uno de verdad; las
geometrías son figuras con área analítica conocida, así que la prueba puede
exigir un número exacto en vez de comparar contra sí misma.

La forma —las claves, el orden, el tipo de cada valor, el espacio duro de las
fechas— sí está copiada del servidor real, porque es lo que se está probando.
"""

import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "inmuebles_ficticios.json")

# El espacio duro que el RI mete en sus fechas —«8:52:57 a. m.»—. Se escribe con
# su escape y no literal: en un archivo fuente es indistinguible de un espacio
# normal, y el fixture dejaría de probar lo que dice probar sin que nada avise.
DURO = " "

# Un rincón de UTM 19N con coordenadas redondas, elegido a propósito lejos de
# donde caen las parcelas reales que se usaron para medir.
E0, N0 = 400000.0, 2050000.0


def anillo(puntos, cerrar=True):
    """De `[(dx, dy)]` a coordenadas absolutas, con el primer vértice repetido.

    El servidor cierra sus anillos repitiendo el primer punto al final, y el
    lector tiene que quitarlo: si el fixture no lo repitiera, esa parte del
    lector no se probaría nunca.
    """
    salida = [[E0 + dx, N0 + dy] for dx, dy in puntos]
    if cerrar:
        salida.append(list(salida[0]))
    return salida


def rasgo(ident, geometria, propiedades):
    return {
        "type": "Feature",
        "id": ident,
        "geometry": geometria,
        "geometry_name": "the_geom",
        "properties": propiedades,
    }


def coleccion(rasgos):
    return {
        "type": "FeatureCollection",
        "features": rasgos,
        "totalFeatures": len(rasgos),
        "numberMatched": len(rasgos),
        "numberReturned": len(rasgos),
        "timeStamp": "2026-08-21T12:00:00.000Z",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::32619"},
        },
    }


# --------------------------------------------------------------- los casos --

# 1. Lo normal: un solar rectangular de 20 x 10 m. Área exacta 200 m², centroide
#    exacto en (E0+10, N0+5), y dentro de la parcela.
RECTANGULO = [(0, 0), (20, 0), (20, 10), (0, 10)]

# 2. Una parcela en L. **Es el caso que justifica media herramienta.** Se
#    descompone en un rectángulo de 60x20 (área 1200, centro en 30,10) y otro de
#    20x40 (área 800, centro en 10,40): el centroide compuesto cae en (22, 22),
#    que es el hueco de la L. El punto entregado tiene que salir ajustado.
ELE = [(0, 0), (60, 0), (60, 20), (20, 20), (20, 60), (0, 60)]

# 3. Un solar con patio interior: 40x40 con un hueco de 10x10 descentrado.
CUADRADO = [(0, 0), (40, 0), (40, 40), (0, 40)]
PATIO = [(24, 24), (34, 24), (34, 34), (24, 34)]

# 4. Dos trozos separados bajo el mismo posicional: el RI publica MultiPolygon.
#    El grande manda; el pequeño está a 500 m, y un punto entre los dos caería en
#    terreno de otro.
TROZO_GRANDE = [(0, 0), (30, 0), (30, 30), (0, 30)]
TROZO_LEJANO = [(500, 500), (506, 500), (506, 506), (500, 506)]


def poligono(puntos):
    return {"type": "Polygon", "coordinates": [anillo(puntos)]}


def multi(*grupos):
    return {"type": "MultiPolygon",
            "coordinates": [[anillo(p) for p in grupo] for grupo in grupos]}


def main():
    datos = {}

    # --- una aprobada corriente, el 95 % de los casos --------------------
    datos["aprobada_simple"] = coleccion([
        rasgo("Aprobados.9000001", poligono(RECTANGULO), {
            "Posicional": "999999000001",
            "Expediente": "669999900001",
            "Operacion": "DESLINDE",
            "Provincia": "PROVINCIA DE PRUEBA",
            "Municipio": "MUNICIPIO DE PRUEBA",
            "FechaInsc": "01/01/2020 8:52:57 a.%sm." % DURO,
            "Area": 200.0,
        }),
    ])

    # --- la parcela en L: el punto tiene que ajustarse -------------------
    datos["previo2017_en_ele"] = coleccion([
        rasgo("AprobadosAnterior2017.9000002", poligono(ELE), {
            "Posicional": "999999000002",
            "Expediente": "669999900002",
            "Provincia": "PROVINCIA DE PRUEBA",
            "Municipio": "MUNICIPIO DE PRUEBA",
            # 1200 + 800 = 2000 m² exactos, y el RI lo publica con la huella de
            # un flotante de 32 bits, como hace de verdad en esta capa.
            "Area": 2000.0,
        }),
    ])

    # --- una ANULADA: tiene que salir con su advertencia -----------------
    datos["anulada"] = coleccion([
        rasgo("Anulados.9000003", poligono(RECTANGULO), {
            "Posicional": "999999000003",
            "Expediente": "669999900003",
            "Operacion": "SUBDIVISION",
            "FechaInsc": "15/06/2018 3:10:00 p.%sm." % DURO,
            "Area": 200.0,
        }),
    ])

    # --- Area = 0 con geometría de verdad --------------------------------
    # Medido en el Visor Parcelario: 1 de cada 85 parcelas aprobadas declara cero
    # teniendo superficie. Si la herramienta tratara ese cero como un número,
    # diría que el inmueble no mide nada.
    datos["area_declarada_cero"] = coleccion([
        rasgo("Aprobados.9000004", poligono(RECTANGULO), {
            "Posicional": "999999000004",
            "Expediente": "669999900004",
            "Operacion": "DESLINDE",
            "Provincia": "PROVINCIA DE PRUEBA",
            "Municipio": "PROVINCIA DE PRUEBA",   # igual que la provincia
            "FechaInsc": "20/03/2025 9:00:00 a.%sm." % DURO,
            "Area": 0,
        }),
    ])

    # --- con patio interior: el hueco se resta del área ------------------
    datos["con_patio"] = coleccion([
        rasgo("Aprobados.9000005", multi([CUADRADO, PATIO]), {
            "Posicional": "999999000005",
            "Expediente": "669999900005",
            "Operacion": "REFUNDICION",
            "Provincia": "PROVINCIA DE PRUEBA",
            "Municipio": "MUNICIPIO DE PRUEBA",
            "FechaInsc": "10/10/2021 11:30:00 a.%sm." % DURO,
            # 1600 - 100 = 1500 m² exactos.
            "Area": 1500.0,
        }),
    ])

    # --- partida en dos trozos: el punto va al mayor ---------------------
    datos["dos_trozos"] = coleccion([
        rasgo("Aprobados.9000006", multi([TROZO_GRANDE], [TROZO_LEJANO]), {
            "Posicional": "999999000006",
            "Expediente": "669999900006",
            "Operacion": "DESLINDE",
            "Provincia": "PROVINCIA DE PRUEBA",
            "Municipio": "MUNICIPIO DE PRUEBA",
            "Area": 936.0,          # 900 + 36
        }),
    ])

    # --- el mismo posicional en dos capas --------------------------------
    # El RI publica identificadores repetidos: el Visor Parcelario encontró dos
    # parcelas distintas con el mismo `Posicional`. Aquí eso significa que la
    # pantalla tiene que enseñar los dos resultados y no quedarse con el primero.
    datos["repetido_en_anuladas"] = coleccion([
        rasgo("Anulados.9000007", poligono(RECTANGULO), {
            "Posicional": "999999000001",       # el mismo que aprobada_simple
            "Expediente": "669999900007",
            "Operacion": "DESLINDE",
            "FechaInsc": "05/05/2015 10:00:00 a.%sm." % DURO,
            "Area": 200.0,
        }),
    ])

    # --- geometría rota: no cancela el resultado, se avisa ---------------
    datos["geometria_rota"] = coleccion([
        rasgo("Aprobados.9000008",
              {"type": "Point", "coordinates": [E0, N0]}, {
                  "Posicional": "999999000008",
                  "Expediente": "669999900008",
                  "Area": 100.0,
              }),
    ])

    # --- fuera del país: el dato oficial mal proyectado ------------------
    # No es un error de tecleo del usuario —el punto lo devuelve el RI—, y es lo
    # único que impediría que el enlace de Waze diera por bueno un punto en el
    # Atlántico.
    datos["fuera_del_pais"] = coleccion([
        rasgo("Aprobados.9000009",
              {"type": "Polygon",
               "coordinates": [[[100000.0, 1000000.0], [100020.0, 1000000.0],
                                [100020.0, 1000010.0], [100000.0, 1000010.0],
                                [100000.0, 1000000.0]]]}, {
                  "Posicional": "999999000009",
                  "Expediente": "669999900009",
                  "Area": 200.0,
              }),
    ])

    # --- nada: el posicional no existe -----------------------------------
    # Es el segundo resultado más frecuente después del acierto, porque la gente
    # teclea mal doce dígitos. Un 200 con cero rasgos es una respuesta legítima
    # del servidor y NO un fallo.
    datos["vacio"] = coleccion([])

    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("Escritos %d casos en %s" % (len(datos), DESTINO))


if __name__ == "__main__":
    main()
