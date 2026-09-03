#!/usr/bin/env python3
"""Обновление официальных названий этапов с formula1.com.

Официальное название (со спонсорским титулом: «FORMULA 1 MSC CRUISES GRANDE
PRÊMIO DE SÃO PAULO 2026») есть только на сайте Ф1 — в календарных JSON его
нет. Скрипт забирает названия и складывает в event_names.json, который читает
бот. Запускается руками раз в сезон:

    python3 fetch_names.py 2027

Названия идут на странице в календарном порядке, по нему и раскладываются по
этапам. У прошедших гонок сайт показывает вместо дат подиум, поэтому дату
сверить можно не везде — но там, где она есть, скрипт проверяет совпадение и
падает при расхождении, чтобы молча не подписать этап чужим названием.
"""

import datetime
import html
import json
import pathlib
import re
import sys
import urllib.request

import f1data

URL = "https://www.formula1.com/en/racing/{year}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
NAMES_FILE = pathlib.Path(__file__).with_name("event_names.json")

TITLE = re.compile(r'<span[^>]*>(FORMULA 1[^<]+)</span>')
# «30 Oct - 01 Nov» или «06 - 08 Nov»; у прошедших гонок этого блока нет
DATES = re.compile(r'>(\d{1,2}(?:\s+[A-Za-z]{3})?\s*[-\u2013]\s*\d{1,2}\s+[A-Za-z]{3})<')
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def scrape(year):
    """[(название, дата окончания уикенда или None)] в календарном порядке."""
    req = urllib.request.Request(URL.format(year=year), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        page = r.read().decode("utf-8", "replace")

    found, seen = [], set()
    for m in TITLE.finditer(page):
        title = html.unescape(m.group(1)).strip()
        if "TESTING" in title.upper() or title in seen:
            continue      # тесты нам не нужны, а список на странице повторяется
        seen.add(title)
        # дата, если карточка ещё не превратилась в результат гонки
        window = page[m.end():m.end() + 600]
        d = DATES.search(window)
        found.append((title, parse_end(html.unescape(d.group(1)), year) if d else None))
    return found


def parse_end(dates, year):
    """'30 Oct - 01 Nov' и '06 - 08 Nov' -> дата последнего дня уикенда."""
    parts = re.split(r"[-–]", dates)
    if len(parts) != 2:
        return None
    tail = parts[1].strip()
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})", tail)
    if not m:
        return None
    day, month = int(m.group(1)), MONTHS.get(m.group(2).title())
    return datetime.date(year, month, day) if month else None


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year
    weekends = f1data.load_weekends(year)
    if not weekends:
        sys.exit(f"Нет календаря на {year} год")

    scraped = scrape(year)
    print(f"Со страницы Ф1 снято этапов: {len(scraped)}, в календаре: {len(weekends)}")
    if len(scraped) != len(weekends):
        sys.exit("Число этапов на сайте и в календаре не совпало — "
                 "раскладывать по порядку нельзя, нужна ручная проверка")

    weekends.sort(key=lambda w: w["gp_utc"])
    names, checked = {}, 0
    for wk, (title, end) in zip(weekends, scraped):
        # дата гонки по времени трассы — именно её показывает сайт Ф1
        if end is not None:
            if wk["gp_utc"].astimezone(wk["tz"]).date() != end:
                sys.exit(f"Порядок разъехался: этап {wk['round']} идёт "
                         f"{wk['gp_utc'].astimezone(wk['tz']).date()}, "
                         f"а сайт для {title!r} показывает {end}")
            checked += 1
        names[str(wk["round"])] = title

    store = json.loads(NAMES_FILE.read_text()) if NAMES_FILE.exists() else {}
    store[str(year)] = dict(sorted(names.items(), key=lambda kv: int(kv[0])))
    NAMES_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n")

    for rnd in sorted((w["round"] for w in weekends)):
        print(f'{rnd:>2}  {names[str(rnd)]}')
    print(f"\nЗаписано в {NAMES_FILE.name}: {len(names)} этапов, "
          f"из них {checked} сверено по дате")


if __name__ == "__main__":
    main()
