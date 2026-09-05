#!/usr/bin/env python3
"""Расписание Ф1 в телеграм-группу.

Запускается по крону несколько раз в день и сам решает, пора ли что-то слать:

  * анонс уикенда   — понедельник 06:00 по Израилю той недели, где гонка;
                      вешается в закреп и висит до конца сезона;
  * напоминание     — 19:00 по Израилю накануне дня гонки Ф1, при включённой
                      сходке — с адресом, где смотрим вместе;
  * межсезонье      — после финального этапа: чистим закрепы и вешаем отсчёт
                      до первой гонки следующего сезона.

Сходка включается реакцией владельца группы на анонс этапа (см. PARTY_EMOJI).
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
from tg import Telegram, find_chats

STATE_FILE = pathlib.Path(__file__).with_name("state.json")

# Сколько времени после расчётного момента ещё имеет смысл слать анонс.
ANNOUNCE_WINDOW = datetime.timedelta(hours=12)

# Реакция-переключатель совместного просмотра. Кастомная эмодзи из набора
# t.me/addemoji/raceemoji опознаётся по custom_emoji_id (его печатает режим
# --watch-reactions), обычная 🔴 — как запасной вариант для не-премиума.
PARTY_CUSTOM_EMOJI = {"5465126501525527671"}
PARTY_PLAIN_EMOJI = {"🔴"}


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def is_party_reaction(reactions):
    for reaction in reactions or []:
        if reaction.get("type") == "custom_emoji":
            if reaction.get("custom_emoji_id") in PARTY_CUSTOM_EMOJI:
                return True
        elif reaction.get("emoji") in PARTY_PLAIN_EMOJI:
            return True
    return False


def emoji_ids(reactions):
    """Компактное описание реакций для лога — без сведений об авторе."""
    return [r.get("custom_emoji_id") or r.get("emoji") for r in reactions or []]


def announce_messages(state, year):
    """message_id анонса -> номер этапа. Учитываются и штатные анонсы, и
    отправленные вручную через --force-announce."""
    result = {}
    for key, value in state.items():
        if not isinstance(value, dict) or "message_id" not in value:
            continue
        parts = key.split("-")
        if len(parts) == 3 and parts[0] == str(year) and parts[2] in ("announce", "manual"):
            result[value["message_id"]] = int(parts[1])
    return result


def handle_reaction(update, tg, state, year, messages):
    """Реакция владельца группы на анонс включает и выключает сходку."""
    reaction = update.get("message_reaction")
    if not reaction:
        return

    user = reaction.get("user") or {}
    old, new = reaction.get("old_reaction"), reaction.get("new_reaction")
    message_id = reaction.get("message_id")
    # Логи публичного репозитория видны всем, поэтому пишем только эмодзи:
    # id и имя автора реакции туда попадать не должны.
    print(f"Реакция на сообщение {message_id}: "
          f"было {emoji_ids(old)}, стало {emoji_ids(new)}")

    rnd = messages.get(message_id)
    if rnd is None:
        print("  — это не анонс этапа, пропускаем")
        return
    if not user:
        print("  — реакция без автора (анонимный админ), пропускаем")
        return

    wants, wanted = is_party_reaction(new), is_party_reaction(old)
    if wants == wanted:
        print("  — реакция не про сходку, пропускаем")
        return

    status = tg.member_status(user["id"])
    if status != "creator":
        print(f"  — реакция не от владельца группы (статус {status}), пропускаем")
        return


    state[f"{year}-{rnd}-party"] = wants
    print(f"  — сходка на этапе {rnd}: {'включена' if wants else 'выключена'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="ничего не отправлять, только показать")
    ap.add_argument("--now", help="подменить текущее время, ISO (для тестов)")
    ap.add_argument("--preview", metavar="РАУНД", type=int,
                    help="показать оба сообщения для этапа и выйти")
    ap.add_argument("--check", action="store_true",
                    help="проверить токен, доступ к группе и права, ничего не отправляя")
    ap.add_argument("--test-pin", action="store_true",
                    help="прогнать полный цикл закрепа на одноразовом сообщении")
    ap.add_argument("--find-chat-id", action="store_true",
                    help="показать chat_id чатов, где есть бот (нужен только токен)")
    ap.add_argument("--watch-reactions", action="store_true",
                    help="подождать реакции и напечатать их целиком, включая "
                         "custom_emoji_id")
    ap.add_argument("--party", metavar="РАУНД", type=int,
                    help="включить сходку на этапе вручную")
    ap.add_argument("--no-party", metavar="РАУНД", type=int,
                    help="выключить сходку на этапе вручную")
    ap.add_argument("--force-announce", metavar="РАУНД", type=int,
                    help="отправить анонс этапа прямо сейчас, минуя расписание")
    args = ap.parse_args()

    if args.find_chat_id:
        find_chats()
        return 0

    if args.test_pin:
        Telegram(dry_run=args.dry_run).test_pin()
        return 0

    if args.check:
        problem = Telegram().check()
        if problem:
            sys.exit(f"НЕ ГОТОВО: {problem}")
        print("Всё на месте: бот админ группы и умеет закреплять.")
        return 0

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
        print(render.announce(wk), "\n\n", render.remind(wk, party=True), sep="")
        return 0

    state = load_state()
    before = json.dumps(state, sort_keys=True)

    if args.party or args.no_party:
        rnd = args.party or args.no_party
        state[f"{now.year}-{rnd}-party"] = bool(args.party)
        print(f"Сходка на этапе {rnd}: {'включена' if args.party else 'выключена'}")
        save_state(state)
        return 0

    tg = Telegram(dry_run=args.dry_run, offset=state.get("updates_offset"))
    messages = announce_messages(state, now.year)
    tg.on_update = lambda u: handle_reaction(u, tg, state, now.year, messages)

    if args.force_announce:
        wk = next((w for w in weekends if w["round"] == args.force_announce), None)
        if not wk:
            sys.exit(f"Нет этапа {args.force_announce} в сезоне {now.year}")
        print(f"Принудительный анонс этапа {wk['round']} ({wk['event']})")
        message_id = tg.send(render.announce(wk), pin=True)
        # запоминаем id, чтобы реакция на это сообщение тоже включала сходку;
        # ключ отдельный, штатный анонс он не отменяет
        state[f"{now.year}-{wk['round']}-manual"] = {"message_id": message_id}
        state["updates_offset"] = tg.offset
        if not args.dry_run:
            save_state(state)
        return 0

    if args.watch_reactions:
        print("Жду реакции 45 секунд...")
        tg.pump(wait=45)
        state["updates_offset"] = tg.offset
        if not args.dry_run:
            save_state(state)
        return 0

    tg.pump()          # разобрать реакции, накопившиеся с прошлого запуска
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
            party = bool(state.get(f"{year}-{rnd}-party"))
            print(f"Напоминание об этапе {rnd} ({wk['event']}), сходка: {party}")
            state[key] = {"sent_at": now.isoformat(),
                          "message_id": tg.send(render.remind(wk, party=party))}
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

    if tg.offset is not None:
        state["updates_offset"] = tg.offset
    if not sent:
        print(f"Нечего слать ({now:%Y-%m-%d %H:%M %Z})")
    if json.dumps(state, sort_keys=True) != before and not args.dry_run:
        save_state(state)
        print(f"Состояние обновлено{': ' + ', '.join(sent) if sent else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
