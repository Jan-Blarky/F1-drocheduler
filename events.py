"""Названия трасс и их таймзоны.

Название этапа НЕ придумываем — берём как есть из источника (там уже учтены
переносы и странности вроде «Bahrain Grand Prix (Malaysia)»). Единственное,
чего в источнике нет, — официальные имена трасс и их таймзоны: в JSON только
город, а координаты местами битые (у Майами широта 0).
"""

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


def event_name(race):
    """Название этапа из источника. В данных оно бывает и полным
    («Bahrain Grand Prix (Malaysia)»), и коротким («Italian») — во втором
    случае дописываем Grand Prix и больше ничего не меняем."""
    name = race["name"].strip()
    return name if "grand prix" in name.lower() else f"{name} Grand Prix"


def circuit(race):
    """(название трассы, таймзона). Незнакомая трасса не роняет бота:
    подставляем город из источника и пишем WARNING в лог Actions."""
    loc = race["location"]
    if loc not in CIRCUITS:
        print(f"WARNING: трасса {loc!r} не заведена в events.CIRCUITS, "
              f"использую город и UTC")
        return loc, "UTC"
    return CIRCUITS[loc]
