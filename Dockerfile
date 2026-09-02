# Imagen para servir la herramienta en el servidor propio.
#
# Python 3.12 y no 3.14: las ruedas precompiladas de las dependencias pesadas del
# hub —pyproj, shapely, PyMuPDF— tardan en publicarse para cada versión nueva, y
# sin rueda el despliegue se pone a compilar C durante minutos, o falla. 3.12 las
# tiene todas.
FROM python:3.14-slim

# Sin esto, Python escribe .pyc dentro del contenedor y no vacía la salida hasta
# cerrar, con lo que los registros aparecen en blanco justo cuando hacen falta
# para saber por qué no arranca.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Las dependencias van en su propia capa, antes del código: así un cambio en
# `app.py` no obliga a reinstalar todo el árbol de paquetes en cada despliegue.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Coolify comprueba este endpoint para saber si el contenedor está sano. Es el
# que trae Streamlit de serie.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health',timeout=4).status==200 else 1)"

# `address=0.0.0.0` es obligatorio dentro de un contenedor: con el 127.0.0.1 que
# Streamlit usa por defecto, el proceso arranca bien y nadie puede alcanzarlo
# desde fuera, que es el fallo más difícil de ver de esta lista.
#
# `enableCORS=false` no es un descuido de seguridad: es obligatorio para que la
# herramienta funcione incrustada. La vitrina vive en
# `localizador.agrimensura.com.do` y la aplicación en
# `localizador.app.agrimensura.com.do` — dominios distintos. Con la comprobación
# de origen activada, Streamlit devuelve 403 al WebSocket y el iframe se queda en
# blanco indefinidamente, sin ningún mensaje.
#
# Lo que se pierde: la app acepta conexiones desde cualquier página que la
# incruste. Aquí eso no abre nada, porque no hay sesión, ni cuenta, ni dato
# guardado que robar — la búsqueda se procesa en memoria y se descarta, y los
# datos que enseña son públicos.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false"]
