"""Тексты сообщений. Разметка — HTML (parse_mode=HTML)."""

import datetime

from f1data import ISRAEL, parse_ts

DAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]

# Только квалификации, спринты и гонки — свободные заезды не показываем.
F1_SESSIONS = {
    "sprintQualifying": "Квалификация к спринту",
    "sprint": "Спринт",
    "qualifying": "Квалификация",
    "gp": "ГОНКА",
}
JUNIOR_SESSIONS = {
    "sprint": "Спринт",
    "feature": "Основная гонка",
}
SERIES_LABEL = {"f1": "Ф1", "f2": "Ф2", "f3": "Ф3"}


def _rows(weekend):
    """Все показываемые сессии уикенда, отсортированные по времени."""
    rows = []
    for series, labels in (("f1", F1_SESSIONS), ("f2", JUNIOR_SESSIONS), ("f3", JUNIOR_SESSIONS)):
        race = weekend.get(series)
        if not race:
            continue
        for key, label in labels.items():
            if key not in race["sessions"]:
                continue
            utc = parse_ts(race["sessions"][key])
            rows.append((utc.astimezone(ISRAEL), utc.astimezone(weekend["tz"]),
                         SERIES_LABEL[series], label, key))
    rows.sort()
    return rows


def _series_phrase(weekend):
    names = [SERIES_LABEL[s] for s in ("f1", "f2", "f3") if s in weekend]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " и " + names[-1]


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def announce(weekend):
    lines = [
        f'🏁 <b>Этап {weekend["round"]} — {weekend["event"]}</b>',
        f'📍 {weekend["circuit"]}',
        f'В эти выходные едут {_series_phrase(weekend)}.',
        '',
    ]
    current_day = None
    for israel, local, series, label, key in _rows(weekend):
        if israel.date() != current_day:
            current_day = israel.date()
            lines.append(f'<b>{DAYS[israel.weekday()].capitalize()}, '
                         f'{israel.day} {MONTHS[israel.month - 1]}</b>')
        marker = '🔴 ' if key == 'gp' else '     '
        lines.append(f'{marker}{series} · {label} — <b>{israel:%H:%M}</b> ({local:%H:%M})')
    lines += ['', '<i>Время израильское, в скобках — местное на трассе.</i>']
    return "\n".join(lines)


def remind(weekend):
    israel = weekend["gp_il"]
    local = weekend["gp_utc"].astimezone(weekend["tz"])
    return (f'⏰ <b>Завтра гонка Ф1</b> — этап {weekend["round"]}, {weekend["event"]}.\n'
            f'📍 {weekend["circuit"]}\n'
            f'Старт в <b>{israel:%H:%M}</b> по Израилю ({local:%H:%M} на трассе).')


def offseason(finished_year, next_year, first_race, today):
    days = (first_race[0].date() - today).days
    word = plural(days, "день", "дня", "дней")
    return (f'🏁 <b>Сезон {finished_year} завершён.</b>\n\n'
            f'Страдать <b>{days} {word}</b> до первой гонки сезона {next_year} — '
            f'{first_race[1]}, {first_race[0].day} {MONTHS[first_race[0].month - 1]}.')
