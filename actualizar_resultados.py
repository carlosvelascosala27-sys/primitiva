#!/usr/bin/env python3
"""Descarga el resultado de La Primitiva y lo guarda en resultados.json.

Uso:
    python actualizar_resultados.py              # último sábado
    python actualizar_resultados.py 2026-09-26   # una fecha concreta

Necesita:  pip install requests beautifulsoup4
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
# Categoría de la web -> clave que usa la página de tu padre
CATEGORIAS = {"Especial": "6r", "1": "6", "2": "5c", "3": "5", "4": "4", "5": "3"}


def ultimo_sabado(hoy=None):
    hoy = hoy or date.today()
    return hoy - timedelta(days=(hoy.weekday() - 5) % 7)


def url_sorteo(d):
    return (f"https://laguinda.app/blog/resultado-primitiva-hoy-"
            f"{DIAS[d.weekday()]}-{d.day:02d}-{MESES[d.month - 1]}-{d.year}/")


def importe(txt):
    """'49.213,69 €' -> 49213.69"""
    limpio = re.sub(r"[^\d,.]", "", txt)
    return float(limpio.replace(".", "").replace(",", "."))


def entero(txt):
    """'10.681' -> 10681"""
    return int(re.sub(r"\D", "", txt) or 0)


def leer(d):
    resp = requests.get(
        url_sorteo(d),
        headers={"User-Agent": "Mozilla/5.0 (compatible; PrimitivaPadre/1.0)"},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    texto = soup.get_text(" ", strip=True)

    # Combinación: "03 09 10 30 36 45 C26 R4"
    m = re.search(r"((?:\d{2}\s+){5}\d{2})\s+C(\d{1,2})\s+R(\d)", texto)
    if not m:
        raise ValueError("No encuentro la combinación en la página (¿sorteo aún no publicado?)")
    resultado = {
        "n": sorted(int(x) for x in m.group(1).split()),
        "c": int(m.group(2)),
        "r": int(m.group(3)),
    }

    # Tabla "Reparto de premios": categoría | acertantes | importe
    premios = {}
    for fila in soup.select("table tr"):
        celdas = [c.get_text(" ", strip=True) for c in fila.find_all(["td", "th"])]
        if len(celdas) < 3:
            continue
        cat = re.match(r"(Especial|[1-5])", celdas[0])
        if cat:
            premios[CATEGORIAS[cat.group(1)]] = {"a": entero(celdas[1]), "e": importe(celdas[2])}
        elif celdas[0].lower().startswith("reintegro"):
            premios["r"] = {"a": entero(celdas[1]), "e": importe(celdas[2])}
    if premios:
        resultado["premios"] = premios

    # Bote: es el del PRÓXIMO sorteo
    b = re.search(r"Próximo bote:?\s*([\d.]+)\s*€", texto)
    if b:
        resultado["bote"] = importe(b.group(1))

    return resultado


def main():
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else ultimo_sabado()
    archivo = Path(__file__).with_name("resultados.json")
    datos = json.loads(archivo.read_text("utf-8")) if archivo.exists() else {}

    clave = d.isoformat()
    if clave in datos:
        print(f"{clave}: ya estaba guardado.")
        return
    try:
        datos[clave] = leer(d)
    except Exception as e:  # el fallo se ve en GitHub Actions
        print(f"{clave}: no se pudo leer el resultado -> {e}")
        sys.exit(1)

    archivo.write_text(json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True), "utf-8")
    print(f"{clave}: guardado -> {datos[clave]}")


if __name__ == "__main__":
    main()
