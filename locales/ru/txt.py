RU: dict[str, str] = {
    "/start": (
        "Привет!\n\n"
        "Я бот для записи к мастеру.\n\n"
        "Доступные команды:\n"
        "/book — записаться\n"
        "/help — справка\n"
        "/lang — язык интерфейса"
    ),
    "/help": (
        "Я помогаю записаться на услугу и управлять визитами.\n\n"
        "Команды:\n"
        "/start — перезапуск бота\n"
        "/book — записаться к мастеру\n"
        "/lang — язык интерфейса\n"
        "/help — эта справка"
    ),
    "/help_admin": (
        "Вы администратор бота.\n\n"
        "Команды:\n"
        "/start — перезапуск бота\n"
        "/book — записаться к мастеру\n"
        "/lang — язык интерфейса\n"
        "/help — эта справка"
    ),
    "/lang": "Выберите язык",
    "unsupported_message": "Этот тип сообщений бот пока не обрабатывает.",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 Английский",
    "save_lang_button_text": "✅ Сохранить",
    "cancel_lang_button_text": "Отмена",
    "lang_saved": (
        "Язык сохранён и будет использоваться в интерфейсе бота.\n\n"
        "Можете отправить /help"
    ),
    "lang_cancelled": (
        "Хорошо, ваш язык по-прежнему: {}.\n\n"
        "Можете отправить /help"
    ),
    "/start_description": "Перезапустить бота",
    "/lang_description": "Настроить язык интерфейса",
    "/help_description": "Посмотреть справку",
    "/book": "Выберите услугу",
    "/book_description": "Записаться к мастеру",
    "book_choose_service": "Выберите услугу",
    "book_choose_day": "Выберите день",
    "book_choose_slot": "Выберите время",
    "book_confirm": (
        "Проверьте запись:\n\n"
        "Услуга: {title}\n"
        "Дата и время проведения: {when}\n"
        "Длительность: {duration} мин\n"
        "Цена: {price}"
    ),
    "book_price_empty": "уточняется",
    "book_ok": "Вы записаны. Статус: ожидает подтверждения мастера.",
    "book_cancelled": "Запись отменена.",
    "book_no_services": "Сейчас нет доступных услуг.",
    "book_no_slots": "Нет свободных слотов. Выберите другой день или услугу.",
    "book_use_buttons": "Выберите вариант кнопками ниже.",
    "book_back_button": "← Назад",
    "book_cancel_button": "Отмена",
    "book_confirm_button": "Записаться",
    "service_button": "{title} · {duration} мин",
    "book_slot_taken": "Этот слот уже занят. Выберите другое время.",
    "book_slot_past": "Это время уже прошло.",
    "book_slot_not_found": "Слот не найден.",
    "book_service_inactive": "Услуга больше недоступна.",
    "book_service_not_found": "Услуга не найдена.",
    "book_mismatch": "Нельзя записаться на этот слот с выбранной услугой.",
    "book_need_start": "Сначала отправьте /start",
    "/today_description": "Записи на сегодня",
    "master_today_header": "📅 Записи на сегодня:",
    "master_today_empty": "На сегодня записей нет.",
    "master_today_item": "{time} — {title} ({status})\nКлиент: {client_id}",
    "master_status_pending": "ожидает",
    "master_status_confirmed": "подтверждена",
    "master_status_cancelled": "отменена",
    "master_confirm_button": "✅ Подтвердить",
    "master_cancel_button": "❌ Отменить",
    "master_confirmed": "Запись #{id} подтверждена.",
    "master_cancelled": "Запись #{id} отменена.",
    "master_action_failed": "Не удалось выполнить действие.",
    "master_close_button": "Закрыть",
}