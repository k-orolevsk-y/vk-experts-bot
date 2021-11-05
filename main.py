import time
import config
import random
from typing import Union
from vk_api import VkApi, ApiError


class Main:
    vk_session: VkApi
    category_id: str

    def __init__(self):
        self.vk_session = VkApi(token=str(config.access_token))
        self.check_access_token()
        self.get_newsfeed_id()
        self.start_bot()

    def check_access_token(self):
        try:
            user = self.vk_session.method("users.get")
            if len(user) <= 0:
                raise ApiError(self.vk_session, None, None, None, {"error_code": -1})
        except ApiError:
            exit("❗️ Невалидный токен.")

    def get_newsfeed(self, params: Union[dict, None] = None):
        if params is None:
            params = {}

        return self.vk_session.method("newsfeed.getCustom", params)

    def get_newsfeed_id(self):
        print("⚙️ Определяю ID категории, в которой Вы эксперт.")

        category_id = self.vk_session.method("execute", {
            "code": '''
                var category_id = 2;
                
                while(category_id < 14) {
                   var newsfeed = API.newsfeed.getCustom({ "count": 3, "feed_id": 'discover_category/'+category_id });
                    if(newsfeed.items[1].rating != null && newsfeed.items[2].rating != null && newsfeed.items[3].rating != null){
                         return category_id;
                    }
                    
                     category_id = category_id+1;
                }
                
                return 0;
            '''
        })
        if category_id == 0:
            exit(f"📛 Не удалось определить категорию, в которой Вы эксперт.")
        elif category_id != 7 and not config.alt_categories:
            exit(f"📛 Для альтернативных от IT категорий бот пока не протестирован, но Вы можете его включить с помощью конфига.")

        self.category_id = f'discover_category/{category_id}'
        print(f"✅ ID успешно определён. ({category_id})\n")

    def start_bot(self):
        _type = input("⚙️ Бот успешно готов к запуску.\nВыберите один из режимов работы (1 - фарм, 2 - умное оценивание):")
        if _type not in ["1", "2"]:
            exit("⛔️ Запуск бота отменён.")

        start_from = ""
        while True:
            result = self.get_newsfeed({"count": 50, "feed_id": self.category_id, "start_from": start_from, "fields": "verified"})
            for item in result['items']:
                if item.get('type') == "expert_card":
                    continue  # Если элемент это карточка эксперта
                elif item.get('rating') is None:
                    continue  # Если нет объекта с информацией об оценивании
                elif not item.get('rating').get('can_change'):
                    continue  # Если мы не можем менять рейтинг
                elif item.get('rating').get('rated') != 0:
                    continue  # Если рейтинг уже установлен

                if _type == "1":
                    try:
                        self.vk_session.method("newsfeed.setPostVote",
                                               {"owner_id": item['source_id'], "post_id": item['post_id'],
                                                "new_vote": -1})
                        print(
                            f"➕ Записи https://vk.com/wall{item['source_id']}_{item['post_id']} была поставлена оценка.")
                    except ApiError:
                        print(
                            f"⛔️ Не удалось оценить запись wall{item['source_id']}_{item['post_id']}.\n\n⚙️ Делаю перерыв...\n")
                        time.sleep(random.randint(300, 900))

                    time.sleep(random.randint(int(config.sleep_time / 3), int(config.sleep_time)))
                    continue

                rate = 1

                ban = {
                    "продаю": 1, "продам": 1, "промокод": 0.5, "переходи по ссылке": 0.5, "в этой версии": 1, "игру": 0.1, "игра": 0.1,
                    "торг ": 1, "вопрос": 0.2, "продвижение": 0.75, "магазин": 0.3, "узо": 0.5, "бюджет": 0.75,
                    "читать далее": 0.45, "freelance.ru": 1, "price": 0.75, "#aliexpress": 0.65, "скидка": 0.5, "скидкой": 0.5, "скидки": 0.5,
                    "приобрести": 0.6, "сетап": 0.5, "сборка пк": 0.6, "сборка компа": 0.6, "сборка компьютера": 0.6, "продаём": 1, "продаем": 1,
                    "♂": 1, "купон": 0.5, "продавец": 0.4, "продавца": 0.4, "состояние на": 0.5, "торг.": 1, "торг,": 1, "торг!": 1, "торг:": 1, "торг;": 1,
                    "aliclick.": 1, "#appstorrent": 0.6
                }
                if len(item.get('text')) > 0:
                    for b in ban.keys():
                        if str(item.get('text')).lower().find(b) != -1:
                            rate -= ban[b]

                if len(item.get('text')) <= 120:
                    if item.get('attachments') is None:
                        rate -= len(item.get('text')) // 25
                    else:
                        rate -= len(item.get('text')) // 50

                if item.get('attachments') is not None:
                    for attach in item.get('attachments'):
                        _type = attach.get('type')
                        if attach.get(_type) is not None:
                            if attach.get(_type).get('caption') in ["aliexpress.ru", "youla.ru"]:
                                rate -= 1
                        elif _type == "article":
                            rate += 0.6

                group = [group for group in result.get('groups') if group.get('id') == item.get('source_id')]
                if len(group) >= 1:
                    group = group[0]
                    ban_names = [
                        "барохолка", "продам", "куплю", "продажа", "покупка", "объявления", "частная группа"
                    ]

                    for ban_name in ban_names:
                        if str(group.get('name')).lower().find(ban_name) != -1:
                            rate -= 1

                    if group.get('verified') == 1:
                        rate += 1

                try:
                    if rate >= 0.5:
                        self.vk_session.method("newsfeed.setPostVote",
                                               {"owner_id": item['source_id'], "post_id": item['post_id'],
                                                "new_vote": 1})
                        print(
                            f"✅ Была положительно оценена запись https://vk.com/wall{item['source_id']}_{item['post_id']}. ({rate})")
                    else:
                        self.vk_session.method("newsfeed.setPostVote",
                                               {"owner_id": item['source_id'], "post_id": item['post_id'],
                                                "new_vote": -1})
                        print(
                            f"🚷 Была отрицательно оценена запись https://vk.com/wall{item['source_id']}_{item['post_id']}. ({rate})")
                except ApiError:
                    print(
                        f"⛔️ Не удалось оценить запись wall{item['source_id']}_{item['post_id']}. ({rate})\n\n⚙️ Делаю перерыв...\n")
                    time.sleep(random.randint(300, 900))

                time.sleep(random.randint(int(config.sleep_time/3), int(config.sleep_time)))

            start_from = result.get('next_from')


Main()
