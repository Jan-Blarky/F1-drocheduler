#!/usr/bin/env python3
"""Расписание Ф1 в телеграм-группу.

Запускается по крону несколько раз в день и сам решает, пора ли что-то слать:

  * анонс уикенда   — понедельник 10:00 по Израилю той недели, где гонка;
                      вешается в закреп и висит до конца сезона;
  * напоминание     — 19:00 по Израилю накануне дня гонки Ф1;
  * межсезонье      — после финального этапа: чистим закрепы и вешаем отсчёт
                      до первой гонки следующего сезона.

Отправленное фиксируется в state.json, поэтому лишний запуск крона ничего не
задублирует, а пропущенный (упавший раннер) догоняется на следующем запуске,
пока не истекло окно.
"""

import argparse
import datetime
import json
import pathlib
import sys

import f1data
import render
from f1data import ISRAEL
from tg import Telegram

STATE_FILE = pathlib.Path(__file__).with_name("state.json")

# Сколько времени после расчётного момента ещё имеет смысл слать анонс.
ANNOUNCE_WINDOW = datetime.timedelta(hours=12)


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="ничего не отправлять, только показать")
    ap.add_argument("--now", help="подменить текущее время, ISO (для тестов)")
    ap.add_argument("--preview", metavar="РАУНД", type=int,
                    help="показать оба сообщения для этапа и выйти")
    ap.add_argument("--force-announce", metavar="РАУНД", type=int,
                    help="отправить анонс этапа прямо сейчас, минуя расписание "
                         "и не отмечая его в state (для проверки прав на закреп)")
    args = ap.parse_args()

    now = (datetime.datetime.fromisoformat(args.now).replace(tzinfo=ISRAEL)
           if args.now else datetime.datetime.now(ISRAEL))
    weekends = f1data.load_weekends(now.year)
    if not weekends:
        print(f"Календарь на {now.year} год недоступен")
        return 0

    if args.preview:
        wk = next((w for w in weekends if w["round"] == args.preview), None)
        if not wk:
            sys.exit(f"Нет этапа {args.preview} в сезоне {now.year}")
        print(render.announce(wk), "\n\n", render.remind(wk), sep="")
        return 0

    tg = Telegram(dry_run=args.dry_run)

    if args.force_announce:
        wk = next((w for w in weekends if w["round"] == args.force_announce), None)
        if not wk:
            sys.exit(f"Нет этапа {args.force_announce} в сезоне {now.year}")
        print(f"Принудительный анонс этапа {wk['round']} ({wk['event']})")
        tg.send(render.announce(wk), pin=True)
        return 0

    state = load_state()
    sent = []

    for wk in weekends:
        rnd, year = wk["round"], wk["year"]

        key = f"{year}-{rnd}-announce"
        due = f1data.announce_at(wk)
        if key not in state and due <= now < due + ANNOUNCE_WINDOW:
            print(f"Анонс этапа {rnd} ({wk['event']})")
            state[key] = {"sent_at": now.isoformat(),
                          "message_id": tg.send(render.announce(wk), pin=True)}
            sent.append(key)

        key = f"{year}-{rnd}-remind"
        due = f1data.remind_at(wk)
        # Верхняя граница — старт гонки: после него напоминание бессмысленно.
        if key not in state and due <= now < wk["gp_il"]:
            print(f"Напоминание об этапе {rnd} ({wk['event']})")
            state[key] = {"sent_at": now.isoformat(),
                          "message_id": tg.send(render.remind(wk))}
            sent.append(key)

    key = f"{now.year}-offseason"
    if key not in state and now >= f1data.offseason_at(weekends):
        first = f1data.first_race_of(now.year + 1)
        if first is None:
            # Календарь следующего сезона ещё не опубликован — попробуем позже.
            print(f"Сезон {now.year} закончился, календаря на {now.year + 1} ещё нет")
        else:
            print(f"Межсезонье: чистим закрепы, считаем дни до {first[1]}")
            tg.unpin_all()
            text = render.offseason(now.year, now.year + 1, first, now.date())
            state[key] = {"sent_at": now.isoformat(),
                          "message_id": tg.send(text, pin=True)}
            sent.append(key)

    if sent and not args.dry_run:
        save_state(state)
        print(f"Отправлено: {', '.join(sent)}")
    elif not sent:
        print(f"Нечего слать ({now:%Y-%m-%d %H:%M %Z})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
