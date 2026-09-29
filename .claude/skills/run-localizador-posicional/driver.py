#!/usr/bin/env python
"""Driver de la herramienta Streamlit «Localizador Posicional - Web»: la arranca EN LOCAL, la abre en Chromium, la maneja y la apaga.

NUNCA contra produccion: escucha solo en 127.0.0.1 y pone AGRIM_SIN_CONTADOR=1 (sin eso cada prueba sube el contador
publico de visitas de la vitrina, que usa la misma clave que produccion).

Se lanza desde la carpeta de la herramienta (la del app.py):
    python .claude/skills/run-localizador-posicional/driver.py smoke              arranca, comprueba que pinta y sin excepciones, captura, apaga
    python .claude/skills/run-localizador-posicional/driver.py pasos pasos.json   arranca, ejecuta los pasos y apaga
    python .claude/skills/run-localizador-posicional/driver.py controles          arranca y lista los campos, botones y opciones que hay en pantalla
    python .claude/skills/run-localizador-posicional/driver.py up                 la deja arrancada (pid en C:/dev/salidas/run/)
    python .claude/skills/run-localizador-posicional/driver.py down               la apaga

Pasos (lista JSON), en orden; cada paso espera a que Streamlit termine de recalcular:
    {"llenar": "Etiqueta del campo", "valor": "1200"}     escribe y confirma con Enter (o "confirmar": "tab")
    {"clic": "Texto del boton, opcion o pestana"}
    {"espera_texto": "algo"} / {"sin_texto": "algo"}       falla si no aparece / si aparece
    {"captura": "nombre"}                                  PNG en C:/dev/salidas/run/localizador-posicional-nombre.png
    {"texto": true}                                        imprime el texto visible
Salida: una linea JSON con ok, titulo, caracteres, excepciones y la ruta de la captura. Codigo 0 si todo bien.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

NOMBRE, SLUG, PUERTO, APP = "Localizador Posicional - Web", "localizador-posicional", 8648, "app.py"
SALIDA = Path("C:/dev/salidas/run")
URL = f"http://127.0.0.1:{PUERTO}"
PID = SALIDA / f"{SLUG}.pid"
ERRORES = re.compile(r"Traceback|ModuleNotFoundError|ImportError|Error running app|Failed to fetch dynamically imported module")


def arrancar():
    SALIDA.mkdir(parents=True, exist_ok=True)
    if not Path(APP).exists():
        sys.exit(f"no encuentro {APP}: lanza el driver desde la carpeta de la herramienta (la del {APP})")
    try:  # ¿ya hay algo escuchando en ese puerto?
        urllib.request.urlopen(f"{URL}/_stcore/health", timeout=2)
        sys.exit(f"el puerto {PUERTO} ya esta ocupado: `driver.py down` o cambia PUERTO")
    except OSError:
        pass
    log = open(SALIDA / f"{SLUG}.log", "w", encoding="utf-8")
    env = dict(os.environ, AGRIM_SIN_CONTADOR="1", PYTHONUTF8="1", STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    p = subprocess.Popen([sys.executable, "-m", "streamlit", "run", APP, f"--server.port={PUERTO}", "--server.headless=true",
                          "--server.address=127.0.0.1", "--browser.gatherUsageStats=false"],
                         stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    PID.write_text(str(p.pid))
    for _ in range(90):
        try:
            if urllib.request.urlopen(f"{URL}/_stcore/health", timeout=2).read() == b"ok":
                return p
        except OSError:
            time.sleep(1)
        if p.poll() is not None:
            break
    apagar()
    sys.exit(f"streamlit no arranco; mira {SALIDA / (SLUG + '.log')}")


def apagar():
    if PID.exists():
        pid = PID.read_text().strip()
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
        PID.unlink(missing_ok=True)


def quieta(pag, extra=500):
    """Espera a que Streamlit deje de recalcular (el indicador «Running» desaparece)."""
    pag.wait_for_selector('[data-testid="stApp"]', timeout=30000)
    for _ in range(60):
        if pag.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        pag.wait_for_timeout(250)
    pag.wait_for_timeout(extra)


def texto(pag):
    return pag.inner_text("body")


def excepciones(pag):
    return pag.locator('[data-testid="stException"]').count() + len(ERRORES.findall(texto(pag)))


def abrir(pw):
    nav = pw.chromium.launch()
    pag = nav.new_page(viewport={"width": 1280, "height": 1600})
    pag.goto(URL, wait_until="networkidle", timeout=90000)
    quieta(pag, 1500)
    if excepciones(pag):  # la primera carga puede fallar al pedir un modulo: una recarga lo dice
        pag.reload(wait_until="networkidle")
        quieta(pag, 1500)
    return nav, pag


def captura(pag, nombre):
    ruta = SALIDA / f"{SLUG}-{nombre}.png"
    pag.screenshot(path=str(ruta), full_page=True)
    return str(ruta).replace(chr(92), "/")


def paso(pag, p):
    if "llenar" in p:
        etiqueta = p["llenar"].replace('"', '')
        # Streamlit pone la etiqueta en el aria-label del <input>; get_by_label a secas puede resolver al boton de ayuda
        campo = pag.locator(f'input[aria-label*="{etiqueta}" i], textarea[aria-label*="{etiqueta}" i]')
        campo = (campo if campo.count() else pag.get_by_label(p["llenar"], exact=False)).first
        campo.click()
        campo.fill(str(p["valor"]))
        campo.press("Tab" if p.get("confirmar") == "tab" else "Enter")
    elif "clic" in p:
        objetivo = pag.get_by_role("button", name=re.compile(re.escape(p["clic"]), re.I))
        if objetivo.count() == 0:
            objetivo = pag.get_by_text(p["clic"], exact=False)
        objetivo.first.click()
    elif "espera_texto" in p:
        pag.get_by_text(p["espera_texto"], exact=False).first.wait_for(timeout=20000)
    elif "sin_texto" in p:
        if p["sin_texto"] in texto(pag):
            raise AssertionError(f"aparece «{p['sin_texto']}»")
    elif "captura" in p:
        print("captura:", captura(pag, p["captura"]))
    elif "texto" in p:
        print(texto(pag)[:2500])
    quieta(pag)


def main():
    orden = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if orden == "down":
        return apagar()
    if orden == "up":
        arrancar()
        return print(f"arrancada en {URL} (pid {PID.read_text()}); `driver.py down` la apaga")
    from playwright.sync_api import sync_playwright
    proceso = arrancar()
    resultado = {"ok": False}
    try:
        with sync_playwright() as pw:
            nav, pag = abrir(pw)
            if orden == "controles":
                print(json.dumps(pag.evaluate("""() => ({
                  campos: [...document.querySelectorAll('input[aria-label], textarea[aria-label]')].map(e => e.getAttribute('aria-label')),
                  botones: [...document.querySelectorAll('button')].map(e => e.innerText.trim()).filter(Boolean),
                  opciones: [...document.querySelectorAll('[role=radio], [role=tab], [role=option]')].map(e => e.innerText.trim()).filter(Boolean)})"""),
                                 ensure_ascii=False))
            if orden == "pasos":
                for p in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")):
                    paso(pag, p)
            resultado = {"ok": excepciones(pag) == 0 and len(texto(pag)) > 200, "titulo": pag.title(), "caracteres": len(texto(pag)),
                         "excepciones": excepciones(pag), "captura": captura(pag, "smoke" if orden == "smoke" else "final")}
            nav.close()
    except Exception as e:  # noqa: BLE001
        resultado["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    finally:
        apagar()
        if proceso.poll() is None:
            proceso.kill()
    print(json.dumps(resultado, ensure_ascii=False))
    sys.exit(0 if resultado.get("ok") else 1)


if __name__ == "__main__":
    main()
