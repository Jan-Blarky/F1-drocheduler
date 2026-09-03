"""Названия этапов, трасс и таймзоны.

Название этапа — официальное, как на formula1.com, со спонсорским титулом:
«FORMULA 1 MSC CRUISES GRANDE PRÊMIO DE SÃO PAULO 2026». В календарных JSON
такого нет, поэтому названия лежат в event_names.json и обновляются раз в
сезон скриптом fetch_names.py. Своего мы не выдумываем.

Имён трасс и таймзон нет ни там, ни там: в JSON только город, а координаты
местами битые (у Майами широта 0) — поэтому они заданы здесь.
"""

import json
import pathlib

# location из JSON -> (официальное название трассы, IANA-таймзона)
CIRCUITS = {
    "Melbourne":         ("Albert Park Circuit",               "Australia/Melbourne"),
    "Shanghai":          ("Shanghai International Circuit",    "Asia/Shanghai"),
    "Suzuka":            ("Suzuka International Racing Course","Asia/Tokyo"),
    "Miami":             ("Miami International Autodrome",     "America/New_York"),
    "Montreal":          ("Circuit Gilles-Villeneuve",         "America/Toronto"),
    "Monte Carlo":       ("Circuit de Monaco",                 "Europe/Monaco"),
    "Barcelona":         ("Circuit de Barcelona-Catalunya",    "Europe/Madrid"),
    "Madrid":            ("Madring",                           "Europe/Madrid"),
    "Spielberg":         ("Red Bull Ring",                     "Europe/Vienna"),
    "Silverstone":       ("Silverstone Circuit",               "Europe/London"),
    "Spa-Francorchamps": ("Circuit de Spa-Francorchamps",      "Europe/Brussels"),
    "Budapest":          ("Hungaroring",                       "Europe/Budapest"),
    "Zandvoort":         ("Circuit Zandvoort",                 "Europe/Amsterdam"),
    "Monza":             ("Autodromo Nazionale Monza",         "Europe/Rome"),
    "Imola":             ("Autodromo Enzo e Dino Ferrari",     "Europe/Rome"),
    "Baku":              ("Baku City Circuit",                 "Asia/Baku"),
    "Sepang":            ("Sepang International Circuit",      "Asia/Kuala_Lumpur"),
    "Singapore":         ("Marina Bay Street Circuit",         "Asia/Singapore"),
    "Austin":            ("Circuit of the Americas",           "America/Chicago"),
    "Mexico City":       ("Autodromo Hermanos Rodriguez",      "America/Mexico_City"),
    "Sao Paulo":         ("Autodromo Jose Carlos Pace",        "America/Sao_Paulo"),
    "Las Vegas":         ("Las Vegas Strip Circuit",           "America/Los_Angeles"),
    "Doha":              ("Lusail International Circuit",      "Asia/Qatar"),
    "Lusail":            ("Lusail International Circuit",      "Asia/Qatar"),
    "Yas Marina":        ("Yas Marina Circuit",                "Asia/Dubai"),
    "Jeddah":            ("Jeddah Corniche Circuit",           "Asia/Riyadh"),
    "Sakhir":            ("Bahrain International Circuit",     "Asia/Bahrain"),
    "Portimao":          ("Autodromo Internacional do Algarve","Europe/Lisbon"),
    "Le Castellet":      ("Circuit Paul Ricard",               "Europe/Paris"),
}


NAMES_FILE = pathlib.Path(__file__).with_name("event_names.json")
try:
    OFFICIAL_NAMES = json.loads(NAMES_FILE.read_text())
except FileNotFoundError:
    OFFICIAL_NAMES = {}


def event_name(race, year, rnd):
    """Официальное название этапа. Если сезон ещё не выкачан fetch_names.py,
    берём короткое имя из календаря, чтобы бот не молчал, и просим обновить."""
    name = OFFICIAL_NAMES.get(str(year), {}).get(str(rnd))
    if name:
        return name
    fallback = race["name"].strip()
    if "grand prix" not in fallback.lower():
        fallback += " Grand Prix"
    print(f"WARNING: нет официального названия для {year} этап {rnd}, "
          f"использую {fallback!r} — запусти fetch_names.py {year}")
    return fallback


def circuit(race):
    """(название трассы, таймзона). Незнакомая трасса не роняет бота:
    подставляем город из источника и пишем WARNING в лог Actions."""
    loc = race["location"]
    if loc not in CIRCUITS:
        print(f"WARNING: трасса {loc!r} не заведена в events.CIRCUITS, "
              f"использую город и UTC")
        return loc, "UTC"
    return CIRCUITS[loc]
