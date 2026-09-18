RU: dict[str, str] = {
    "/start": (
        "Привет!\n\n"
        "Я бот для записи к мастеру.\n\n"
        "Доступные команды:\n"
        "/profile - авторизация\n"
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
        "/schedule — недельный график\n"
        "/time_off — выходные / отсутствие\n"
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
        "/profile - авторизация\n"
        "/book — записаться к мастеру\n"
        "/my_bookings — мои записи\n"
        "/lang — язык интерфейса\n"
        "/help — эта справка"
    ),
    "/help_master": (
        "Вы мастер. Управление записью:\n\n"
        "/today — записи на сегодня (подтвердить / отменить)\n"
        "/schedule — недельный график\n"
        "/time_off — выходные и отсутствие\n"
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
        "/user &lt;id|@username&gt; — карточка пользователя\n"
        "/set_role &lt;id|@username&gt; &lt;роль&gt; — изменить роль\n"
        "/ban &lt;id|@username&gt; — забанить\n"
        "/unban &lt;id|@username&gt; — разбанить\n"
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
    "book_choose_window": "Выберите время",
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
    "book_no_windows": "Нет свободного времени. Выберите другой день или услугу.",
    "book_use_buttons": "Выберите вариант кнопками ниже.",
    "book_back_button": "← Назад",
    "book_cancel_button": "Отмена",
    "book_confirm_button": "Записаться",
    "service_button": "{title} · {duration} мин",
    "book_window_taken": "Это время уже занято. Выберите другое.",
    "book_window_not_found": "Это время больше недоступно.",
    "book_service_inactive": "Услуга больше недоступна.",
    "book_service_not_found": "Услуга не найдена.",
    "book_need_start": "Сначала отправьте /start",
    "/today_description": "Записи на сегодня",
    "master_today_header": "📅 Записи на сегодня:",
    "master_today_empty": "На сегодня записей нет.",
    "master_today_item": (
        "{time} — {title} ({status})\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}"
    ),
    "master_today_item_past": (
        "{time} — {title} ({status})\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}\n"
        "✓ Время записи уже прошло"
    ),
    "status_pending": "ожидает",
    "status_confirmed": "подтверждена",
    "status_cancelled": "отменена",
    "master_confirm_button": "✅ Подтвердить",
    "master_cancel_button": "❌ Отменить",
    "master_confirmed": "Запись #{id} подтверждена.",
    "master_cancelled": "Запись #{id} отменена.",
    "master_action_failed": "Не удалось выполнить действие.",
    "master_close_button": "Закрыть",
    "master_action_past": "Нельзя изменить запись: время уже прошло.",
    "master_new_booking": (
        "🔔 Новая запись\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}\n\n"
        "Записи на сегодня: /today"
    ),
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
        "Дата и время: {when}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}"
    ),
    "/user_description": "Карточка пользователя",
    "/set_role_description": "Изменить роль",
    "/ban_description": "Забанить",
    "/unban_description": "Разбанить",
    "admin_usage_user": "Использование: /user &lt;id|@username&gt;",
    "admin_usage_ban": "Использование: /ban &lt;id|@username&gt;",
    "admin_usage_unban": "Использование: /unban &lt;id|@username&gt;",
    "admin_usage_set_role": "Использование: /set_role &lt;id|@username&gt; &lt;роль&gt;",
    "admin_user_not_found": "Пользователь {target} не найден.",
    "admin_user_card": (
        "👤 Пользователь {user_id}\n\n"
        "Username: {username}\n"
        "Имя: {first_name}\n"
        "Фамилия: {last_name}\n"
        "Телефон: {phone}\n"
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
    "/profile_description": "Мой профиль",
    "profile_ask_first_name": "Как вас зовут? (имя)",
    "profile_ask_last_name": "Ваша фамилия?",
    "profile_ask_phone": (
        "Укажите телефон для связи.\n"
        "Можно нажать кнопку ниже или ввести номер вручную (+7...)."
    ),
    "profile_share_phone_button": "📱 Отправить телефон",
    "profile_invalid_name": "Слишком короткое значение. Введите ещё раз.",
    "profile_invalid_phone": (
        "Не удалось распознать номер. "
        "Отправьте контакт кнопкой или номер в формате +79001234567."
    ),
    "profile_saved": "Профиль сохранён.",
    "profile_saved_continue_book": "Теперь можно записаться: /book",
    "profile_cancelled": "Заполнение профиля отменено.",
    "profile_card": (
        "Ваш профиль:\n\n"
        "Имя: {first_name}\n"
        "Фамилия: {last_name}\n"
        "Телефон: {phone}"
    ),
    "profile_edit_hint": "Чтобы изменить данные, отправьте: /edit_profile",
    "/schedule_description": "Мой график",
    "schedule_header": "🗓 Ваш недельный график:",
    "schedule_list_item": "• {weekday} {starts}–{ends}",
    "schedule_empty": (
        "График ещё не задан.\n\n"
        "Добавьте интервал кнопкой ниже."
    ),
    "schedule_add_button": "➕ Добавить",
    "schedule_close_button": "Закрыть",
    "schedule_closed": "График закрыт.",
    "schedule_weekday_1": "Пн",
    "schedule_weekday_2": "Вт",
    "schedule_weekday_3": "Ср",
    "schedule_weekday_4": "Чт",
    "schedule_weekday_5": "Пт",
    "schedule_weekday_6": "Сб",
    "schedule_weekday_7": "Вс",
    "schedule_enter_starts": (
        "Введите время начала ЧЧ:ММ\n"
        "Пример: 09:00\n\n"
        "Отмена: /cancel"
    ),
    "schedule_enter_ends": (
        "Введите время окончания ЧЧ:ММ\n"
        "Пример: 18:00\n\n"
        "Отмена: /cancel"
    ),
    "schedule_choose_weekdays": (
        "Выберите дни для {starts}–{ends}.\n"
        "Нажмите день, чтобы отметить, затем «Сохранить»."
    ),
    "schedule_invalid_time": "Неверный формат времени. Используйте ЧЧ:ММ",
    "schedule_invalid_range": "Время окончания должно быть позже начала.",
    "schedule_need_weekday": "Выберите хотя бы один день.",
    "schedule_add_ok": "Добавлено: {starts}–{ends} ({days}).",
    "schedule_cancelled": "Редактирование графика отменено.",
    "schedule_save_button": "Сохранить",
    "schedule_back_button": "← Назад",
    "schedule_cancel_button": "Отмена",
    "schedule_delete_button": "🗑 {item}",
    "schedule_confirm_delete": "Удалить {item}?",
    "schedule_confirm_yes": "Да",
    "schedule_confirm_no": "Нет",
    "schedule_deleted": "Интервал удалён.",
    "schedule_delete_not_found": "Интервал не найден.",
    "/time_off_description": "Выходные / отсутствие",
    "time_off_header": "🚫 Ближайшие выходные:",
    "time_off_list_item": "• {when}{note}",
    "time_off_empty": (
        "Ближайших выходных нет.\n\n"
        "Заблокируйте дни кнопкой ниже."
    ),
    "time_off_add_button": "➕ Добавить",
    "time_off_close_button": "Закрыть",
    "time_off_closed": "Список выходных закрыт.",
}
