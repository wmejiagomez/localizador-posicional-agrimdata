# -*- coding: utf-8 -*-
"""Contador público de búsquedas resueltas.

Cuenta cada búsqueda que se completó de verdad —se preguntó al Registro
Inmobiliario y contestó—, así el número refleja uso real y no solo visitas a la
página. No hay servidor propio: se apoya en el mismo servicio gratuito que usan
las demás herramientas del hub (countapi.mileshilliard.com), con una clave propia
para no mezclar los conteos.

**La clave es distinta de la de las demás, y eso no es un detalle.** Este módulo
se copió del Visor Parcelario con su clave dentro; dejarla habría sumado las
búsquedas de esta herramienta al contador de consultas de aquélla, y los dos
números habrían quedado mal para siempre sin que nada avisara. Es el registro
número 6 de las nueve listas del protocolo del hub, y uno de los dos que fallan
apuntando al contador ajeno en vez de faltar.

Ningún número posicional viaja hacia este servicio: solo se le pide «sumá uno» o
«decime cuánto llevás». Es un conteo, no un registro — coherente con que esta
herramienta no guarde nada de lo que se consulta.
"""

import threading

import requests

# El sufijo de versión permite empezar de cero si algún día hiciera falta: basta
# con cambiarlo a -v2.
CLAVE = "agrimensura-localizador-busquedas-v1"
BASE = "https://countapi.mileshilliard.com/api/v1"
TIMEOUT = 5

# Aviso sobre este servicio: la clave es pública y su endpoint `/set` permite
# fijar cualquier valor a quien la conozca. La consecuencia es cosmética —un
# número de vitrina equivocado—, nunca una fuga: por aquí no viaja ningún dato
# del usuario. Si algún día el número apareciera manipulado, se reinicia con
# /set?value=N y se cambia el sufijo de la clave.

# El servicio gratuito solo sabe sumar de a uno: no existe un «sumar N» atómico
# en su API. Leer el total y reescribirlo con N sumado tiene una condición de
# carrera real, así que se prefiere golpearlo N veces seguidas, en un hilo aparte
# para no demorarle la respuesta al usuario.
MAX_FALLOS_SEGUIDOS = 3


def _sumar_en_hilo(cantidad):
    fallos_seguidos = 0
    for _ in range(cantidad):
        try:
            requests.get(f"{BASE}/hit/{CLAVE}", timeout=TIMEOUT)
            fallos_seguidos = 0
        except requests.RequestException:
            fallos_seguidos += 1
            if fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
                break  # el servicio no responde; insistir no cambia eso


def sumar(cantidad):
    """Suma `cantidad` al contador. No bloquea: corre en segundo plano.

    Nunca lanza — un fallo aquí no puede tumbar una búsqueda real. Se llama
    normalmente con 1: una búsqueda respondida.

    **El argumento es obligatorio a propósito.** En División de parcelas el doble
    de las pruebas era `lambda n=1: None`, más permisivo que la función real, y
    la aplicación llamaba `sumar()` sin argumento: la batería entera pasaba y el
    usuario veía la pantalla roja. Un doble así no prueba, tapa.
    """
    if cantidad <= 0:
        return
    threading.Thread(target=_sumar_en_hilo, args=(cantidad,),
                     daemon=True).start()


def leer():
    """Lee el total actual. Devuelve None si el servicio no responde.

    Sin caché propia: quien llama decide cada cuánto refrescar (en la app,
    `st.cache_data` con TTL; evita golpear el servicio en cada interacción, ya que
    Streamlit vuelve a correr el script entero en cada una).
    """
    try:
        r = requests.get(f"{BASE}/get/{CLAVE}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("value")
    except (requests.RequestException, ValueError):
        return None
