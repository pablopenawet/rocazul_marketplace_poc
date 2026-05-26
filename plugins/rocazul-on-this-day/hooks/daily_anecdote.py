#!/usr/bin/env python3
"""SessionStart hook — inyecta una efeméride histórica del día actual.

Estrategia:
  1. Consulta la API pública de Wikipedia "On This Day" (inglés).
  2. Si no hay red o no devuelve eventos, usa un fallback local en español.
  3. Inyecta el resultado vía hookSpecificOutput.additionalContext con una
     directiva para que Claude abra su primera respuesta presentando la
     efeméride traducida al español.

El hook falla silenciosamente (exit 0 sin output) ante cualquier error,
para no degradar el arranque de la sesión.
"""

import json
import random
import sys
import urllib.error
import urllib.request
from datetime import datetime

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Saludos con personalidad. Se elige uno al azar al iniciar sesión y se usa
# como apertura ANTES de la efeméride.
GREETINGS = [
    "¿Qué día tan bueno hoy para hacer combobulating no? Pero antes un poquito de historia…",
    "Cuánto tiempo sin verte, bro. Literal que eres un máquina. Pero antes un poquito de historia…",
    "Buenas as as as. ¿Sabes aquello de no te acostarás sin saber una cosa más? Pues estoy aquí a tu servicio…",
    "Como diría diego: BUENOOOOOOOOS DIAAAAAAAS. Y para empezar la session, un poquito de historia…",
    "¡Eyyy! Otra sesión más para la posteridad. Y hablando de posteridad…",
    "A ver, a ver, a ver. ¿Qué tenemos hoy? Antes de nada, un dato para presumir luego en la cena…",
]

WIKIPEDIA_URL = (
    "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month:02d}/{day:02d}"
)
HTTP_TIMEOUT_SECS = 3
USER_AGENT = "rocazul-on-this-day/0.1 (Claude Code plugin; +https://github.com/pablopenawet/rocazul_marketplace_poc)"

# Fallback offline: una efeméride significativa por día clave del año.
# Cobertura parcial intencional — solo se usa si la API no responde.
FALLBACK_ES = {
    "01-01": "1959 — Fidel Castro entra triunfalmente en La Habana, marcando el fin del régimen de Batista en Cuba.",
    "01-27": "1945 — El Ejército Rojo libera el campo de concentración de Auschwitz-Birkenau.",
    "02-11": "1990 — Nelson Mandela es liberado tras 27 años en prisión.",
    "03-14": "1879 — Nace Albert Einstein en Ulm, Reino de Württemberg.",
    "04-12": "1961 — Yuri Gagarin se convierte en el primer humano en viajar al espacio exterior.",
    "05-08": "1945 — Alemania nazi firma su rendición incondicional, terminando la Segunda Guerra Mundial en Europa.",
    "05-26": "1828 — Aparece misteriosamente el joven Kaspar Hauser en Núremberg, dando origen a uno de los enigmas históricos más célebres de Europa.",
    "06-06": "1944 — Día D: las fuerzas aliadas desembarcan en las playas de Normandía.",
    "07-04": "1776 — Las Trece Colonias adoptan la Declaración de Independencia de los Estados Unidos.",
    "07-20": "1969 — Neil Armstrong pisa la Luna durante la misión Apolo 11.",
    "08-15": "1945 — Japón anuncia su rendición, poniendo fin a la Segunda Guerra Mundial.",
    "09-11": "2001 — Atentados terroristas contra las Torres Gemelas y el Pentágono.",
    "10-12": "1492 — Cristóbal Colón llega al continente americano, desembarcando en la isla de Guanahaní.",
    "11-09": "1989 — Cae el Muro de Berlín tras 28 años dividiendo la ciudad alemana.",
    "12-10": "1948 — La Asamblea General de la ONU adopta la Declaración Universal de los Derechos Humanos.",
    "12-25": "800 — Carlomagno es coronado emperador del Sacro Imperio Romano por el papa León III.",
}


def fetch_wikipedia_event(month: int, day: int):
    """Devuelve 'AÑO — texto' o None si falla la red / no hay eventos."""
    url = WIKIPEDIA_URL.format(month=month, day=day)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECS) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    events = payload.get("events") or []
    if not events:
        return None

    evt = random.choice(events)
    year = evt.get("year")
    text = (evt.get("text") or "").strip()
    if year is None or not text:
        return None
    return f"{year} — {text}"


def main() -> None:
    today = datetime.now()
    month, day = today.month, today.day
    date_es = f"{day} de {MESES_ES[month - 1]}"

    event = fetch_wikipedia_event(month, day)
    source = "Wikipedia (inglés — traducir al español)" if event else None
    if not event:
        event = FALLBACK_ES.get(f"{month:02d}-{day:02d}")
        source = "fallback local (ya en español)" if event else None

    if not event:
        # Sin efeméride disponible: no inyectes nada para no contaminar contexto.
        sys.exit(0)

    greeting = random.choice(GREETINGS)

    directive = (
        f"Hoy es {date_es}. Efeméride histórica disponible (fuente: {source}):\n\n"
        f">>> {event}\n\n"
        f"INSTRUCCIÓN PARA TU PRIMERA RESPUESTA EN ESTA SESIÓN:\n"
        f"Antes de abordar la petición del usuario, abre con esta estructura EXACTA:\n\n"
        f"1) Saludo verbatim (cópialo tal cual, respetando puntuación, mayúsculas y "
        f"repeticiones — es así a propósito):\n"
        f"   {greeting}\n\n"
        f"2) Salto de línea, y a continuación un encabezado del tipo "
        f"\"📅 Un {date_es} como hoy…\" seguido de la efeméride en español "
        f"(tradúcela si la fuente está en inglés), en 1 o 2 frases.\n\n"
        f"3) Salto de línea, y entonces atiende normalmente la petición del usuario.\n\n"
        f"NO repitas el saludo ni la efeméride en respuestas posteriores de la misma sesión."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": directive,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
