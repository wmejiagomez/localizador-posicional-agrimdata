# -*- coding: utf-8 -*-
"""De lo que devuelve el servidor del RI a la ficha que se enseña.

Este módulo no toca la red: recibe el `FeatureCollection` que trajo `ri.py` y lo
convierte en la ficha del inmueble, con su punto ya calculado. Así todo lo de
aquí se prueba con el cable desenchufado.

**Lo que sale de aquí es un punto y cuatro datos**, no una parcela para el CAD.
La geometría se conserva únicamente para dibujar el contorno en el mapa y para
calcular el punto; no se entrega, y no debe entregarse — es la línea que separa
esta herramienta del Visor Parcelario, y está razonada en `PLIEGO.md`.

**Las dos áreas se enseñan igual que allí**, y por el mismo motivo medido: el RI
publica un `Area` que no siempre coincide con la de la geometría que él mismo
entrega, y una de cada 85 parcelas declara cero teniendo superficie. Aquí no es
el asunto de la pantalla —quien viene a esto quiere llegar al terreno, no
depositar— así que la declarada manda en la ficha y la medida se enseña al lado
cuando difieren de verdad.
"""

from . import centroide, coordenadas, ri

# El espacio duro (U+00A0) que el RI mete en sus fechas —«8:52:57 a. m.»—. Se
# declara con su punto de código y no escrito literal: en un archivo fuente es
# indistinguible de un espacio normal, y el día que alguien reindente el módulo
# desaparece sin que nada avise.
ESPACIO_DURO = " "

# Cómo se rotula cada campo del RI en la ficha. Los nombres que publica el
# servicio son de base de datos; los que ve el usuario tienen que ser palabras.
ROTULOS = {
    "Posicional": "Número posicional",
    "Expediente": "Expediente",
    "Provincia": "Provincia",
    "Municipio": "Municipio",
    "Operacion": "Operación",
    "FechaInsc": "Inscrito el",
}

# Los que no se enseñan en la ficha porque ya tienen su sitio propio en la
# pantalla, o porque no le dicen nada a quien no es agrimensor.
OCULTOS = ("Area",)


class ErrorInmueble(ValueError):
    pass


def _texto(valor):
    """Un atributo listo para enseñar. `None` y el vacío se ven igual."""
    if valor is None:
        return ""
    return str(valor).replace(ESPACIO_DURO, " ").strip()


def _anillos_de(geo):
    """Geometría de GeoJSON -> `[(puntos, es_hueco)]`, sin el vértice repetido.

    Admite `Polygon` y `MultiPolygon`, que es lo único que sirve el RI. La tercera
    coordenada, si viene, se descarta: el parcelario es plano.
    """
    tipo = (geo or {}).get("type")
    if tipo == "Polygon":
        poligonos = [geo["coordinates"]]
    elif tipo == "MultiPolygon":
        poligonos = geo["coordinates"]
    else:
        raise ErrorInmueble(
            "El Registro Inmobiliario devolvió una geometría de tipo «%s», y "
            "aquí sólo se esperan polígonos." % tipo)

    salida = []
    for poligono in poligonos:
        for indice, anillo in enumerate(poligono):
            puntos = [(float(p[0]), float(p[1])) for p in anillo]
            if len(puntos) > 1 and puntos[0] == puntos[-1]:
                puntos = puntos[:-1]
            if len(puntos) >= 3:
                salida.append((puntos, indice > 0))
    if not salida:
        raise ErrorInmueble(
            "La geometría llegó sin ningún contorno utilizable.")
    return salida


