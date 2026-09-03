"""Официальные названия этапов и трасс + таймзоны трасс.

Названия в исходных данных (sportstimes/f1) ненадёжны — там встречаются
обрывки вроде "Bahrain Grand Prix (Malaysia)". Поэтому названия берём
только отсюда, а из JSON — исключительно времена сессий.
"""

# location из JSON -> IANA-таймзона трассы
CIRCUIT_TZ = {
    "Melbourne": "Australia/Melbourne",
    "Shanghai": "Asia/Shanghai",
    "Suzuka": "Asia/Tokyo",
    "Miami": "America/New_York",
    "Montreal": "America/Toronto",
    "Monte Carlo": "Europe/Monaco",
    "Barcelona": "Europe/Madrid",
    "Madrid": "Europe/Madrid",
    "Spielberg": "Europe/Vienna",
    "Silverstone": "Europe/London",
    "Spa-Francorchamps": "Europe/Brussels",
    "Budapest": "Europe/Budapest",
    "Zandvoort": "Europe/Amsterdam",
    "Monza": "Europe/Rome",
    "Imola": "Europe/Rome",
    "Baku": "Asia/Baku",
    "Sepang": "Asia/Kuala_Lumpur",
    "Singapore": "Asia/Singapore",
    "Austin": "America/Chicago",
    "Mexico City": "America/Mexico_City",
    "Sao Paulo": "America/Sao_Paulo",
    "Las Vegas": "America/Los_Angeles",
    "Doha": "Asia/Qatar",
    "Lusail": "Asia/Qatar",
    "Yas Marina": "Asia/Dubai",
    "Jeddah": "Asia/Riyadh",
    "Sakhir": "Asia/Bahrain",
    "Portimao": "Europe/Lisbon",
    "Le Castellet": "Europe/Paris",
}

# (год, раунд) -> (официальное название этапа, официальное название трассы)
EVENTS = {
    2026: {
        1:  ("Australian Grand Prix",           "Albert Park Circuit"),
        2:  ("Chinese Grand Prix",              "Shanghai International Circuit"),
        3:  ("Japanese Grand Prix",             "Suzuka International Racing Course"),
        4:  ("Miami Grand Prix",                "Miami International Autodrome"),
        5:  ("Canadian Grand Prix",             "Circuit Gilles-Villeneuve"),
        6:  ("Monaco Grand Prix",               "Circuit de Monaco"),
        7:  ("Barcelona-Catalunya Grand Prix",  "Circuit de Barcelona-Catalunya"),
        8:  ("Austrian Grand Prix",             "Red Bull Ring"),
        9:  ("British Grand Prix",              "Silverstone Circuit"),
        10: ("Belgian Grand Prix",              "Circuit de Spa-Francorchamps"),
        11: ("Hungarian Grand Prix",            "Hungaroring"),
        12: ("Dutch Grand Prix",                "Circuit Zandvoort"),
        13: ("Italian Grand Prix",              "Autodromo Nazionale Monza"),
        14: ("Spanish Grand Prix",              "Madring"),
        15: ("Azerbaijan Grand Prix",           "Baku City Circuit"),
        # TODO: подтвердить официальное название 16-го этапа (перенос в Сепанг).
        16: ("Malaysian Grand Prix",            "Sepang International Circuit"),
        17: ("Singapore Grand Prix",            "Marina Bay Street Circuit"),
        18: ("United States Grand Prix",        "Circuit of the Americas"),
        19: ("Mexico City Grand Prix",          "Autodromo Hermanos Rodriguez"),
        20: ("Sao Paulo Grand Prix",            "Autodromo Jose Carlos Pace"),
        21: ("Las Vegas Grand Prix",            "Las Vegas Strip Circuit"),
        22: ("Qatar Grand Prix",                "Lusail International Circuit"),
        23: ("Abu Dhabi Grand Prix",            "Yas Marina Circuit"),
    },
}


def event_names(year, rnd, race):
    """Официальные названия. Если раунд ещё не занесён в EVENTS — падаем на
    данные источника и громко пишем в лог, чтобы это заметили в Actions."""
    try:
        return EVENTS[year][rnd]
    except KeyError:
        fallback = (f'{race["name"]} Grand Prix', race["location"])
        print(f"WARNING: нет названий для {year} этап {rnd}, использую {fallback}")
        return fallback


def circuit_tz(race):
    loc = race["location"]
    if loc not in CIRCUIT_TZ:
        print(f"WARNING: нет таймзоны для трассы {loc!r}, использую UTC")
        return "UTC"
    return CIRCUIT_TZ[loc]
