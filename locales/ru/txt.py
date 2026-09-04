RU: dict[str, str] = {
    "/start": (
        "Привет!\n\n"
        "Я бот для записи к мастеру.\n\n"
        "Доступные команды:\n"
        "/book — записаться\n"
        "/my_bookings — мои записи\n"
        "/help — справка\n"
        "/lang — язык интерфейса"
    ),
    "/start_master": (
        "Привет!\n\n"
        "Вы вошли как мастер.\n\n"
        "Команды:\n"
        "/today — записи на сегодня\n"
        "/add_slot — добавить слот\n"
        "/services — мои услуги\n"
        "/add_service — добавить услугу\n"
        "/lang — язык интерфейса\n"
        "/help — справка"
    ),
    "/start_admin": (
        "Привет!\n\n"
        "Вы администратор бота.\n\n"
        "Команды:\n"
        "/book — записаться\n"
        "/my_bookings — мои записи\n"
        "/user — карточка пользователя\n"
        "/set_role — изменить роль\n"
        "/ban — забанить\n"
        "/unban — разбанить\n"
        "/lang — язык интерфейса\n"
        "/help — справка"
    ),
    "/help": (
        "Я помогаю записаться на услугу и управлять визитами.\n\n"
        "Команды:\n"
        "/start — перезапуск бота\n"
        "/book — записаться к мастеру\n"
        "/my_bookings — мои записи\n"
        "/lang — язык интерфейса\n"
        "/help — эта справка"
    ),
    "/help_master": (
        "Вы мастер. Управление записью:\n\n"
        "/today — записи на сегодня (подтвердить / отменить)\n"
        "/add_slot — добавить свободный слот\n"
        "/services — список услуг\n"
        "/add_service — добавить услугу\n"
        "/lang — язык интерфейса\n"
        "/help — эта справка"
    ),
    "/help_admin": (
        "Вы администратор бота.\n\n"
        "Команды:\n"
        "/start — перезапуск бота\n"
        "/book — записаться к мастеру\n"
        "/my_bookings — мои записи\n"
        "/user <id> — карточка пользователя\n"
        "/set_role <id> <роль> — изменить роль\n"
        "/ban <id> — забанить\n"
        "/unban <id> — разбанить\n"
        "/lang — язык интерфейса\n"
        "/help — эта справка"
    ),
    "client_booking_confirmed": (
        "Ваша запись подтверждена.\n\n"
        "Услуга: {title}\n"
        "Когда: {when}"
    ),
    "client_booking_cancelled_by_master": (
        "Мастер отменил вашу запись.\n\n"
        "Услуга: {title}\n"
        "Когда: {when}"
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
    "status_pending": "ожидает",
    "status_confirmed": "подтверждена",
    "status_cancelled": "отменена",
    "master_confirm_button": "✅ Подтвердить",
    "master_cancel_button": "❌ Отменить",
    "master_confirmed": "Запись #{id} подтверждена.",
    "master_cancelled": "Запись #{id} отменена.",
    "master_action_failed": "Не удалось выполнить действие.",
    "master_close_button": "Закрыть",
    "master_new_booking": (
        "🔔 Новая запись\n\n"
        "Услуга: {title}\n"
        "Когда: {when}\n"
        "Клиент: {client_id}\n\n"
        "Записи на сегодня: /today"
    ),
    "/add_slot_description": "Добавить слот",
    "add_slot_enter_date": (
        "Введите дату слота в формате ДД.ММ.ГГГГ\n"
        "Например: 05.09.2026\n\n"
        "Отмена: /cancel"
    ),
    "add_slot_enter_time": (
        "Введите время начала в формате ЧЧ:ММ\n"
        "Например: 14:30\n\n"
        "Отмена: /cancel"
    ),
    "add_slot_enter_duration": (
        "Введите длительность слота в минутах\n"
        "Например: 60\n\n"
        "Отмена: /cancel"
    ),
    "add_slot_invalid_date": "Неверный формат даты. Используйте ДД.ММ.ГГГГ",
    "add_slot_invalid_time": "Неверный формат времени. Используйте ЧЧ:ММ",
    "add_slot_invalid_duration": "Введите целое число минут больше 0",
    "add_slot_past": "Нельзя создать слот в прошлом. Введите другую дату или время.",
    "add_slot_duplicate": "Слот на это время уже существует.",
    "add_slot_ok": "Слот создан: {when}, длительность {duration} мин.",
    "add_slot_cancelled": "Добавление слота отменено.",
    "/services_description": "Мои услуги",
    "services_list_header": "📋 Ваши услуги:",
    "services_list_item": "• {title} — {duration} мин, {price} ({status})",
    "services_price_empty": "цена уточняется",
    "services_status_active": "активна",
    "services_status_inactive": "неактивна",
    "services_empty": (
        "У вас пока нет услуг.\n\n"
        "Добавить: /add_service"
    ),
    "services_add_hint": "Добавить услугу: /add_service",
    "add_service_enter_title": (
        "Введите название услуги\n"
        "Например: Маникюр\n\n"
        "Отмена: /cancel"
    ),
    "add_service_enter_duration": (
        "Введите длительность в минутах\n"
        "Например: 60\n\n"
        "Отмена: /cancel"
    ),
    "add_service_enter_price": (
        "Введите цену (число) или «-» без цены\n"
        "Например: 1500 или 1500.50\n\n"
        "Отмена: /cancel"
    ),
    "add_service_invalid_title": "Название не должно быть пустым (макс. 100 символов).",
    "add_service_invalid_duration": "Введите целое число минут больше 0.",
    "add_service_invalid_price": "Неверный формат цены. Число или «-».",
    "add_service_ok": "Услуга добавлена: {title}, {duration} мин, {price}.",
    "add_service_cancelled": "Добавление услуги отменено.",
    "/add_service_description": "Добавить услугу",
    "book_slot_too_short": "Этот слот короче длительности услуги. Выберите другое время.",
    "/my_bookings_description": "Мои записи",
    "my_bookings_header": "🗓 Ваши записи:",
    "my_bookings_empty": (
        "У вас нет активных записей.\n\n"
        "Записаться: /book"
    ),
    "my_bookings_item": "{when} — {title} ({status})",
    "my_bookings_cancel_button": "❌ Отменить запись",
    "my_bookings_close_button": "Закрыть",
    "my_bookings_cancelled": "Запись отменена.",
    "my_bookings_action_failed": "Не удалось отменить запись.",
    "master_booking_cancelled_by_client": (
        "Клиент отменил запись.\n\n"
        "Услуга: {title}\n"
        "Когда: {when}\n"
        "Клиент: {client_id}"
    ),
    "/user_description": "Карточка пользователя",
    "/set_role_description": "Изменить роль",
    "/ban_description": "Забанить",
    "/unban_description": "Разбанить",
    "admin_usage_user": "Использование: /user <user_id>",
    "admin_usage_ban": "Использование: /ban <user_id>",
    "admin_usage_unban": "Использование: /unban <user_id>",
    "admin_usage_set_role": "Использование: /set_role <user_id> <роль>",
    "admin_user_not_found": "Пользователь {user_id} не найден.",
    "admin_user_card": (
        "👤 Пользователь {user_id}\n\n"
        "Username: {username}\n"
        "Роль: {role}\n"
        "Язык: {language}\n"
        "Забанен: {banned}\n"
        "Регистрация: {created_at}"
    ),
    "admin_no_username": "не указан",
    "admin_yes": "да",
    "admin_no": "нет",
    "admin_ban_self": "Нельзя забанить самого себя.",
    "admin_ban_staff": "Нельзя забанить администратора или мастера.",
    "admin_already_banned": "Пользователь {user_id} уже забанен.",
    "admin_not_banned": "Пользователь {user_id} не забанен.",
    "admin_banned": "Пользователь {user_id} забанен.",
    "admin_unbanned": "Пользователь {user_id} разбанен.",
    "admin_invalid_role": "Неизвестная роль. Доступные: {roles}",
    "admin_demote_self": "Нельзя снять с себя роль администратора.",
    "admin_role_unchanged": "У пользователя {user_id} уже роль {role}.",
    "admin_role_set": "Пользователю {user_id} установлена роль {role}.",
    "admin_role_changed_notice": "Ваша роль изменена на {role}.",
}