def ficha(capa, rasgo):
    """Un `Feature` del RI -> la ficha del inmueble, con el punto ya resuelto.

    El punto se calcula **aquí y una sola vez**: el mapa, los dos enlaces de
    navegación y las coordenadas que se enseñan salen todos del mismo par, así
    que no pueden discrepar entre sí. Ese fallo —el mapa señalando un sitio y
    Waze llevando a otro— sería invisible en cualquier prueba de contenido.
    """
    definicion = ri.CAPAS[capa]
    propiedades = rasgo.get("properties") or {}
    anillos = _anillos_de(rasgo.get("geometry"))

    punto, ajustado = centroide.punto_para_ir(anillos)
    este, norte = punto
    lon, lat = coordenadas.utm_a_geo(este, norte, ri.ZONA)

    crudo = propiedades.get(ri.CAMPO_AREA)
    try:
        declarada = float(crudo)
    except (TypeError, ValueError):
        declarada = None
    # **El cero del RI no es un área, es un hueco.** Medido en el Visor
    # Parcelario: 1 de 85 parcelas aprobadas declara `Area = 0` con geometría de
    # 124.53 m². Tratarlo como número diría que el inmueble no mide nada.
    if declarada is not None and declarada <= 0:
        declarada = None

    datos = []
    for campo in definicion["campos"]:
        if campo in OCULTOS:
            continue
        valor = _texto(propiedades.get(campo))
        if valor:
            datos.append((ROTULOS.get(campo, campo), valor))

    return {
        "capa": capa,
        "etiqueta": definicion["etiqueta"],
        "nota": definicion["nota"],
        "color": definicion["color"],
        "anulada": capa == "anuladas",
        "posicional": _texto(propiedades.get(ri.CAMPO_POSICIONAL)),
        "expediente": _texto(propiedades.get("Expediente")),
        "municipio": _texto(propiedades.get("Municipio")),
        "provincia": _texto(propiedades.get("Provincia")),
        "datos": datos,
        "anillos": anillos,
        "area_declarada": declarada,
        "area_medida": centroide.superficie(anillos),
        "vertices": sum(len(p) for p, _ in anillos),
        "este": este,
        "norte": norte,
        "lat": lat,
        "lon": lon,
        "punto_ajustado": ajustado,
        "aviso_pais": coordenadas.fuera_del_pais(lat, lon),
    }


def leer(documentos):
    """`{capa: FeatureCollection}` -> `(fichas, avisos)`.

    Las fichas salen en el orden de `ri.ORDEN`: aprobadas primero, anuladas al
    final. Un inmueble con la geometría rota **no cancela el resultado**: se dice
    cuál y por qué, y los demás siguen. Aquí eso importa más que en otras
    herramientas porque el dato lo pone un tercero y no se puede arreglar.
    """
    fichas, avisos = [], []
    for capa in ri.ORDEN:
        documento = documentos.get(capa)
        if not documento:
            continue
        for indice, rasgo in enumerate(documento.get("features") or [], 1):
            try:
                fichas.append(ficha(capa, rasgo))
            except (ErrorInmueble, centroide.ErrorCentroide,
                    ValueError, TypeError, KeyError) as ex:
                avisos.append(
                    "«%s»: el resultado %d llegó con la geometría rota y se "
                    "dejó fuera (%s)." % (ri.CAPAS[capa]["etiqueta"], indice, ex))
    return fichas, avisos


# Diferencia mínima entre las dos áreas para que valga la pena decirla. Las áreas
# se enseñan con dos decimales, así que por debajo de medio centímetro cuadrado
# se estaría pidiendo al usuario que mire dos números idénticos y busque la
# diferencia. No se usa aquí la tolerancia derivada del Visor Parcelario —que
# cuenta la cuantización de la coordenada y la precisión del flotante de 32 bits—
# porque esta pantalla no es para depositar: para contrastar áreas al milímetro
# está aquella herramienta, y esta enlaza a ella.
DIFERENCIA_VISIBLE = 0.005


def diferencia_de_areas(f):
    """Cuánto se separan las dos áreas, o `None` si no hay nada que comparar."""
    if f["area_declarada"] is None:
        return None
    diferencia = abs(f["area_medida"] - f["area_declarada"])
    return diferencia if diferencia > DIFERENCIA_VISIBLE else None


def donde(f):
    """«Santo Domingo Este, Santo Domingo» — o lo que haya, o nada.

    Es la primera línea que lee alguien que solo tiene un número: antes de ver el
    mapa ya sabe si su inmueble está donde creía. Cuando el municipio y la
    provincia se llaman igual —Santiago, Azua, Barahona— se dice una sola vez.
    """
    municipio, provincia = f["municipio"], f["provincia"]
    if municipio and provincia and municipio.upper() != provincia.upper():
        return "%s, %s" % (municipio.title(), provincia.title())
    return (municipio or provincia or "").title()
