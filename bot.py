import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
from threading import Thread
import json
import os
import urllib.parse
# Токен бота
TOKEN = "8132157647:AAEKgebdk_Q86DZdbPFncwYqhj7YHmrKj20"

# ID администраторов
ADMIN_IDS = [1376242458]

# Начальные пары и их курсы

# Структуры для хранения данных
user_data = {}
exchange_requests = []

# Создаем объект бота
bot = telebot.TeleBot(TOKEN)

# Файлы для хранения данных
ADMINS_FILE = "admins.json"
PAIRS_FILE = "pairs.json"
NETWORKS_FILE = "networks.json"
EXCHANGE_REQUESTS_FILE = "exchange_requests.json"
CASHOUT_REQUESTS_FILE = "cashout_requests.json"

MAIN_ADMIN_ID = 123456789  # замените на свой ID

def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []  # Возвращаем пустой список, если файл не найден
def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
# Загружаем данные о парах и сетях из файлов
PAIRS = load_json(PAIRS_FILE)
NETWORKS = load_json(NETWORKS_FILE)

# Проверка загрузки данных
print("Загруженные пары:", PAIRS)
print("Загруженные сети:", NETWORKS)

# Пример функции для получения списка торговых пар
def get_trading_pairs():
    """Возвращает список торговых пар."""
    return list(PAIRS.keys())


# Функция для получения списка торговых символов с Binance
def get_binance_symbols():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    symbols = []
    for symbol in data['symbols']:
        if symbol['status'] == 'TRADING' and symbol['isSpotTradingAllowed']:
            symbols.append(symbol['symbol'])
    return symbols

# Функция для получения курса с Binance
def fetch_binance_price(pair):
    try:
        symbol = pair.replace("/", "")
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
        response = requests.get(url)
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Ошибка при получении курса: {e}")
        return PAIRS.get(pair, 0)

# Функция для обновления курсов каждые 10 минут
def update_exchange_rates():
    while True:
        for pair in PAIRS.keys():
            new_price = fetch_binance_price(pair)
            PAIRS[pair] = new_price
            print(f"Обновленный курс для {pair}: {new_price}")
        time.sleep(600)  # обновляем курс каждые 10 минут

# Запускаем обновление курсов в отдельном потоке
Thread(target=update_exchange_rates, daemon=True).start()
@bot.message_handler(commands=["admin"])
def admin_command(message):
    if message.chat.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "🛠 Админ-панель:", reply_markup=get_admin_panel())
    else:
        bot.send_message(message.chat.id, "🚫 У вас нет доступа к этой команде.")

