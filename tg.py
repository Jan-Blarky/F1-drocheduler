"""Минимальный клиент Telegram Bot API на стандартной библиотеке."""

import json
import os
import time
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


class Telegram:
    def __init__(self, token=None, chat_id=None, dry_run=False):
        self.token = token or os.environ.get("TG_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TG_CHAT_ID", "")
        self.dry_run = dry_run
        missing = [name for name, value in
                   (("TG_BOT_TOKEN", self.token), ("TG_CHAT_ID", self.chat_id))
                   if not value]
        if missing and not dry_run:
            raise SystemExit(f"Не заданы {' / '.join(missing)}")
        if missing:
            print(f"WARNING: не заданы {' / '.join(missing)} — "
                  f"в боевом запуске это была бы ошибка")

    def _raw(self, method, http_timeout=30, **params):
        if self.dry_run:
            print(f"[dry-run] {method}({', '.join(f'{k}={v!r}' for k, v in params.items() if k != 'text')})")
            return {"message_id": 0}
        body = json.dumps(params).encode()
        req = urllib.request.Request(
            API.format(token=self.token, method=method),
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=http_timeout) as r:
            payload = json.load(r)
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram {method}: {payload}")
        return payload["result"]

    def _call(self, method, **params):
        return self._raw(method, chat_id=self.chat_id, **params)

    def send(self, text, pin=False, silent=False):
        if self.dry_run:
            print("\n" + "-" * 60 + f"\n{text}\n" + "-" * 60)
        result = self._call("sendMessage", text=text, parse_mode="HTML",
                            disable_web_page_preview=True,
                            disable_notification=silent)
        if pin:
            # без звука: уведомление о самом сообщении уже пришло
            self._call("pinChatMessage", message_id=result["message_id"],
                       disable_notification=True)
            self.drop_pin_notice(result["message_id"])
        return result["message_id"]

    def drop_pin_notice(self, pinned_id, wait=30):
        """Убрать служебное «бот закрепил сообщение», которое Telegram сам
        добавляет в чат следом за закрепом.

        Его id ниоткуда не возвращается, поэтому ждём его в getUpdates и
        удаляем только то сообщение, у которого в pinned_message лежит именно
        наш закреп: угадывать id по соседству нельзя — можно снести чужое.
        """
        if self.dry_run:
            print("[dry-run] удаление служебного сообщения о закрепе")
            return True

        offset, deadline = None, time.monotonic() + wait
        while time.monotonic() < deadline:
            try:
                # timeout — длинный опрос на стороне Telegram, http_timeout — наш
                updates = self._raw("getUpdates", http_timeout=40, timeout=20,
                                    offset=offset, allowed_updates=["message"])
            except Exception as e:                      # noqa: BLE001
                print(f"WARNING: не удалось прочитать апдейты ({e})")
                return False
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                pinned = message.get("pinned_message")
                if (pinned and pinned.get("message_id") == pinned_id
                        and str(message.get("chat", {}).get("id")) == str(self.chat_id)):
                    try:
                        self._raw("deleteMessage", chat_id=self.chat_id,
                                  message_id=message["message_id"])
                        return True
                    except Exception as e:              # noqa: BLE001
                        print(f"WARNING: служебное сообщение о закрепе не удалено "
                              f"— нужно право «Удаление сообщений» ({e})")
                        return False
        print("WARNING: служебное сообщение о закрепе не пришло в getUpdates, "
              "удалять нечего")
        return False

    def check(self):
        """Проверка боем без единого сообщения в группу: жив ли токен, виден
        ли чат и выдано ли право на закреп."""
        me = self._call("getMe")
        print(f"Бот: @{me.get('username')} (id {me.get('id')})")

        chat = self._call("getChat")
        print(f"Чат: {chat.get('title')!r}, тип {chat.get('type')}, id {chat.get('id')}")

        member = self._call("getChatMember", user_id=me["id"])
        status = member.get("status")
        can_pin = member.get("can_pin_messages")
        can_delete = member.get("can_delete_messages")
        print(f"Статус бота в чате: {status}, право на закреп: {can_pin}, "
              f"право на удаление: {can_delete}")

        if status != "administrator":
            return "Бот не администратор — закрепить сообщение не сможет"
        if not can_pin:
            return "У бота нет права «Закрепление сообщений»"
        if not can_delete:
            return ("У бота нет права «Удаление сообщений» — служебные надписи "
                    "о закрепе останутся висеть в чате")
        if chat.get("type") not in ("group", "supergroup"):
            return f"Это не групповой чат, а {chat.get('type')}"
        return None

    def test_pin(self):
        """Полный цикл закрепа на одноразовом сообщении: отправить, закрепить,
        убрать служебную надпись, открепить и удалить за собой. В чате остаётся
        только мелькнувшее сообщение."""
        message_id = self.send("🔧 Проверка закрепа — сообщение сейчас исчезнет.",
                               pin=True, silent=True)
        self._call("unpinChatMessage", message_id=message_id)
        self._raw("deleteMessage", chat_id=self.chat_id, message_id=message_id)
        print("Тестовое сообщение откреплено и удалено.")

    def unpin_all(self):
        self._call("unpinAllChatMessages")


def find_chats(token=None):
    """Печатает чаты, из которых бот недавно получал апдейты, — так проще
    всего узнать chat_id группы, не разбирая JSON руками."""
    token = token or os.environ.get("TG_BOT_TOKEN", "")
    if not token:
        raise SystemExit("Не задан TG_BOT_TOKEN")
    with urllib.request.urlopen(API.format(token=token, method="getUpdates"), timeout=30) as r:
        payload = json.load(r)
    if not payload.get("ok"):
        raise SystemExit(f"Telegram getUpdates: {payload}")

    chats = {}
    for update in payload["result"]:
        for value in update.values():
            if isinstance(value, dict) and "chat" in value:
                chat = value["chat"]
                chats[chat["id"]] = chat
    if not chats:
        print("Апдейтов нет. Добавь бота в группу и напиши в ней что-нибудь "
              "(например /start), потом запусти снова.")
        return
    print("Найденные чаты:")
    for chat_id, chat in chats.items():
        title = chat.get("title") or chat.get("username") or chat.get("first_name", "")
        print(f"  {chat_id}   {chat.get('type')}   {title}")
    print("\nВ TG_CHAT_ID нужен id группы — отрицательное число.")
