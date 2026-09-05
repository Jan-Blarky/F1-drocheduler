// Триггер для бота, живущий вне GitHub.
//
// Расписания GitHub Actions выполняются «по возможности»: за трое суток
// наблюдений из тридцати с лишним слотов отработала примерно четверть, с
// задержками до двух часов. Запуски же по событию dispatch стартуют
// мгновенно — поэтому крон переезжает сюда, а воркер умеет ровно одно:
// в нужную минуту постучаться в GitHub. Вся логика остаётся в Python.

const OWNER = "Jan-Blarky";
const REPO = "F1-drocheduler";

export default {
  async scheduled(event, env) {
    const response = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "User-Agent": "f1-drocheduler-trigger",
        },
        body: JSON.stringify({
          event_type: "run-bot",
          client_payload: { cron: event.cron },
        }),
      },
    );

    // Бросаем исключение, чтобы промах было видно в логах воркера,
    // а не только по отсутствию сообщения в группе.
    if (!response.ok) {
      throw new Error(`GitHub ${response.status}: ${await response.text()}`);
    }
  },
};
