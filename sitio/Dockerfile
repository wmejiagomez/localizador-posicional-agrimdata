# La vitrina del Localizador, servida desde el servidor propio.
#
# La zona tiene un comodín que manda a este servidor todo lo que no tenga
# registro propio, así que una vitrina nueva no necesita crear un subdominio en
# cPanel, ni una cuenta de FTP, ni una contraseña. Y de paso se queda sin el
# microcaché del alojamiento, que sirve la copia anterior durante horas cada vez
# que se publica un cambio.
#
# El contenido es una copia exacta de `../pagina_localizador.html`, y
# `pruebas/test_vitrina.py` lo exige. La copia se hace con el archivo ya editado,
# nunca al revés.
FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY assets /usr/share/nginx/html/assets

# Una página estática no necesita nada más. El `healthcheck` va aquí y no en el
# compose para que valga igual si algún día se levanta a mano.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
