---
name: run-localizador-posicional
description: Arranca «Localizador Posicional - Web» (herramienta Streamlit del hub de agrimensura.com.do) en local, la abre en Chromium, la maneja y captura pantalla; nunca contra produccion. Usar al pedir ejecutar, arrancar, lanzar, probar, verificar, capturar o abrir Localizador Posicional - Web.
---

# Ejecutar y manejar «Localizador Posicional - Web» en local

Herramienta Streamlit (`app.py`) que en produccion corre en un contenedor detras de Traefik. Aqui se lanza sola en `127.0.0.1:8648`
y se maneja con Playwright desde `driver.py`. Las rutas son relativas a la carpeta de la herramienta (la del `app.py`).

## Requisitos (Windows, los de esta maquina)
`C:/Python314/python.exe` con `streamlit` y `playwright` (`python -m playwright install chromium` una vez). Las dependencias de la
herramienta salen de su `requirements.txt`.

## Ejecutar (camino del agente)
```
C:/Python314/python.exe .claude/skills/run-localizador-posicional/driver.py smoke
```
Arranca, espera a que pinte, comprueba que no hay excepciones, captura y apaga. Deja `C:/dev/salidas/run/localizador-posicional-smoke.png`;
mirala: si sale en blanco o con un cuadro rojo, no esta bien. Sale con codigo 0 si todo va bien y escribe una linea JSON.

Para conocer lo que se puede manejar:
```
C:/Python314/python.exe .claude/skills/run-localizador-posicional/driver.py controles
```
Medido el 29/09/2026 — campos: «Número posicional». Botones: «Deploy», «Buscar el inmueble». Opciones: ninguna.

Para manejarla, un `pasos.json` (ver la cabecera de `driver.py`): `{"llenar": "Etiqueta", "valor": "..."}`, `{"clic": "Texto"}`,
`{"espera_texto": "..."}`, `{"sin_texto": "..."}`, `{"captura": "nombre"}`; se lanza con `driver.py pasos pasos.json`.

## Pruebas
```
C:/Python314/python.exe pruebas/todas.py
```
La bateria completa del repo; el 29/09/2026 dio verde en las 40 herramientas.

## Trampas medidas
- **Nunca contra produccion.** El driver escucha solo en 127.0.0.1 y pone `AGRIM_SIN_CONTADOR=1`: sin eso cada prueba suma al contador
  publico de la vitrina, que usa la misma clave que produccion.
- **`get_by_label` a secas falla en Streamlit:** resuelve al boton de ayuda (`?`) y no al campo. El driver usa el `aria-label` del `<input>`.
- **La primera carga puede mostrar «Failed to fetch dynamically imported module»** (visto tambien en produccion); el driver recarga una vez.
- **Puerto ocupado:** `driver.py down` (o el proceso quedo vivo: `taskkill /F /T /PID <pid de C:/dev/salidas/run/localizador-posicional.pid>`).
- **Lanzalo desde la carpeta del repo real** (`C:/Proyectos Agrimensura.com.do/...`), no desde la copia de Drive, que no es un repositorio.
- **Estas recetas no viajan al servidor:** `.gitattributes` lleva `.claude export-ignore` y `.gitattributes export-ignore`;
  `git archive HEAD | tar -t | grep .claude` debe dar 0 lineas.

## Si falla
- `no encuentro app.py`: no estas en la carpeta de la herramienta.
- `streamlit no arranco`: mira `C:/dev/salidas/run/localizador-posicional.log` (casi siempre una dependencia sin instalar).
