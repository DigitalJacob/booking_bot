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
    "status_pending": "ожидает подтверждения",
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
    "my_bookings_header": "Ваши записи:",
    "my_bookings_empty": (
        "У вас нет активных записей.\n\n"
        "Записаться можно через меню → Запись."
    ),
    "my_bookings_item": "• {weekday} {when} — {title} ({status})",
    "my_bookings_list_button": "{weekday} {when} · {title}",
    "my_bookings_card": (
        "Запись\n\n"
        "Когда: {when}\n"
        "Услуга: {title}\n"
        "Статус: {status}"
    ),
    "my_bookings_cancel_button": "Отменить запись",
    "my_bookings_back_button": "← Назад",
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
    "admin_hub_ask_target": (
        "Введите id или @username пользователя\n\n"
        "Отмена: /cancel"
    ),
    "admin_hub_ask_role": (
        "Выберите новую роль для пользователя {user_id}\n\n"
        "Отмена: /cancel"
    ),
    "admin_hub_cancelled": "Модерация отменена.",
    "admin_role_client_button": "client",
    "admin_role_master_button": "master",
    "admin_role_admin_button": "admin",
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
    "time_off_enter_starts": (
        "Введите первый день выходного ДД.ММ.ГГГГ\n"
        "Пример: 20.09.2026\n\n"
        "Отмена: /cancel"
    ),
    "time_off_enter_ends": (
        "Введите последний день выходного ДД.ММ.ГГГГ\n"
        "Та же дата = один день. Пример: 22.09.2026\n\n"
        "Отмена: /cancel"
    ),
    "time_off_invalid_date": "Неверный формат даты. Используйте ДД.ММ.ГГГГ",
    "time_off_invalid_range": "Дата окончания должна быть не раньше даты начала.",
    "time_off_add_ok": "Выходной добавлен: {when}.",
    "time_off_cancelled": "Редактирование выходных отменено.",
    "time_off_delete_button": "🗑 {item}",
    "time_off_confirm_delete": "Удалить {item}?",
    "time_off_confirm_yes": "Да",
    "time_off_confirm_no": "Нет",
    "time_off_deleted": "Выходной удалён.",
    "time_off_delete_not_found": "Выходной не найден.",
    "services_add_button": "➕ Добавить",
    "services_close_button": "Закрыть",
    "services_back_button": "← Назад",
    "services_closed": "Список услуг закрыт.",
    "services_card": (
        "{title}\n"
        "Длительность: {duration} мин\n"
        "Цена: {price}\n"
        "Статус: {status}"
    ),
    "services_not_found": "Услуга не найдена.",
    "services_deactivate_button": "⏸ Деактивировать",
    "services_activate_button": "▶️ Включить",
    "services_deactivated": "Услуга деактивирована.",
    "services_activated": "Услуга включена.",
    "services_edit_button": "✏️ Изменить",
    "edit_service_enter_title": (
        "Введите новое название\n"
        "Сейчас: {title}\n\n"
        "Отмена: /cancel"
    ),
    "edit_service_enter_duration": (
        "Введите новую длительность в минутах\n"
        "Сейчас: {duration}\n\n"
        "Отмена: /cancel"
    ),
    "edit_service_enter_price": (
        "Введите новую цену (или - чтобы очистить)\n"
        "Сейчас: {price}\n\n"
        "Отмена: /cancel"
    ),
    "edit_service_ok": "Услуга обновлена: {title}, {duration} мин, {price}.",
    "edit_service_cancelled": "Редактирование отменено.",
    "hub_title": "Главное меню",
    "hub_settings_title": "Настройки",
    "hub_profile_title": "Профиль",
    "hub_schedule_title": "График",
    "hub_moderation_title": "Модерация",
    "hub_back_button": "← Назад",
    "hub_home_button": "⌂ Меню",
    "hub_ok_button": "OK",
    "hub_book_button": "Запись",
    "hub_my_bookings_button": "Мои записи",
    "hub_today_button": "Сегодня",
    "hub_services_button": "Услуги",
    "hub_schedule_section_button": "График",
    "hub_profile_section_button": "Профиль",
    "hub_settings_section_button": "Настройки",
    "hub_moderation_section_button": "Модерация",
    "hub_working_hours_button": "Рабочие часы",
    "hub_time_off_button": "Выходные",
    "hub_profile_show_button": "Показать профиль",
    "hub_profile_edit_button": "Изменить профиль",
    "hub_lang_button": "Язык",
    "hub_help_button": "Справка",
    "hub_admin_user_button": "Карточка пользователя",
    "hub_admin_set_role_button": "Сменить роль",
    "hub_admin_ban_button": "Забанить",
    "hub_admin_unban_button": "Разбанить",
    "hub_today_opened": "Записи на сегодня ниже. Нажмите ⌂ Меню, чтобы вернуться.",
    "hub_profile_edit_started": "Обновите профиль ниже. Нажмите ⌂ Меню, чтобы вернуться.",
    "hub_profile_incomplete": "Профиль не заполнен. Заполните данные ниже.",
    "/menu_description": "Открыть главное меню",
}
