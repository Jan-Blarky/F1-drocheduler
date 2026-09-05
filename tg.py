"""Минимальный клиент Telegram Bot API на стандартной библиотеке."""

import json
import os
import time
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"
# Реакции и служебные сообщения о закрепе приходят одним потоком, поэтому
# читать его надо в одном месте: подтверждённый offset стирает всё, что было
# раньше, и «лишний» getUpdates легко проглотил бы чужую реакцию.
ALLOWED_UPDATES = ["message", "message_reaction"]


class Telegram:
    def __init__(self, token=None, chat_id=None, dry_run=False,
                 offset=None, on_update=None):
        self.token = token or os.environ.get("TG_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TG_CHAT_ID", "")
        self.dry_run = dry_run
        self.offset = offset          # с какого update_id читать дальше
        self.on_update = on_update    # куда отдавать всё, что пришло

        missing = [name for name, value in
                   (("TG_BOT_TOKEN", self.token), ("TG_CHAT_ID", self.chat_id))
                   if not value]
        if missing and not dry_run:
            raise SystemExit(f"Не заданы {' / '.join(missing)}")
        if missing:
            print(f"WARNING: не заданы {' / '.join(missing)} — "
                  f"в боевом запуске это была бы ошибка")

    # --- транспорт ---------------------------------------------------------

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

    # --- чтение апдейтов ---------------------------------------------------

    def pump(self, wait=0, stop_when=None):
        """Вычитать очередь апдейтов и раздать их on_update.

        wait — сколько секунд Telegram держит длинный опрос, если очередь
        пуста. stop_when опознаёт апдейт, ради которого мы пришли: пачку
        дочитываем до конца (чтобы ничего не потерять), но дальше не ждём.
        """
        if self.dry_run:
            print(f"[dry-run] getUpdates(offset={self.offset})")
            return False

        found, deadline = False, time.monotonic() + wait
        while True:
            updates = self._raw("getUpdates", http_timeout=wait + 25,
                                offset=self.offset, timeout=wait,
                                allowed_updates=ALLOWED_UPDATES)
            for update in updates:
                self.offset = update["update_id"] + 1
                if stop_when is not None and stop_when(update):
                    found = True
                elif self.on_update is not None:
                    self.on_update(update)
            if found or time.monotonic() >= deadline:
                return found

    # --- отправка ----------------------------------------------------------

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

    def drop_pin_notice(self, pinned_id, wait=25):
        """Убрать служебное «бот закрепил сообщение», которое Telegram сам
        добавляет в чат следом за закрепом.

        Его id ниоткуда не возвращается, поэтому ждём его в апдейтах и удаляем
        только то сообщение, у которого в pinned_message лежит именно наш
        закреп: угадывать id по соседству нельзя — можно снести чужое.
        """
        notice_id = None

        def is_notice(update):
            nonlocal notice_id
            message = update.get("message") or {}
            pinned = message.get("pinned_message") or {}
            if (pinned.get("message_id") == pinned_id
                    and str(message.get("chat", {}).get("id")) == str(self.chat_id)):
                notice_id = message["message_id"]
                return True
            return False

        try:
            self.pump(wait=wait, stop_when=is_notice)
        except Exception as e:                              # noqa: BLE001
            print(f"WARNING: не удалось прочитать апдейты ({e})")
            return False

        if notice_id is None:
            print("WARNING: служебное сообщение о закрепе не пришло, удалять нечего")
            return False
        try:
            self._raw("deleteMessage", chat_id=self.chat_id, message_id=notice_id)
            return True
        except Exception as e:                              # noqa: BLE001
            print(f"WARNING: служебное сообщение о закрепе не удалено — "
                  f"нужно право «Удаление сообщений» ({e})")
            return False

    def unpin_all(self):
        self._call("unpinAllChatMessages")

    # --- диагностика -------------------------------------------------------

    def member_status(self, user_id):
        """creator / administrator / member / left / kicked."""
        return self._call("getChatMember", user_id=user_id).get("status")

    def test_pin(self):
        """Полный цикл закрепа на одноразовом сообщении: отправить, закрепить,
        убрать служебную надпись, открепить и удалить за собой. В чате остаётся
        только мелькнувшее сообщение."""
        message_id = self.send("🔧 Проверка закрепа — сообщение сейчас исчезнет.",
                               pin=True, silent=True)
        self._call("unpinChatMessage", message_id=message_id)
        self._raw("deleteMessage", chat_id=self.chat_id, message_id=message_id)
        print("Тестовое сообщение откреплено и удалено.")

    def check(self):
        """Проверка боем без единого сообщения в группу: жив ли токен, виден
        ли чат и выданы ли права."""
        me = self._call("getMe")
        print(f"Бот: id {me.get('id')}")

        # название группы в публичный лог Actions не пишем
        chat = self._call("getChat")
        print(f"Чат: тип {chat.get('type')}")

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
