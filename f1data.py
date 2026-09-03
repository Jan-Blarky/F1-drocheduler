"""Загрузка календарей Ф1/Ф2/Ф3 и сборка уикендов."""

import datetime
import json
import urllib.error
import urllib.request

from zoneinfo import ZoneInfo

import events

URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db/{series}/{year}.json"
SERIES = ("f1", "f2", "f3")
ISRAEL = ZoneInfo("Asia/Jerusalem")


def parse_ts(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch(series, year):
    """Список этапов серии или None, если календаря на этот год ещё нет."""
    try:
        with urllib.request.urlopen(URL.format(series=series, year=year), timeout=30) as r:
            return json.load(r)["races"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _session_dates(race):
    return {parse_ts(v).date() for v in race["sessions"].values()}


def load_weekends(year):
    """Этапы Ф1 с приклеенными к ним по датам этапами Ф2/Ф3.

    Ф2 и Ф3 приезжают не на каждый этап, а их нумерация раундов своя, поэтому
    единственный надёжный признак — пересечение дат сессий.
    """
    f1_races = fetch("f1", year)
    if f1_races is None:
        return []

    juniors = {s: (fetch(s, year) or []) for s in ("f2", "f3")}
    weekends = []
    for race in f1_races:
        days = _session_dates(race)
        wk = {"year": year, "round": race["round"], "f1": race}
        for s, races in juniors.items():
            for jr in races:
                if _session_dates(jr) & days:
                    wk[s] = jr
                    break
        circuit, tz = events.circuit(race)
        wk["event"] = events.event_name(race)
        wk["circuit"] = circuit
        wk["tz"] = ZoneInfo(tz)
        wk["gp_utc"] = parse_ts(race["sessions"]["gp"])
        wk["gp_il"] = wk["gp_utc"].astimezone(ISRAEL)
        weekends.append(wk)
    return weekends


def announce_at(weekend):
    """Понедельник 10:00 по Израилю той недели, на которой проходит гонка.

    Гонка бывает и в субботу (Баку-2026), поэтому отсчитываем от понедельника
    недели, а не «минус шесть дней от гонки».
    """
    race_day = weekend["gp_il"].date()
    monday = race_day - datetime.timedelta(days=race_day.weekday())
    return datetime.datetime.combine(monday, datetime.time(10, 0), ISRAEL)


def remind_at(weekend):
    """19:00 по Израилю накануне того дня, когда гонка идёт по израильскому
    календарю. Для Лас-Вегаса гонка местно субботняя, но у нас воскресная —
    правило это учитывает автоматически."""
    eve = weekend["gp_il"].date() - datetime.timedelta(days=1)
    return datetime.datetime.combine(eve, datetime.time(19, 0), ISRAEL)


def offseason_at(weekends):
    """Понедельник 10:00 по Израилю на следующей неделе после финального этапа."""
    last = max(w["gp_il"] for w in weekends).date()
    monday = last - datetime.timedelta(days=last.weekday()) + datetime.timedelta(days=7)
    return datetime.datetime.combine(monday, datetime.time(10, 0), ISRAEL)


def first_race_of(year):
    """(дата первой гонки сезона по Израилю, официальное название) или None."""
    races = fetch("f1", year)
    if not races:
        return None
    race = min(races, key=lambda r: r["sessions"]["gp"])
    return parse_ts(race["sessions"]["gp"]).astimezone(ISRAEL), events.event_name(race)
