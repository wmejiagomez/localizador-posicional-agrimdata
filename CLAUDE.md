# Reglas de esta sección

Estas instrucciones se cargan solas en cada sesión que trabaje en esta carpeta.
Son obligatorias.

## Qué es esto

El **Localizador de inmuebles por posicional**: se escribe un número posicional
del Registro Inmobiliario y la herramienta dice dónde queda el inmueble, lo pinta
sobre la foto aérea y entrega la ruta para Google Maps y para Waze.

Los datos se consultan **en vivo** al GeoServer público del RI,
`atlas.ri.gob.do`. Es la tercera herramienta del hub que depende de un tercero en
vivo, después del Extractor de calles y del Visor Parcelario.

**Es gratuita**, y eso no es un descuido: su público no es el de la suscripción.
El razonamiento completo está en `PLIEGO.md`.

## Antes de tocar nada

1. **Lea [PLIEGO.md](PLIEGO.md).** Trae las fases 0 y 1 hechas, con las
   mediciones que las sustentan. No vuelva a decidir lo ya decidido; si algo le
   parece mal, corríjalo con su motivo, no lo ignore.
2. El protocolo del hub manda en todo lo demás: `..\PROTOCOLO.md`.
3. El [Visor Parcelario](../Visor%20Parcelario%20-%20Web/PROTOCOLO.md) consulta el
   mismo servicio y tiene protocolo propio con lo que puede salir mal con el RI.
   Léalo antes de tocar `nucleo/ri.py`.

## Las siete que no se negocian

1. **El punto tiene que caer DENTRO de la parcela.** Es la herramienta entera. El
   centroide de una parcela en L o en U cae fuera de ella: medido, 5 de 412
   parcelas rurales reales, la peor a 50.94 m. Un punto fuera manda al usuario al
   terreno del vecino y **no da ningún error** — el mapa se ve perfecto y Waze
   abre. Por eso se calcula el centroide, **se comprueba que está dentro** y si no
   se sustituye por un punto interior. Nunca se entrega el centroide sin
   comprobar.

2. **Y se dice cuál de los dos se está dando.** Quien va a conducir hasta allí
   tiene derecho a saber si el punto es el centro de su terreno o un punto
   interior escogido porque el centro caía fuera. Decir «se ajustó» siempre sería
   mentir en el 99.8 % de los casos; no decirlo nunca escondería justo el caso en
   que el punto no es el centro.

3. **Esta herramienta no es el Registro Inmobiliario y tiene que decirlo**, en la
   pantalla y en la vitrina. Y **no certifica nada**: quien llega puede estar a
   punto de comprar un terreno. La pantalla dice explícitamente que no se compre
   ni se firme nada con ella.

4. **El punto es para llegar, no para medir.** No son los linderos. Esa frase no
   puede desaparecer de la pantalla: sin ella, alguien levanta una verja guiándose
   por un mapa.

5. **No entrega archivos. Nunca.** Ni DXF, ni KML, ni shapefile, ni CSV. Es la
   línea que separa esta herramienta del Visor Parcelario, que es de pago. El día
   que alguien añada `ezdxf` a `requirements.txt` o un `st.download_button` a
   `app.py`, lo que está cambiando no es una dependencia: es qué producto es esto
   y a quién le quita el pan. `test_privacidad.py` lo comprueba sobre el código.

6. **Se consulta como consultaría una persona.** Una búsqueda por acción pedida a
   propósito, `User-Agent` honesto que nombre a ESTA herramienta, y **nunca un
   barrido**: no se recorren números, no se resuelven listas y no se cachea el
   parcelario. El portal oficial pone un reCAPTCHA delante de cada consulta y este
   servicio no lo tiene; el límite se lo pone la herramienta a sí misma.

7. **En el código fuente nunca van datos reales — ni un posicional.** El
   repositorio es **público**, y la respuesta del servidor trae posicionales,
   expedientes y superficies de inmuebles reales. Los fixtures son **sintéticos**:
   la forma exacta del servidor con identificadores inventados que empiezan por
   nueves. `test_privacidad.py` rastrea la fuga en todo el repositorio y se
   comprueba a sí mismo poniéndose delante un número con forma real — **cazó dos
   en su primera ejecución**, uno en `test_ri.py` y otro en el propio archivo.

## Lo que ya se midió, para no volver a medirlo

Todo el 21/08/2026, contra el servidor real. Está en `PLIEGO.md` con su contexto.

```
posicional ................. 12 dígitos, solo dígitos (2 087 de 2 087)
campo Posicional ........... xsd:string en las tres capas -> filtro con comillas
buscar en aprobadas ........ 11.1 - 11.5 s   (730 084 registros, sin índice)
buscar en previo2017 .......  4.6 -  7.7 s
buscar en anuladas .........  0.2 -  0.4 s
las tres en serie .......... 15.9 s      en paralelo: 11.1 s
las tres en UNA petición ... HTTP 500 — no se puede, está probado
consulta espacial por bbox .  0.06 - 0.22 s
centroide fuera, urbano .... 0 de 534
centroide fuera, rural ..... 5 de 412 (1.21 %), peor 50.94 m
validación del algoritmo ... 2 090 parcelas reales · 0 fuera · 0.016 ms cada una
alto incrustada a 1280 px .. partida 975 · con resultado 1891
alto incrustada a 375 px ... partida 1452
```

## Y la que vale para todo el hub

**Verificar es demostrar que si estuviera roto se vería.** Si la respuesta a «¿qué
habría visto si esto fallara?» es «lo mismo», la prueba no vale.

Y **mirar la pantalla no es un trámite de cierre**: con la batería entera en
verde, el navegador enseñó un `AttributeError`, el aviso del RI repetido palabra
por palabra, los botones de ir con estilo secundario y «1 inmuebles localizados».
Ninguna prueba veía ninguno de los cuatro.

## Detalles del entorno

- Los comandos se dan con **ruta completa**: `C:\Python314\python.exe` y la ruta
  del script entre comillas. Werner los copia y los pega en **PowerShell 5.1**,
  donde `&&` no existe: para encadenar, `;`.
- **Reinicie el servidor de Streamlit antes de creerse una medida.** Reejecuta el
  guion en cada cambio pero se queda con el módulo ya importado: un símbolo nuevo
  en `nucleo/marca.py` da `AttributeError` en pantalla hasta que se reinicia. Pasó
  el 21/08/2026.
- El despliegue se hace con `..\_publicar\desplegar_compose.py localizador`. **Es
  gratuita**: la aplicación tiene que contestar **200**, no 302.
- Werner maneja el panel del hosting y el de Coolify. Claude no inicia sesión ni
  escribe contraseñas.

## Al terminar

Actualice el pliego si aprendió algo que no estaba escrito, y deje el estado en la
memoria del proyecto. La próxima sesión empieza de cero: lo que no quede escrito,
se pierde.
