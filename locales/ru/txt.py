RU: dict[str, str] = {
    "/help": (
        "Я помогаю записаться на услугу и управлять визитами.\n\n"
        "Всё управление — кнопками главного меню:\n"
        "• Запись — записаться к мастеру\n"
        "• Услуги — описание и фото услуг\n"
        "• Мои записи — ваши визиты\n"
        "• Профиль — контакты для связи\n"
        "• Настройки — язык и эта справка\n\n"
        "Команда /start обновляет меню; /menu присылает новое сообщение с меню."
    ),
    "/help_master": (
        "Вы мастер. Управление — кнопками главного меню:\n\n"
        "• Записи — неделя или календарь месяца → день → карточка "
        "(подтвердить / отменить)\n"
        "• Услуги — каталог и добавление\n"
        "• График — рабочие часы или дни; "
        "выходные (недельный режим) или перерывы в рабочем дне (месячный)\n"
        "• Настройки — язык и эта справка\n\n"
        "Команда /start обновляет меню; /menu присылает новое сообщение с меню."
    ),
    "/help_admin": (
        "Вы администратор бота. Модерация — "
        "кнопками главного меню:\n\n"
        "• Карточка пользователя\n"
        "• Сменить роль\n"
        "• Забанить / Разбанить\n"
        "• Настройки — язык и эта справка\n\n"
        "Команда /start обновляет меню; /menu присылает новое сообщение с меню."
    ),
    "client_booking_confirmed": (
        "Ваша запись подтверждена.\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}"
    ),
    "client_booking_cancelled_by_master": (
        "Мастер отменил вашу запись.\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}"
    ),
    "/lang": "Выберите язык",
    "unsupported_message": "Этот тип сообщений бот пока не обрабатывает.",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 Английский",
    "save_lang_button_text": "✅ Сохранить",
    "cancel_lang_button_text": "Отмена",
    "/start_description": "Старт бота/обновление меню",
    "/menu_description": "Новое сообщение с меню",
    "book_choose_service": "Выберите услугу",
    "book_choose_month": "Выберите месяц:",
    "book_choose_day": "Выберите день · {month}:",
    "book_choose_window": "Выберите время",
    "book_month_unavailable": "Этот месяц недоступен.",
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
    "catalog_header": "📋 Услуги мастера — выберите, чтобы посмотреть:",
    "catalog_empty": "Сейчас нет доступных услуг.",
    "catalog_back_button": "← Назад",
    "catalog_to_list_button": "← К списку",
    "catalog_not_found": "Услуга не найдена или больше недоступна.",
    "catalog_price_empty": "уточняется",
    "catalog_card_duration": "Длительность: {duration} мин",
    "catalog_card_price": "Цена: {price}",
    "master_bookings_header": "Записи · {week}\n{total}",
    "master_bookings_empty": (
        "На неделю {week} активных записей нет."
    ),
    "master_bookings_total_one": "Всего — {n} запись",
    "master_bookings_total_few": "Всего — {n} записи",
    "master_bookings_total_many": "Всего — {n} записей",
    "master_bookings_day_line_one": "{day} — {n} запись",
    "master_bookings_day_line_few": "{day} — {n} записи",
    "master_bookings_day_line_many": "{day} — {n} записей",
    "master_bookings_day_button": "{day}",
    "master_bookings_day_header": "{day}",
    "master_bookings_day_empty": "На {day} активных записей нет.",
    "master_bookings_day_item": "• {time} — {title} ({status})",
    "master_bookings_slot_button": "{time} · {title}",
    "master_bookings_card": (
        "Запись\n\n"
        "Дата и время: {when}\n"
        "Услуга: {title}\n"
        "Статус: {status}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}"
    ),
    "master_bookings_card_past": (
        "Запись\n\n"
        "Дата и время: {when}\n"
        "Услуга: {title}\n"
        "Статус: {status}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}\n\n"
        "✓ Время записи уже прошло"
    ),
    "master_bookings_back_button": "← Назад",
    "master_bookings_back_week_button": "← К неделе",
    "master_bookings_back_month_button": "← К месяцу",
    "master_bookings_close_button": "⌂ Меню",
    "master_bookings_week_prev": "←",
    "master_bookings_week_next": "→",
    "master_bookings_week_current": "Эта неделя",
    "master_bookings_month_header": "Записи · {month}\n{total}",
    "master_bookings_month_empty": (
        "В {month} активных записей нет.\n"
        "Выберите день на календаре или другой месяц."
    ),
    "master_bookings_month_prev": "←",
    "master_bookings_month_next": "→",
    "master_bookings_month_current": "Этот месяц",
    "master_bookings_calendar_day": "{day}",
    "master_bookings_calendar_day_busy": "•{day}",
    "status_pending": "ожидает подтверждения",
    "status_confirmed": "подтверждена",
    "status_cancelled": "отменена",
    "master_confirm_button": "✅ Подтвердить",
    "master_cancel_button": "❌ Отменить",
    "master_confirmed": "Запись #{id} подтверждена.",
    "master_cancelled": "Запись #{id} отменена.",
    "master_action_failed": "Не удалось выполнить действие.",
    "master_action_past": "Нельзя изменить запись: время уже прошло.",
    "master_new_booking": (
        "🔔 Новая запись\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}"
    ),
    "client_reminder_evening": (
        "Напоминание: завтра у вас запись.\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}"
    ),
    "client_reminder_hour": (
        "Напоминание: через час у вас запись.\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}"
    ),
    "master_reminder_evening": (
        "Напоминание: завтра запись.\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}"
    ),
    "master_reminder_hour": (
        "Напоминание: через час запись.\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}\n"
        "Клиент: {client_name}\n"
        "Телефон: {client_phone}"
    ),
    "reminder_ok_button": "OK",
    "reminder_cancel_button": "Отменить запись",
    "cancel_confirm": (
        "Отменить эту запись?\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}"
    ),
    "cancel_yes_button": "Да, отменить",
    "cancel_no_button": "Нет",
    "cancel_ask_reason": (
        "Можно коротко указать причину отмены "
        "(или нажмите «Без причины»)."
    ),
    "cancel_skip_reason_button": "Без причины",
    "cancel_reason_too_long": (
        "Слишком длинный текст. Уложитесь в 200 символов "
        "или нажмите «Без причины»."
    ),
    "cancel_reason_block": "\n\nПричина: {reason}",
    "cancel_done": "Запись отменена.",
    "cancel_failed": "Не удалось отменить запись.",
    "cancel_past": "Нельзя отменить: время уже прошло.",
    "cancel_unavailable": "Запись уже недоступна.",
    "decline_confirm": (
        "Отклонить эту заявку?\n\n"
        "Услуга: {title}\n"
        "Дата и время: {when}"
    ),
    "decline_yes_button": "Да, отклонить",
    "decline_ask_reason": (
        "Можно коротко указать причину отказа "
        "(или нажмите «Без причины»)."
    ),
    "decline_done": "Заявка отклонена.",
    "services_list_header": "📋 Ваши услуги:",
    "services_list_item": "• {title} — {duration} мин, {price} ({status})",
    "services_price_empty": "цена уточняется",
    "services_status_active": "активна",
    "services_status_inactive": "неактивна",
    "services_empty": (
        "У вас пока нет услуг.\n\n"
        "Добавьте услугу кнопкой ниже."
    ),
    "add_service_enter_title": (
        "Введите название услуги\n"
        "Например: Маникюр"
    ),
    "add_service_enter_duration": (
        "Введите длительность в минутах\n"
        "Например: 60"
    ),
    "add_service_enter_price": (
        "Введите цену (число) или «-» без цены\n"
        "Например: 1500 или 1500.50"
    ),
    "add_service_invalid_title": "Название не должно быть пустым (макс. 100 символов).",
    "add_service_invalid_duration": "Введите целое число минут больше 0.",
    "add_service_invalid_price": "Неверный формат цены. Число или «-».",
    "add_service_ok": "Услуга добавлена: {title}, {duration} мин, {price}.",
    "my_bookings_header": "Ваши записи:",
    "my_bookings_empty": (
        "У вас нет активных записей.\n\n"
        "Записаться можно через меню → Запись."
    ),
    "my_bookings_item": "• {weekday} {when} — {title} ({status})",
    "my_bookings_list_button": "{weekday} {when} · {title}",
    "my_bookings_card": (
        "Запись\n\n"
        "Дата и время: {when}\n"
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
        "Введите id или @username пользователя"
    ),
    "admin_hub_ask_role": (
        "Выберите новую роль для пользователя {user_id}"
    ),
    "admin_cancel_button": "Отмена",
    "admin_role_client_button": "client",
    "admin_role_master_button": "master",
    "admin_role_admin_button": "admin",
    "profile_consent_text": (
        "Перед записью нужно согласие на обработку персональных данных "
        "и коротко представиться.\n\n"
        "Мы запросим имя, фамилию и телефон, чтобы мастер мог связаться "
        "с вами по записи.\n\n"
        "Оператор: {operator_name}\n"
        "Контакты: {operator_contacts}\n\n"
        "Нажимая «Согласен», вы даёте согласие на обработку этих данных "
        "для записи и связи."
    ),
    "profile_consent_accept": "Согласен",
    "profile_consent_decline": "Не согласен",
    "profile_consent_terms_button": "Полные условия",
    "profile_consent_declined": (
        "Без согласия на обработку данных запись через бота недоступна."
    ),
    "profile_pdn_operator_fallback": "уточняется",
    "profile_pdn_contacts_fallback": "уточняется",
    "profile_intro_book": (
        "Перед записью нужно коротко представиться: имя, фамилия и телефон — "
        "чтобы мастер мог с вами связаться и подтвердить визит.\n\n"
        "Пожалуйста, введите имя:"
    ),
    "profile_intro_edit": (
        "Обновим ваши контакты.\n\n"
        "Пожалуйста, введите имя:"
    ),
    "profile_ask_first_name": "Введите имя:",
    "profile_ask_last_name": "Введите фамилию:",
    "profile_ask_phone": (
        "Укажите телефон для связи.\n"
        "Можно нажать кнопку ниже или ввести номер вручную (+7...)."
    ),
    "profile_share_phone_button": "📱 Отправить телефон",
    "profile_cancel_button": "Отмена",
    "profile_invalid_name": "Слишком короткое значение. Введите ещё раз.",
    "profile_invalid_phone": (
        "Не удалось распознать номер. "
        "Отправьте контакт кнопкой или номер в формате +79001234567."
    ),
    "profile_card": (
        "Ваш профиль:\n\n"
        "Имя: {first_name}\n"
        "Фамилия: {last_name}\n"
        "Телефон: {phone}"
    ),
    "schedule_header": "🗓 Ваш недельный график:",
    "schedule_list_item": "• {weekday} {starts}–{ends}",
    "schedule_empty": (
        "График ещё не задан.\n\n"
        "Нажмите «Редактировать график», чтобы добавить интервалы."
    ),
    "schedule_add_button": "➕ Добавить",
    "schedule_edit_button": "✏️ Редактировать график",
    "schedule_weekday_1": "Пн",
    "schedule_weekday_2": "Вт",
    "schedule_weekday_3": "Ср",
    "schedule_weekday_4": "Чт",
    "schedule_weekday_5": "Пт",
    "schedule_weekday_6": "Сб",
    "schedule_weekday_7": "Вс",
    "schedule_enter_starts": (
        "Введите время начала ЧЧ:ММ\n"
        "Пример: 09:00"
    ),
    "schedule_enter_ends": (
        "Введите время окончания ЧЧ:ММ\n"
        "Пример: 18:00"
    ),
    "schedule_choose_weekdays": (
        "Выберите дни для {starts}–{ends}.\n"
        "Нажмите день, чтобы отметить, затем «Сохранить»."
    ),
    "schedule_invalid_time": "Неверный формат времени. Используйте ЧЧ:ММ",
    "schedule_invalid_range": "Время окончания должно быть позже начала.",
    "schedule_need_weekday": "Выберите хотя бы один день.",
    "schedule_add_ok": "Добавлено: {starts}–{ends} ({days}).",
    "schedule_save_button": "Сохранить",
    "schedule_back_button": "← Назад",
    "schedule_cancel_button": "Отмена",
    "schedule_delete_button": "🗑 {item}",
    "schedule_confirm_delete": "Удалить {item}?",
    "schedule_confirm_yes": "Да",
    "schedule_confirm_no": "Нет",
    "schedule_deleted": "Интервал удалён.",
    "schedule_delete_not_found": "Интервал не найден.",
    "time_off_header": "🚫 Ближайшие выходные:",
    "time_off_list_item": "• {when}{note}",
    "time_off_empty": (
        "Ближайших выходных нет.\n\n"
        "Нажмите «Добавить», чтобы заблокировать дни."
    ),
    "time_off_add_button": "➕ Добавить",
    "time_off_back_button": "← Назад",
    "time_off_cancel_button": "Отмена",
    "time_off_choose_kind": "Какой выходной добавить?",
    "time_off_kind_days_button": "Целый день / диапазон",
    "time_off_kind_hours_button": "Часы в одном дне",
    "time_off_enter_starts": (
        "Введите первый день выходного ДД.ММ.ГГГГ\n"
        "Пример: {example}"
    ),
    "time_off_enter_ends": (
        "Введите последний день выходного ДД.ММ.ГГГГ\n"
        "Та же дата = один день. Пример: {example}"
    ),
    "time_off_enter_hours_day": (
        "Введите день ДД.ММ.ГГГГ\n"
        "Пример: {example}"
    ),
    "time_off_enter_hours_starts": (
        "Введите время начала ЧЧ:ММ\n"
        "Пример: 14:00"
    ),
    "time_off_enter_hours_ends": (
        "Введите время окончания ЧЧ:ММ\n"
        "Пример: 16:00"
    ),
    "time_off_invalid_date": "Неверный формат даты. Используйте ДД.ММ.ГГГГ",
    "time_off_invalid_time": "Неверный формат времени. Используйте ЧЧ:ММ",
    "time_off_invalid_range": "Дата окончания должна быть не раньше даты начала.",
    "time_off_invalid_time_range": "Время окончания должно быть позже времени начала.",
    "time_off_invalid_past": (
        "Нельзя добавить выходной только в прошлом — "
        "он не попадёт в список ближайших. "
        "Последний день должен быть сегодня или позже."
    ),
    "time_off_invalid_hours_past": (
        "Это окно уже в прошлом и не попадёт в список ближайших. "
        "Укажите более позднее время окончания."
    ),
    "time_off_add_ok": "Выходной добавлен: {when}.",
    "time_off_delete_button": "🗑 {item}",
    "time_off_confirm_delete": "Удалить {item}?",
    "time_off_confirm_yes": "Да",
    "time_off_confirm_no": "Нет",
    "time_off_deleted": "Выходной удалён.",
    "time_off_delete_not_found": "Выходной не найден.",
    "hub_breaks_button": "Перерывы",
    "time_off_breaks_header": "⏸ Ближайшие перерывы:",
    "time_off_breaks_empty": (
        "Ближайших перерывов нет.\n\n"
        "Добавьте часы недоступности внутри рабочего дня.\n"
        "Полный выходной — снимите день в «Рабочих днях»."
    ),
    "time_off_breaks_add_ok": "Перерыв добавлен: {when}.",
    "time_off_breaks_deleted": "Перерыв удалён.",
    "time_off_breaks_confirm_delete": "Удалить перерыв {item}?",
    "time_off_choose_open_day": "Выберите рабочий день на {month}:",
    "time_off_month_no_open_days": (
        "В {month} нет открытых рабочих дней для перерыва.\n"
        "Сначала отметьте дни в «Рабочих днях» или выберите другой месяц."
    ),
    "time_off_day_not_work_day": (
        "Этот день не рабочий. Выберите день с точкой на календаре "
        "или отметьте его в «Рабочих днях»."
    ),
    "time_off_month_prev": "←",
    "time_off_month_next": "→",
    "time_off_month_current": "Этот месяц",
    "time_off_calendar_day": "{day}",
    "time_off_calendar_day_open": "•{day}",
    "time_off_warn_header": (
        "В этом интервале есть записи. "
        "Перерыв сохранится, записи останутся:\n\n"
        "{list}\n\n"
        "Сохранить всё равно?"
    ),
    "time_off_warn_item": "• {when} — {client}",
    "time_off_warn_more": "…и ещё {n}",
    "time_off_warn_anyway": "Всё равно сохранить",
    "time_off_warn_back": "← Назад",
    "gap_view": (
        "⏱ Перерыв после приёма: {minutes} мин\n\n"
        "Следующая запись клиента не начнётся раньше, чем закончится эта пауза. "
        "0 = без перерыва."
    ),
    "gap_edit_button": "✏️ Изменить",
    "gap_back_button": "← Назад",
    "gap_cancel_button": "Отмена",
    "gap_enter": (
        "Введите перерыв после приёма в минутах "
        "(0 = без перерыва).\n"
        "Пример: 15"
    ),
    "gap_invalid": "Введите целое число минут (0 или больше).",
    "gap_invalid_max": "Максимум — {max} минут.",
    "gap_saved": "Перерыв установлен: {minutes} мин.",
    "gap_save_failed": "Не удалось сохранить перерыв. Попробуйте ещё раз.",
    "min_lead_view": (
        "⏳ Минимальный запас до записи: {minutes} мин\n\n"
        "Клиент не увидит слоты раньше, чем через столько минут от сейчас. "
        "0 = можно записаться сразу."
    ),
    "min_lead_edit_button": "✏️ Изменить",
    "min_lead_back_button": "← Назад",
    "min_lead_cancel_button": "Отмена",
    "min_lead_enter": (
        "Введите минимальный запас до записи в минутах "
        "(0 = можно сразу).\n"
        "Пример: 60"
    ),
    "min_lead_invalid": "Введите целое число минут (0 или больше).",
    "min_lead_invalid_max": "Максимум — {max} минут (24 часа).",
    "min_lead_saved": "Минимальный запас установлен: {minutes} мин.",
    "min_lead_save_failed": "Не удалось сохранить запас. Попробуйте ещё раз.",
    "slot_step_view": (
        "📐 Шаг сетки слотов: {step}\n\n"
        "Как часто предлагать время начала записи. "
        "«Как длительность услуги» — шаг равен выбранной услуге."
    ),
    "slot_step_value_default": "как длительность услуги",
    "slot_step_value_minutes": "{minutes} мин",
    "slot_step_edit_button": "✏️ Изменить",
    "slot_step_back_button": "← Назад",
    "slot_step_cancel_button": "Отмена",
    "slot_step_default_button": "Как длительность услуги",
    "slot_step_enter": (
        "Введите шаг сетки в минутах (целое число от 1).\n"
        "Пример: 15\n\n"
        "Или нажмите «Как длительность услуги»."
    ),
    "slot_step_invalid": "Введите целое число минут (1 или больше).",
    "slot_step_invalid_max": "Максимум — {max} минут.",
    "slot_step_saved": "Шаг сетки установлен: {minutes} мин.",
    "slot_step_saved_default": "Шаг сетки: как длительность услуги.",
    "slot_step_save_failed": "Не удалось сохранить шаг сетки. Попробуйте ещё раз.",
    "services_add_button": "➕ Добавить",
    "services_back_button": "← Назад",
    "services_cancel_button": "Отмена",
    "services_card": (
        "{title}\n"
        "Длительность: {duration} мин\n"
        "Цена: {price}\n"
        "Статус: {status}\n"
        "Описание: {description}\n"
        "Фото: {photo}"
    ),
    "services_card_media": (
        "{title}\n"
        "Длительность: {duration} мин\n"
        "Цена: {price}\n"
        "Статус: {status}\n"
        "Описание: {description}"
    ),
    "services_description_empty": "не указано",
    "services_photo_yes": "есть",
    "services_photo_no": "нет",
    "services_not_found": "Услуга не найдена.",
    "services_deactivate_button": "⏸ Деактивировать",
    "services_activate_button": "▶️ Включить",
    "services_deactivated": "Услуга деактивирована.",
    "services_activated": "Услуга включена.",
    "services_edit_button": "✏️ Изменить",
    "services_description_button": "📝 Описание",
    "services_photo_button": "🖼 Фото",
    "services_clear_description_button": "Удалить описание",
    "services_clear_photo_button": "Удалить фото",
    "services_enter_description": (
        "Введите описание услуги (макс. {max} символов).\n"
        "Сейчас: {description}"
    ),
    "services_invalid_description": (
        "Описание не должно быть пустым и длиннее {max} символов."
    ),
    "services_description_saved": "Описание сохранено.",
    "services_description_cleared": "Описание удалено.",
    "services_enter_photo": (
        "Отправьте одно фото услуги (не файл и не альбом).\n"
        "Сейчас: {photo}"
    ),
    "services_invalid_photo": "Нужно именно фото (не документ и не альбом).",
    "services_photo_saved": "Фото сохранено.",
    "services_photo_cleared": "Фото удалено.",
    "edit_service_enter_title": (
        "Введите новое название\n"
        "Сейчас: {title}"
    ),
    "edit_service_enter_duration": (
        "Введите новую длительность в минутах\n"
        "Сейчас: {duration}"
    ),
    "edit_service_enter_price": (
        "Введите новую цену (или - чтобы очистить)\n"
        "Сейчас: {price}"
    ),
    "edit_service_ok": "Услуга обновлена: {title}, {duration} мин, {price}.",
    "hub_title": "Главное меню",
    "hub_settings_title": "Настройки",
    "hub_profile_title": "Профиль",
    "hub_schedule_title": "График",
    "work_days_choose_month": "Выберите месяц:",
    "work_days_choose_days": "Выберите рабочие дни на {month}:",
    "work_days_enter_starts": (
        "Введите время начала работы в формате ЧЧ:ММ\n"
        "Например: 09:00"
    ),
    "work_days_enter_ends": (
        "Введите время окончания работы в формате ЧЧ:ММ\n"
        "Например: 18:00"
    ),
    "work_days_confirm": (
        "Установить рабочие дни {dates} "
        "с {starts}–{ends}?"
    ),
    "work_days_confirm_clear": (
        "Убрать все рабочие дни на {month}? "
        "Дни станут выходными для записи."
    ),
    "work_days_confirm_off": "Сделать выходным: {dates}?",
    "work_days_no_changes": "Ничего не изменилось.",
    "work_days_month_unavailable": "Этот месяц недоступен.",
    "work_days_saved": (
        "Сохранено: {dates}, {starts}–{ends}."
    ),
    "work_days_off_saved": "Выходные: {dates}.",
    "work_days_cleared": "Рабочие дни на {month} сняты.",
    "work_days_summary_button": "Показать текущий график",
    "work_days_summary_header": "График на {month}:",
    "work_days_summary_item": "• {date} {starts}–{ends}",
    "work_days_summary_empty": "На {month} рабочих дней пока нет.",
    "work_days_warn_header": (
        "На закрываемых днях есть записи. "
        "Дни закроются, записи останутся:\n\n"
        "{list}\n\n"
        "Сохранить всё равно?"
    ),
    "work_days_warn_item": "• {when} — {client}",
    "work_days_warn_more": "…и ещё {n}",
    "work_days_warn_anyway": "Всё равно сохранить",
    "work_days_warn_back": "← К календарю",
    "work_days_next_button": "Далее",
    "work_days_back_button": "← Назад",
    "work_days_cancel_button": "Отмена",
    "work_days_confirm_yes": "Да",
    "work_days_confirm_no": "Нет",
    "work_days_month_1": "Январь",
    "work_days_month_2": "Февраль",
    "work_days_month_3": "Март",
    "work_days_month_4": "Апрель",
    "work_days_month_5": "Май",
    "work_days_month_6": "Июнь",
    "work_days_month_7": "Июль",
    "work_days_month_8": "Август",
    "work_days_month_9": "Сентябрь",
    "work_days_month_10": "Октябрь",
    "work_days_month_11": "Ноябрь",
    "work_days_month_12": "Декабрь",
    "work_days_month_short_1": "янв",
    "work_days_month_short_2": "фев",
    "work_days_month_short_3": "мар",
    "work_days_month_short_4": "апр",
    "work_days_month_short_5": "май",
    "work_days_month_short_6": "июн",
    "work_days_month_short_7": "июл",
    "work_days_month_short_8": "авг",
    "work_days_month_short_9": "сен",
    "work_days_month_short_10": "окт",
    "work_days_month_short_11": "ноя",
    "work_days_month_short_12": "дек",
    "hub_back_button": "← Назад",
    "hub_home_button": "⌂ Меню",
    "hub_ok_button": "OK",
    "hub_book_button": "Запись",
    "hub_catalog_button": "Услуги",
    "hub_my_bookings_button": "Мои записи",
    "hub_bookings_button": "Записи",
    "hub_services_button": "Услуги",
    "hub_schedule_section_button": "График",
    "hub_profile_section_button": "Профиль",
    "hub_settings_section_button": "Настройки",
    "hub_working_hours_button": "Рабочие часы",
    "hub_work_days_button": "Рабочие дни",
    "hub_time_off_button": "Выходные",
    "hub_gap_button": "Перерыв между записями",
    "hub_min_lead_button": "Минимальный запас",
    "hub_slot_step_button": "Шаг сетки",
    "hub_profile_show_button": "Показать профиль",
    "hub_profile_edit_button": "Изменить профиль",
    "hub_lang_button": "Язык",
    "hub_help_button": "Справка",
    "hub_admin_user_button": "Карточка пользователя",
    "hub_admin_set_role_button": "Сменить роль",
    "hub_admin_ban_button": "Забанить",
    "hub_admin_unban_button": "Разбанить",
}
