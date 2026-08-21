# Localizador de inmuebles por posicional

Escriba el **número posicional** de un inmueble del Registro Inmobiliario
dominicano y la herramienta dice **dónde queda**: lo sitúa sobre la foto aérea y
ofrece abrir la ruta en **Google Maps** o en **Waze**.

Gratis, sin registro, sin descargas y sin guardar nada.

- Vitrina: <https://localizador.agrimensura.com.do>
- Aplicación: <https://localizador.app.agrimensura.com.do>
- Catálogo del hub: <https://herramientas.agrimensura.com.do>

**No es el Registro Inmobiliario y no certifica nada.** Es un producto
independiente de Agrimdata & Servicios, SRL que consulta los geoservicios
públicos del RI. El portal oficial es
<https://servicios.ri.gob.do/ConsultaParcelario>.

---

## Qué hace, y qué no

| Hace | No hace |
|---|---|
| Busca un posicional en las tres capas de resultantes del RI | No busca por designación catastral ni por expediente |
| Dice municipio, provincia, superficie y fecha de inscripción | No dice quién es el propietario — el RI no publica titularidad |
| Sitúa un punto **dentro** de la parcela, sobre la foto aérea | No dice por dónde pasan los linderos |
| Da la ruta lista para Google Maps y para Waze | No entrega archivos: ni DXF, ni KML, ni shapefile |
| Avisa si la resultante está **anulada** | No comprueba cargas ni gravámenes |
| Avisa cuando el punto tuvo que moverse | No admite listas ni lotes |

Para lo de la columna derecha —designación catastral, expediente, DXF, KML,
shapefile, cuadro de coordenadas y las dos áreas contrastadas— está el
[Visor Parcelario](https://parcelario.agrimensura.com.do).

## Lo que hay que saber antes de tocar el código

**El centroide de una parcela puede caer fuera de la parcela.** Es toda la
dificultad de esta herramienta y no se ve construyendo con ejemplos urbanos.
Medido el 21/08/2026 sobre parcelas reales del RI:

```
zona urbana (Ensanche Naco) ..... 534 anillos ·  0 fuera  (0.00 %)
zona rural (Cibao, Sur, Este) ... 412 anillos ·  5 fuera  (1.21 %)
                                  peor alejamiento: 50.94 m
```

Un punto 51 m fuera manda al usuario al terreno del vecino y **no produce ningún
error**. Por eso `nucleo/centroide.py` calcula el centroide, **comprueba que cae
dentro**, y si no lo sustituye por un punto interior garantizado — y la pantalla
dice cuál de los dos está dando. Validado después sobre **2 090 parcelas reales
de seis zonas: 0 puntos fuera, 5 ajustados (0.24 %)**.

**El campo `Posicional` no está indexado en el servidor del RI.** Buscar tarda
11.1 s en la capa de aprobadas, 4.6 s en previo2017 y 0.2 s en anuladas. Las tres
se consultan **en paralelo** —15.9 s en serie contra 11.1 s a la vez— y la
pantalla avisa de la espera antes de empezar. Pedir las tres capas en una sola
petición WFS **no funciona**: el GeoServer del RI devuelve HTTP 500.

**En este repositorio no entra ningún posicional real.** Es público, y la
respuesta del RI trae identificadores de inmuebles de verdad. Los fixtures son
sintéticos, con la forma exacta del servidor y números que empiezan por nueves;
`pruebas/test_privacidad.py` rastrea la fuga y **se comprueba a sí mismo**
poniéndose delante un número con forma real.

## Cómo se corre en local

```
pip install -r requirements.txt
streamlit run app.py
```

## Las pruebas

```
python pruebas/todas.py
```

Nueve suites. Ocho corren **con el cable desenchufado**; `test_red_real.py` sale
a internet para comprobar el **contrato** del servicio del RI —que las tres capas
sigan sirviendo el campo `Posicional`— y si no hay conexión informa en vez de
ponerse roja.

| Suite | Qué cubre |
|---|---|
| `test_centroide.py` | el punto al que se manda al usuario, y que caiga dentro |
| `test_ri.py` | la capa de red, con dobles: paralelo, reintentos, caídas |
| `test_inmueble.py` | de la respuesta del RI a la ficha |
| `test_navegacion.py` | los dos enlaces, leídos **de vuelta** desde la URL |
| `test_mapa.py` | las trampas de folium, sobre el HTML generado |
| `test_app.py` | la interfaz con `AppTest` |
| `test_vitrina.py` | que la vitrina diga la verdad y no se desincronice |
| `test_privacidad.py` | lo que no puede hacer nunca |
| `test_red_real.py` | el contrato del servicio del RI, salteable |

## Cómo está organizado

```
app.py                      la pantalla, y nada más
nucleo/ri.py                lo ÚNICO que habla con el mundo exterior
nucleo/centroide.py         el punto, y el punto interior garantizado
nucleo/inmueble.py          de la respuesta del RI a la ficha
nucleo/navegacion.py        los enlaces de Google Maps y Waze
nucleo/coordenadas.py       UTM 19N <-> grados, verificado contra las CORS
nucleo/mapa.py              el mapa de folium
nucleo/marca.py             identidad y textos legales de ESTA herramienta
nucleo/contador.py          el contador público, con su clave propia
nucleo/marco.py             publica la altura hacia la vitrina
datos/generar_fixtures.py   genera los casos sintéticos de la batería
sitio/                      la vitrina, servida por su propio contenedor
```

## Despliegue

```
python ..\_publicar\desplegar_compose.py localizador
```

Las etiquetas de Traefik viven en `docker-compose.yml` y **no lleva
`acceso-pro@file`**: es gratuita, así que su aplicación tiene que contestar
**200** y no 302.

## Datos y licencias

El parcelario es del **Registro Inmobiliario de la República Dominicana** y se
consulta en vivo en sus geoservicios públicos (`atlas.ri.gob.do`); los derechos
sobre esa información son suyos. La foto aérea la sirve **Esri** y el callejero
**CARTO**, con datos de **OpenStreetMap**. Google Maps y Waze son marcas de sus
respectivos titulares y no están asociadas a este producto.