# Функция генерации админ-панели
def get_admin_panel():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 Добавить админа", callback_data="add_admin"),
        InlineKeyboardButton("❌ Удалить админа", callback_data="remove_admin"),
        InlineKeyboardButton("📋 Список админов", callback_data="list_admins")
    )
    markup.add(
        InlineKeyboardButton("➕ Добавить адрес", callback_data="add_wallet"),
        InlineKeyboardButton("➖ Удалить адрес", callback_data="remove_wallet"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats")
    )
    # Добавляем кнопку "🏠 На главную" в конце
    markup.add(InlineKeyboardButton("🏠 На главную", callback_data="back_to_main"))

    return markup



# Команда /admin — вход в админ-панель
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    user_id = str(message.from_user.id)
    admins = load_json(ADMINS_FILE)

    if user_id in admins or user_id == str(ADMIN_IDS[0]):
        bot.send_message(message.chat.id, "🔧 <b>Админ-панель:</b>", reply_markup=get_admin_panel(), parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа.")




# Обработка кнопки "📋 Список админов"
@bot.callback_query_handler(func=lambda call: call.data == "list_admins")
def list_admins(call):
    admins = load_json(ADMINS_FILE)
    text = "📃 <b>Список администраторов:</b>\n"
    for i, admin_id in enumerate(admins, 1):
        text += f"{i}. <code>{admin_id}</code>\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          parse_mode="HTML", reply_markup=get_admin_panel())

# Обработка кнопки "👤 Добавить админа"
@bot.callback_query_handler(func=lambda call: call.data == "add_admin")
def add_admin_request(call):
    bot.send_message(call.message.chat.id, "Введите ID пользователя, которого нужно сделать администратором:")
    bot.register_next_step_handler(call.message, add_admin_process)

def add_admin_process(message):
    user_id = str(message.text).strip()
    admins = load_json(ADMINS_FILE)

    if user_id in admins:
        bot.send_message(message.chat.id, "⚠️ Этот пользователь уже является админом.", reply_markup=get_admin_panel())
    else:
        admins.append(user_id)
        save_json(ADMINS_FILE, admins)
        bot.send_message(message.chat.id, f"✅ Пользователь <code>{user_id}</code> добавлен в админы.",
                         parse_mode="HTML", reply_markup=get_admin_panel())

# Обработка кнопки "❌ Удалить админа"
@bot.callback_query_handler(func=lambda call: call.data == "remove_admin")
def remove_admin_request(call):
    bot.send_message(call.message.chat.id, "Введите ID администратора, которого нужно удалить:")
    bot.register_next_step_handler(call.message, remove_admin_process)

def remove_admin_process(message):
    user_id = str(message.text).strip()
    admins = load_json(ADMINS_FILE)

    if user_id in admins:
        admins.remove(user_id)
        save_json(ADMINS_FILE, admins)
        bot.send_message(message.chat.id, f"✅ Админ <code>{user_id}</code> удалён.",
                         parse_mode="HTML", reply_markup=get_admin_panel())
    else:
        bot.send_message(message.chat.id, "❌ Этот пользователь не является админом.", reply_markup=get_admin_panel())


# Начало удаления — выбор пары
@bot.callback_query_handler(func=lambda call: call.data == "remove_wallet")
def remove_wallet_start(call):
    user_data[call.message.chat.id] = {"step": "remove_pair"}

    # Создаем объект markup для клавиатуры
    markup = InlineKeyboardMarkup()

    # Добавляем кнопки для выбора пар
    for pair in PAIRS.keys():
        markup.add(InlineKeyboardButton(pair, callback_data=f"remove_pair_{pair}"))

    # Добавляем кнопку "Назад"
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))

    # Отправляем сообщение с клавиатурой
    bot.edit_message_text("Выберите торговую пару для удаления адреса:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# Выбор сети после пары
@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_pair_"))
def remove_wallet_network(call):
    pair = call.data.split("remove_pair_")[1]
    user_data[call.message.chat.id] = {"pair": pair, "step": "remove_network_wallet"}
    
    wallets = load_json("wallets.json")
    networks = wallets.get(pair, {}).keys()

    if not networks:
        bot.send_message(call.message.chat.id, f"❌ Для пары {pair} нет адресов.", reply_markup=get_admin_panel())
        return

    markup = InlineKeyboardMarkup()
    for network in networks:
        markup.add(InlineKeyboardButton(network, callback_data=f"remove_network_{network}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="remove_wallet"))
    bot.edit_message_text(f"Выберите сеть для <b>{pair}</b>:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")


# Выбор адреса для удаления
@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_network_"))
def remove_wallet_address(call):
    network = call.data.split("remove_network_")[1]
    chat_id = call.message.chat.id

    if "pair" not in user_data.get(chat_id, {}):
        bot.send_message(chat_id, "❌ Ошибка. Сначала выберите торговую пару.", reply_markup=get_admin_panel())
        return

    pair = user_data[chat_id]["pair"]
    user_data[chat_id]["network"] = network  # 🛠 Сохраняем сеть!

    wallets = load_json("wallets.json")

    if pair in wallets and network in wallets[pair]:
        addresses = wallets[pair][network]
        if not addresses:
            bot.send_message(chat_id, f"❌ Адресов для {pair} ({network}) не найдено.", reply_markup=get_admin_panel())
            return

        markup = InlineKeyboardMarkup()
        for i, address in enumerate(addresses, 1):
            encoded = urllib.parse.quote(address)
            # Кнопки с номером адреса для выбора
            markup.add(InlineKeyboardButton(f"Адрес {i}: {address}", callback_data=f"remove_address_{encoded}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="remove_wallet"))

        bot.send_message(chat_id, f"Выберите адрес для удаления из <b>{pair} ({network})</b>:", parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"❌ Адреса для <b>{pair} ({network})</b> не найдены.", parse_mode="HTML", reply_markup=get_admin_panel())

# Удаление адреса
@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_address_"))
def confirm_delete_address(call):
    chat_id = call.message.chat.id
    address = urllib.parse.unquote(call.data.split("remove_address_")[1])

    data = user_data.get(chat_id, {})
    pair = data.get("pair")
    network = data.get("network")

    wallets = load_json("wallets.json")

    if pair and network and address in wallets.get(pair, {}).get(network, []):
        wallets[pair][network].remove(address)

        if not wallets[pair][network]:
            del wallets[pair][network]

        if not wallets[pair]:
            del wallets[pair]

        save_json("wallets.json", wallets)
        # Отправляем только адрес, без скобок
        bot.send_message(chat_id, f"✅ Адрес {address} из <b>{pair} ({network})</b> удалён.", parse_mode="HTML", reply_markup=get_admin_panel())
    else:
        bot.send_message(chat_id, "❌ Адрес не найден.", reply_markup=get_admin_panel())

    user_data.pop(chat_id, None)



@bot.callback_query_handler(func=lambda call: call.data == "add_wallet")
def add_wallet_start(call):
    user_data[call.message.chat.id] = {"step": "choose_pair_wallet"}
    markup = InlineKeyboardMarkup()
    for pair in PAIRS.keys():
        markup.add(InlineKeyboardButton(pair, callback_data=f"wallet_pair_{pair}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text("🔁 Выберите торговую пару:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("wallet_pair_"))
def choose_wallet_network(call):
    pair = call.data.split("wallet_pair_")[1]
    user_data[call.message.chat.id] = {"pair": pair, "step": "choose_network_wallet"}

    networks = NETWORKS.get(pair, [])
    if not networks:
        bot.send_message(call.message.chat.id, "❌ Для этой пары нет сетей. Сначала настройте их.")
        return

    markup = InlineKeyboardMarkup()
    for network in networks:
        markup.add(InlineKeyboardButton(network, callback_data=f"wallet_network_{network}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="add_wallet"))
    bot.edit_message_text(f"🌐 Выберите сеть для пары <b>{pair}</b>:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wallet_network_"))
def ask_wallet_address(call):
    network = call.data.split("wallet_network_")[1]
    if call.message.chat.id not in user_data or "pair" not in user_data[call.message.chat.id]:
        bot.send_message(call.message.chat.id, "⚠️ Ошибка. Начните сначала.", reply_markup=get_admin_panel())
        return

    user_data[call.message.chat.id]["network"] = network
    bot.send_message(
        call.message.chat.id,
        f"💳 Введите адрес кошелька для <b>{user_data[call.message.chat.id]['pair']} ({network})</b>:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(call.message, save_wallet_address)

def save_wallet_address(message):
    chat_id = message.chat.id
    address = message.text.strip()
    data = user_data.get(chat_id, {})
    pair = data.get("pair")
    network = data.get("network")

    if not pair or not network or not address:
        bot.send_message(chat_id, "❌ Неверные данные. Повторите добавление.", reply_markup=get_admin_panel())
        return

    wallets = load_json("wallets.json")
    wallets.setdefault(pair, {}).setdefault(network, [])

    if address in wallets[pair][network]:
        bot.send_message(chat_id, "⚠️ Этот адрес уже добавлен.", reply_markup=get_admin_panel())
    else:
        wallets[pair][network].append(address)
        save_json("wallets.json", wallets)

        bot.send_message(
            chat_id,
            f"✅ Адрес для <b>{pair} ({network})</b> сохранён:\n<code>{address}</code>",
            parse_mode="HTML",
            reply_markup=get_admin_panel()
        )

    user_data.pop(chat_id, None)


@bot.callback_query_handler(func=lambda call: call.data == "add_admin")
def start_add_admin(call):
    user_data[call.message.chat.id] = {"step": "waiting_for_admin_id"}
    bot.send_message(call.message.chat.id, "Введите <b>ID пользователя</b>, которого хотите добавить в админы:", parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get("step") == "waiting_for_admin_id")
def process_add_admin(message):
    try:
        new_admin_id = str(int(message.text.strip()))  # проверка на число
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат ID. Введите числовой ID.")
        return

    admins = load_json(ADMINS_FILE)
    if new_admin_id in admins:
        bot.send_message(message.chat.id, "⚠️ Этот ID уже есть в списке админов.")
    else:
        admins.append(new_admin_id)
        save_json(ADMINS_FILE, admins)
        bot.send_message(message.chat.id, f"✅ <b>ID {new_admin_id}</b> добавлен в список администраторов.", parse_mode="HTML")

    user_data.pop(message.chat.id, None)




@bot.callback_query_handler(func=lambda call: call.data == "remove_admin")
def start_remove_admin(call):
    admins = load_json(ADMINS_FILE)

    if not admins:
        bot.answer_callback_query(call.id, "Нет администраторов для удаления.")
        return

    markup = InlineKeyboardMarkup()
    for admin_id in admins:
        markup.add(InlineKeyboardButton(f"Удалить {admin_id}", callback_data=f"remove_admin_id_{admin_id}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))

    bot.edit_message_text("Выберите ID администратора для удаления:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_admin_id_"))
def confirm_remove_admin(call):
    remove_id = call.data.split("remove_admin_id_")[1]
    admins = load_json(ADMINS_FILE)

    if remove_id in admins:
        admins.remove(remove_id)
        save_json(ADMINS_FILE, admins)
        bot.answer_callback_query(call.id, f"✅ ID {remove_id} удалён из админов.")
        bot.edit_message_text(f"ID <b>{remove_id}</b> удалён из списка администраторов.", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_panel())
    else:
        bot.answer_callback_query(call.id, "❌ ID не найден в списке.")

# Обработка кнопки "Назад" в админ-панели
@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def back_to_admin(call):
    # Передаем chat_id и message_id из сообщения
    back_to_admin_panel(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    # Создаем главное меню
    main_markup = InlineKeyboardMarkup(row_width=2)
    main_markup.add(
        InlineKeyboardButton("💱 Обмен", callback_data="exchange"),
        InlineKeyboardButton("💵 Обнал", callback_data="cashout")
    )
    # Отправляем главное меню пользователю
    bot.edit_message_text("Выберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_markup)






@bot.callback_query_handler(func=lambda call: call.data == "stats")
def show_stats(call):
    exchange_data = load_json(EXCHANGE_REQUESTS_FILE)
    cashout_data = load_json(CASHOUT_REQUESTS_FILE)

    exchange_count = len(exchange_data) if isinstance(exchange_data, list) else 0
    cashout_count = len(cashout_data) if isinstance(cashout_data, list) else 0

    wallets = load_json("wallets.json")
    wallet_count = sum(len(networks) for pair, networks in wallets.items())

    stats_text = (
        "<b>📊 Статистика</b>\n\n"
        f"🔁 Обменов всего: <b>{exchange_count}</b>\n"
        f"💵 Обналичиваний всего: <b>{cashout_count}</b>\n"
        f"💳 Адресов в базе: <b>{wallet_count}</b>\n"
    )

    bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=get_admin_panel())

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start_command(message):
    if message.chat.id in ADMIN_IDS:
        # Убираем кнопку для перехода в админ-панель
        markup = main_menu()
        bot.send_message(message.chat.id, "🏠 Добро пожаловать, администратор! Выберите действие:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "🏠 Добро пожаловать! Выберите действие:", reply_markup=main_menu())

# Главное меню
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Обмен", callback_data="exchange"))
    markup.add(InlineKeyboardButton("Обнал", callback_data="cashout"))
    return markup

# Меню обмена
def exchange_menu():
    markup = InlineKeyboardMarkup()
    for pair in PAIRS.keys():
        markup.add(InlineKeyboardButton(f"{pair} - {PAIRS[pair]} USDT", callback_data=f"pair_{pair}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    return markup

# Меню выбора сети
def network_menu(pair):
    markup = InlineKeyboardMarkup()
    for network in NETWORKS.get(pair, []):
        markup.add(InlineKeyboardButton(network, callback_data=f"network_{network}"))
    markup.add(InlineKeyboardButton("🔙 Назад в пары", callback_data="back_to_exchange"))
    return markup

# Обмен - выбор пары
@bot.callback_query_handler(func=lambda call: call.data == "exchange")
def exchange(call):
    bot.send_message(call.message.chat.id, "Выберите валютную пару:", reply_markup=exchange_menu())

# Обмен - выбор сети
@bot.callback_query_handler(func=lambda call: call.data.startswith("pair_"))
def select_pair(call):
    pair = call.data.split("_")[1]
    user_data[call.message.chat.id] = {"pair": pair}
    bot.send_message(call.message.chat.id, "Выберите сеть:", reply_markup=network_menu(pair))

# Обмен - возврат к выбору пары
@bot.callback_query_handler(func=lambda call: call.data == "back_to_exchange")
def back_to_exchange(call):
    bot.send_message(call.message.chat.id, "Выберите валютную пару:", reply_markup=exchange_menu())

# Обмен - получение адреса для отправки
@bot.callback_query_handler(func=lambda call: call.data.startswith("network_"))
def select_network(call):
    if call.message.chat.id not in user_data:
        bot.send_message(call.message.chat.id, "Ошибка! Начните заново.", reply_markup=main_menu())
        return

    network = call.data.split("_", 1)[1]
    user_data[call.message.chat.id]["network"] = network

    pair = user_data[call.message.chat.id]["pair"]
    wallets = load_json("wallets.json")
    addresses = wallets.get(pair, {}).get(network)

    if not addresses:
        bot.send_message(call.message.chat.id, "⚠️ Для выбранной пары и сети адрес не найден. Обратитесь в поддержку или выберите другую пару.", reply_markup=main_menu())
        return

    # Если один адрес — отправляем сразу
    if isinstance(addresses, str):
        address_list = [addresses]
    else:
        address_list = addresses

    if len(address_list) == 1:
        send_wallet_and_confirm(call.message.chat.id, address_list[0])
    else:
        markup = InlineKeyboardMarkup()
        for idx, addr in enumerate(address_list):
            markup.add(InlineKeyboardButton(f"Адрес {idx+1}", callback_data=f"choose_address_{idx}"))
        bot.send_message(call.message.chat.id, "Выберите адрес для перевода:", reply_markup=markup)

    # Сохраняем список в user_data
    user_data[call.message.chat.id]["addresses"] = address_list
@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_address_"))
def choose_address(call):
    index = int(call.data.split("_")[2])
    addresses = user_data.get(call.message.chat.id, {}).get("addresses", [])
    
    if 0 <= index < len(addresses):
        send_wallet_and_confirm(call.message.chat.id, addresses[index])
    else:
        bot.send_message(call.message.chat.id, "Ошибка выбора адреса.")
def send_wallet_and_confirm(chat_id, address):
    bot.send_message(
        chat_id,
        f"Отправьте средства на адрес:\n<code>{address}</code>\nПосле отправки нажмите '✅ Подтвердить'",
        parse_mode="HTML"
    )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_exchange"))
    markup.add(InlineKeyboardButton("🔙 Назад в пары", callback_data="back_to_exchange"))
    bot.send_message(chat_id, "Ожидаю подтверждения...", reply_markup=markup)

# Обмен - подтверждение отправки
@bot.callback_query_handler(func=lambda call: call.data == "confirm_exchange")
def confirm_exchange(call):
    bot.send_message(call.message.chat.id, "Введите ваш кошелек для получения средств:")
    bot.register_next_step_handler(call.message, get_wallet_address)

# Обмен - получение кошелька
def get_wallet_address(message):
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "Ошибка! Начните заново.", reply_markup=main_menu())
        return

    # Проверяем, не нажал ли пользователь кнопку "🔙 Назад в пары"
    if message.text == "🔙 Назад в пары":
        bot.send_message(message.chat.id, "Выберите валютную пару:", reply_markup=exchange_menu())
        return

    user_data[message.chat.id]["wallet"] = message.text
    bot.send_message(message.chat.id, "✅ Адрес получен, ожидайте в течение 10 минут.", reply_markup=main_menu())

    # Формируем сообщение для админов
    username = f"@{message.from_user.username}" if message.from_user.username else "❌ Нет username"
    admin_msg = (f"📌 <b>Новая заявка на обмен!</b>\n"
                 f"🔹 <b>Пара:</b> {user_data[message.chat.id]['pair']}\n"
                 f"🔹 <b>Сеть:</b> {user_data[message.chat.id]['network']}\n"
                 f"🔹 <b>Кошелек пользователя:</b> <code>{message.text}</code>\n"
                 f"👤 <b>Пользователь:</b> {username}\n"
                 f"🆔 <b>User ID:</b> <code>{message.chat.id}</code>\n"
                 f"🔗 <a href='tg://user?id={message.chat.id}'>Связаться</a>")

    for admin in ADMIN_IDS:
        bot.send_message(admin, admin_msg, parse_mode="HTML")

# Меню обнала
def cashout_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💵 Вывести наличные", callback_data="cashout"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    return markup

# Обнал - главное меню
@bot.callback_query_handler(func=lambda call: call.data == "cashout")
def cashout(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    markup.add(InlineKeyboardButton("💰 Ввести сумму", callback_data="enter_cashout_amount"))
    bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)

# Обнал - ввод суммы
@bot.callback_query_handler(func=lambda call: call.data == "enter_cashout_amount")
def ask_for_amount(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    bot.send_message(call.message.chat.id, "Введите сумму для обнала:", reply_markup=markup)
    bot.register_next_step_handler(call.message, get_cashout_amount)

# Обнал - получение суммы
def get_cashout_amount(message):
    if message.text == "🔙 Назад":
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu())
        return  # Выход из функции

    try:
        amount = float(message.text)
        
        # Сохраняем сумму в данных пользователя
        user_data[message.chat.id] = {"cashout_amount": amount}

        bot.send_message(message.chat.id, "✅ Заявка на обнал отправлена. Ожидайте связи с администратором.", reply_markup=main_menu())

        username = f"@{message.from_user.username}" if message.from_user.username else "❌ Нет username"
        admin_msg = (f"📌 <b>Новая заявка на обнал!</b>\n"
                     f"🔹 <b>Сумма:</b> {amount} USDT\n"
                     f"👤 <b>Пользователь:</b> {username}\n"
                     f"🆔 <b>User ID:</b> <code>{message.chat.id}</code>\n"
                     f"🔗 <a href='tg://user?id={message.chat.id}'>Связаться</a>")

        # Отправляем сообщение всем админам
        for admin in ADMIN_IDS:
            bot.send_message(admin, admin_msg, parse_mode="HTML")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите корректную сумму.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")))
        bot.register_next_step_handler(message, get_cashout_amount)


bot.polling()
