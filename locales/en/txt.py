EN: dict[str, str] = {
    "/help": (
        "I help you book a service and manage appointments.\n\n"
        "Everything is controlled from the main menu buttons:\n"
        "• Book — book an appointment\n"
        "• Services — descriptions and photos\n"
        "• My bookings — your visits\n"
        "• Profile — contact details\n"
        "• Settings — language and this help\n\n"
        "Send /start to open the menu again."
    ),
    "/help_master": (
        "You are a specialist. Use the main menu buttons:\n\n"
        "• Bookings — week → day → card "
        "(confirm / cancel)\n"
        "• Services — catalogue and add\n"
        "• Schedule — working hours and time off\n"
        "• Settings — language and this help\n\n"
        "Send /start to open the menu again."
    ),
    "/help_admin": (
        "You are a bot administrator. Moderation is on "
        "the main menu buttons:\n\n"
        "• User card\n"
        "• Set role\n"
        "• Ban / Unban\n"
        "• Settings — language and this help\n\n"
        "Send /start to open the menu again."
    ),
    "client_booking_confirmed": (
        "Your appointment has been confirmed.\n\n"
        "Service: {title}\n"
        "Date and time: {when}"
    ),
    "client_booking_cancelled_by_master": (
        "The specialist cancelled your appointment.\n\n"
        "Service: {title}\n"
        "Date and time: {when}"
    ),
    "/lang": "Select a language",
    "unsupported_message": "This type of message is not supported yet.",
    "ru": "🇷🇺 Russian",
    "en": "🇬🇧 English",
    "save_lang_button_text": "✅ Save",
    "cancel_lang_button_text": "Cancel",
    "/start_description": "Restart the bot",
    "book_choose_service": "Choose a service",
    "book_choose_day": "Choose a day",
    "book_choose_window": "Choose a time",
    "book_confirm": (
        "Please confirm your appointment:\n\n"
        "Service: {title}\n"
        "Date and time: {when}\n"
        "Duration: {duration} min\n"
        "Price: {price}"
    ),
    "book_price_empty": "to be confirmed",
    "book_ok": "You are booked. Status: waiting for the specialist to confirm.",
    "book_cancelled": "Booking cancelled.",
    "book_no_services": "No services are available right now.",
    "book_no_windows": "No available times. Choose another day or service.",
    "book_use_buttons": "Please use the buttons below.",
    "book_back_button": "← Back",
    "book_cancel_button": "Cancel",
    "book_confirm_button": "Book",
    "service_button": "{title} · {duration} min",
    "book_window_taken": "This time is already taken. Please choose another.",
    "book_window_not_found": "This time is no longer available.",
    "book_service_inactive": "This service is no longer available.",
    "book_service_not_found": "Service not found.",
    "book_need_start": "Please send /start first",
    "catalog_header": "📋 Master’s services — tap one to view:",
    "catalog_empty": "No services available right now.",
    "catalog_back_button": "← Back",
    "catalog_to_list_button": "← Back to list",
    "catalog_not_found": "Service not found or no longer available.",
    "catalog_price_empty": "TBD",
    "catalog_card_duration": "Duration: {duration} min",
    "catalog_card_price": "Price: {price}",
    "master_bookings_header": "Bookings · {week}\n{total}",
    "master_bookings_empty": (
        "No active bookings for the week of {week}."
    ),
    "master_bookings_total_one": "Total — {n} booking",
    "master_bookings_total_few": "Total — {n} bookings",
    "master_bookings_total_many": "Total — {n} bookings",
    "master_bookings_day_line_one": "{day} — {n} booking",
    "master_bookings_day_line_few": "{day} — {n} bookings",
    "master_bookings_day_line_many": "{day} — {n} bookings",
    "master_bookings_day_button": "{day}",
    "master_bookings_day_header": "{day}",
    "master_bookings_day_empty": "No active bookings on {day}.",
    "master_bookings_day_item": "• {time} — {title} ({status})",
    "master_bookings_slot_button": "{time} · {title}",
    "master_bookings_card": (
        "Appointment\n\n"
        "When: {when}\n"
        "Service: {title}\n"
        "Status: {status}\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}"
    ),
    "master_bookings_card_past": (
        "Appointment\n\n"
        "When: {when}\n"
        "Service: {title}\n"
        "Status: {status}\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}\n\n"
        "✓ Appointment time has already passed"
    ),
    "master_bookings_back_button": "← Back",
    "master_bookings_back_week_button": "← Week",
    "master_bookings_close_button": "⌂ Menu",
    "master_bookings_week_prev": "←",
    "master_bookings_week_next": "→",
    "master_bookings_week_current": "This week",
    "status_pending": "awaiting confirmation",
    "status_confirmed": "confirmed",
    "status_cancelled": "cancelled",
    "master_confirm_button": "✅ Confirm",
    "master_cancel_button": "❌ Cancel",
    "master_confirmed": "Appointment #{id} confirmed.",
    "master_cancelled": "Appointment #{id} cancelled.",
    "master_action_failed": "Failed to perform action.",
    "master_action_past": "Cannot change this appointment: the time has already passed.",
    "master_new_booking": (
        "🔔 New booking\n\n"
        "Service: {title}\n"
        "Date and time: {when}\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}"
    ),
    "services_list_header": "📋 Your services:",
    "services_list_item": "• {title} — {duration} min, {price} ({status})",
    "services_price_empty": "price to be confirmed",
    "services_status_active": "active",
    "services_status_inactive": "inactive",
    "services_empty": (
        "You have no services yet.\n\n"
        "Add one with the button below."
    ),
    "add_service_enter_title": (
        "Enter the service name\n"
        "Example: Manicure"
    ),
    "add_service_enter_duration": (
        "Enter the duration in minutes\n"
        "Example: 60"
    ),
    "add_service_enter_price": (
        "Enter the price (number) or «-» for no price\n"
        "Example: 1500 or 1500.50"
    ),
    "add_service_invalid_title": "Name must not be empty (max 100 characters).",
    "add_service_invalid_duration": "Enter a whole number of minutes greater than 0.",
    "add_service_invalid_price": "Invalid price format. Use a number or «-».",
    "add_service_ok": "Service added: {title}, {duration} min, {price}.",
    "my_bookings_header": "Your appointments:",
    "my_bookings_empty": (
        "You have no active appointments.\n\n"
        "Book one from the menu → Book."
    ),
    "my_bookings_item": "• {weekday} {when} — {title} ({status})",
    "my_bookings_list_button": "{weekday} {when} · {title}",
    "my_bookings_card": (
        "Appointment\n\n"
        "When: {when}\n"
        "Service: {title}\n"
        "Status: {status}"
    ),
    "my_bookings_cancel_button": "Cancel appointment",
    "my_bookings_back_button": "← Back",
    "my_bookings_close_button": "Close",
    "my_bookings_cancelled": "Appointment cancelled.",
    "my_bookings_action_failed": "Failed to cancel the appointment.",
    "master_booking_cancelled_by_client": (
        "The client cancelled an appointment.\n\n"
        "Service: {title}\n"
        "Date and time: {when}\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}"
    ),
    "admin_user_not_found": "User {target} not found.",
    "admin_user_card": (
        "👤 User {user_id}\n\n"
        "Username: {username}\n"
        "First name: {first_name}\n"
        "Last name: {last_name}\n"
        "Phone: {phone}\n"
        "Role: {role}\n"
        "Language: {language}\n"
        "Banned: {banned}\n"
        "Registered: {created_at}"
    ),
    "admin_no_username": "not set",
    "admin_yes": "yes",
    "admin_no": "no",
    "admin_ban_self": "You cannot ban yourself.",
    "admin_ban_staff": "You cannot ban an administrator or a specialist.",
    "admin_already_banned": "User {user_id} is already banned.",
    "admin_not_banned": "User {user_id} is not banned.",
    "admin_banned": "User {user_id} has been banned.",
    "admin_unbanned": "User {user_id} has been unbanned.",
    "admin_invalid_role": "Unknown role. Available: {roles}",
    "admin_demote_self": "You cannot remove your own administrator role.",
    "admin_role_unchanged": "User {user_id} already has the role {role}.",
    "admin_role_set": "User {user_id} now has the role {role}.",
    "admin_role_changed_notice": "Your role has been changed to {role}.",
    "admin_hub_ask_target": (
        "Enter user id or @username"
    ),
    "admin_hub_ask_role": (
        "Choose a new role for user {user_id}"
    ),
    "admin_cancel_button": "Cancel",
    "admin_role_client_button": "client",
    "admin_role_master_button": "master",
    "admin_role_admin_button": "admin",
    "profile_ask_first_name": "What is your first name?",
    "profile_ask_last_name": "What is your last name?",
    "profile_ask_phone": (
        "Share a phone number so the specialist can contact you.\n"
        "Tap the button below or type the number manually (+1...)."
    ),
    "profile_share_phone_button": "📱 Share phone number",
    "profile_cancel_button": "Cancel",
    "profile_invalid_name": "That value is too short. Please try again.",
    "profile_invalid_phone": (
        "Could not read that number. "
        "Share a contact via the button or type it like +79001234567."
    ),
    "profile_saved_continue_book": (
        "You can book now from the menu → Book."
    ),
    "profile_card": (
        "Your profile:\n\n"
        "First name: {first_name}\n"
        "Last name: {last_name}\n"
        "Phone: {phone}"
    ),
    "schedule_header": "🗓 Your weekly schedule:",
    "schedule_list_item": "• {weekday} {starts}–{ends}",
    "schedule_empty": (
        "No working hours yet.\n\n"
        "Tap “Edit schedule” to add intervals."
    ),
    "schedule_add_button": "➕ Add",
    "schedule_edit_button": "✏️ Edit schedule",
    "schedule_weekday_1": "Mon",
    "schedule_weekday_2": "Tue",
    "schedule_weekday_3": "Wed",
    "schedule_weekday_4": "Thu",
    "schedule_weekday_5": "Fri",
    "schedule_weekday_6": "Sat",
    "schedule_weekday_7": "Sun",
    "schedule_enter_starts": (
        "Enter the start time as HH:MM\n"
        "Example: 09:00"
    ),
    "schedule_enter_ends": (
        "Enter the end time as HH:MM\n"
        "Example: 18:00"
    ),
    "schedule_choose_weekdays": (
        "Select weekdays for {starts}–{ends}.\n"
        "Tap a day to toggle, then Save."
    ),
    "schedule_invalid_time": "Invalid time format. Use HH:MM",
    "schedule_invalid_range": "End time must be after start time.",
    "schedule_need_weekday": "Select at least one weekday.",
    "schedule_add_ok": "Added: {starts}–{ends} ({days}).",
    "schedule_save_button": "Save",
    "schedule_back_button": "← Back",
    "schedule_cancel_button": "Cancel",
    "schedule_delete_button": "🗑 {item}",
    "schedule_confirm_delete": "Delete {item}?",
    "schedule_confirm_yes": "Yes",
    "schedule_confirm_no": "No",
    "schedule_deleted": "Interval removed.",
    "schedule_delete_not_found": "Interval not found.",
    "time_off_header": "🚫 Upcoming time off:",
    "time_off_list_item": "• {when}{note}",
    "time_off_empty": (
        "No upcoming time off.\n\n"
        "Tap “Edit” to block days."
    ),
    "time_off_add_button": "➕ Add",
    "time_off_edit_button": "✏️ Edit",
    "time_off_back_button": "← Back",
    "time_off_cancel_button": "Cancel",
    "time_off_choose_kind": "What kind of time off?",
    "time_off_kind_days_button": "Full day / date range",
    "time_off_kind_hours_button": "Hours in one day",
    "time_off_enter_starts": (
        "Enter the first day off as DD.MM.YYYY\n"
        "Example: {example}"
    ),
    "time_off_enter_ends": (
        "Enter the last day off as DD.MM.YYYY\n"
        "Same date = one day. Example: {example}"
    ),
    "time_off_enter_hours_day": (
        "Enter the day as DD.MM.YYYY\n"
        "Example: {example}"
    ),
    "time_off_enter_hours_starts": (
        "Enter the start time as HH:MM\n"
        "Example: 14:00"
    ),
    "time_off_enter_hours_ends": (
        "Enter the end time as HH:MM\n"
        "Example: 16:00"
    ),
    "time_off_invalid_date": "Invalid date format. Use DD.MM.YYYY",
    "time_off_invalid_time": "Invalid time format. Use HH:MM",
    "time_off_invalid_range": "The end date must be on or after the start date.",
    "time_off_invalid_time_range": "The end time must be after the start time.",
    "time_off_invalid_past": (
        "A time-off block entirely in the past will not appear "
        "in the upcoming list. The last day must be today or later."
    ),
    "time_off_invalid_hours_past": (
        "This time window is already in the past and will not appear "
        "in the upcoming list. Pick a later end time."
    ),
    "time_off_add_ok": "Time off added: {when}.",
    "time_off_delete_button": "🗑 {item}",
    "time_off_confirm_delete": "Delete {item}?",
    "time_off_confirm_yes": "Yes",
    "time_off_confirm_no": "No",
    "time_off_deleted": "Time off removed.",
    "time_off_delete_not_found": "Time off not found.",
    "gap_view": (
        "⏱ Break after each appointment: {minutes} min\n\n"
        "Clients cannot book the next slot until this pause ends. "
        "0 = back-to-back."
    ),
    "gap_edit_button": "✏️ Change",
    "gap_back_button": "← Back",
    "gap_cancel_button": "Cancel",
    "gap_enter": (
        "Enter the break after each appointment in minutes "
        "(0 = no break).\n"
        "Example: 15"
    ),
    "gap_invalid": "Enter a whole number of minutes (0 or more).",
    "gap_invalid_max": "Maximum is {max} minutes.",
    "gap_saved": "Break set to {minutes} min.",
    "gap_save_failed": "Could not save the break. Try again.",
    "min_lead_view": (
        "⏳ Minimum lead time: {minutes} min\n\n"
        "Clients cannot book a start sooner than this many minutes from now. "
        "0 = allow booking immediately."
    ),
    "min_lead_edit_button": "✏️ Change",
    "min_lead_back_button": "← Back",
    "min_lead_cancel_button": "Cancel",
    "min_lead_enter": (
        "Enter the minimum lead time in minutes "
        "(0 = allow booking immediately).\n"
        "Example: 60"
    ),
    "min_lead_invalid": "Enter a whole number of minutes (0 or more).",
    "min_lead_invalid_max": "Maximum is {max} minutes (24 hours).",
    "min_lead_saved": "Minimum lead time set to {minutes} min.",
    "min_lead_save_failed": "Could not save the lead time. Try again.",
    "slot_step_view": (
        "📐 Slot grid step: {step}\n\n"
        "How often to offer appointment start times. "
        "“Use service duration” means the step equals the chosen service."
    ),
    "slot_step_value_default": "same as service duration",
    "slot_step_value_minutes": "{minutes} min",
    "slot_step_edit_button": "✏️ Change",
    "slot_step_back_button": "← Back",
    "slot_step_cancel_button": "Cancel",
    "slot_step_default_button": "Use service duration",
    "slot_step_enter": (
        "Enter the grid step in minutes (whole number from 1).\n"
        "Example: 15\n\n"
        "Or tap “Use service duration”."
    ),
    "slot_step_invalid": "Enter a whole number of minutes (1 or more).",
    "slot_step_invalid_max": "Maximum is {max} minutes.",
    "slot_step_saved": "Grid step set to {minutes} min.",
    "slot_step_saved_default": "Grid step: same as service duration.",
    "slot_step_save_failed": "Could not save the grid step. Try again.",
    "services_add_button": "➕ Add",
    "services_back_button": "← Back",
    "services_cancel_button": "Cancel",
    "services_card": (
        "{title}\n"
        "Duration: {duration} min\n"
        "Price: {price}\n"
        "Status: {status}\n"
        "Description: {description}\n"
        "Photo: {photo}"
    ),
    "services_card_media": (
        "{title}\n"
        "Duration: {duration} min\n"
        "Price: {price}\n"
        "Status: {status}\n"
        "Description: {description}"
    ),
    "services_description_empty": "not set",
    "services_photo_yes": "yes",
    "services_photo_no": "no",
    "services_not_found": "Service not found.",
    "services_deactivate_button": "⏸ Deactivate",
    "services_activate_button": "▶️ Activate",
    "services_deactivated": "Service deactivated.",
    "services_activated": "Service activated.",
    "services_edit_button": "✏️ Edit",
    "services_description_button": "📝 Description",
    "services_photo_button": "🖼 Photo",
    "services_clear_description_button": "Remove description",
    "services_clear_photo_button": "Remove photo",
    "services_enter_description": (
        "Enter the service description (max {max} characters).\n"
        "Current: {description}"
    ),
    "services_invalid_description": (
        "Description must not be empty and at most {max} characters."
    ),
    "services_description_saved": "Description saved.",
    "services_description_cleared": "Description removed.",
    "services_enter_photo": (
        "Send one photo of the service (not a file or album).\n"
        "Current: {photo}"
    ),
    "services_invalid_photo": "Send a photo (not a document or album).",
    "services_photo_saved": "Photo saved.",
    "services_photo_cleared": "Photo removed.",
    "edit_service_enter_title": (
        "Enter the new service name\n"
        "Current: {title}"
    ),
    "edit_service_enter_duration": (
        "Enter the new duration in minutes\n"
        "Current: {duration}"
    ),
    "edit_service_enter_price": (
        "Enter the new price (or - to clear)\n"
        "Current: {price}"
    ),
    "edit_service_ok": "Service updated: {title}, {duration} min, {price}.",
    "hub_title": "Main menu",
    "hub_settings_title": "Settings",
    "hub_profile_title": "Profile",
    "hub_schedule_title": "Schedule",
    "work_days_stub": (
        "Monthly work-day setup is coming in the next update.\n"
        "The bot is in monthly mode — slots are not built from calendar days yet."
    ),
    "hub_back_button": "← Back",
    "hub_home_button": "⌂ Menu",
    "hub_ok_button": "OK",
    "hub_book_button": "Book",
    "hub_catalog_button": "Services",
    "hub_my_bookings_button": "My bookings",
    "hub_bookings_button": "Bookings",
    "hub_services_button": "Services",
    "hub_schedule_section_button": "Schedule",
    "hub_profile_section_button": "Profile",
    "hub_settings_section_button": "Settings",
    "hub_working_hours_button": "Working hours",
    "hub_work_days_button": "Work days",
    "hub_time_off_button": "Time off",
    "hub_gap_button": "Break between appointments",
    "hub_min_lead_button": "Minimum lead time",
    "hub_slot_step_button": "Slot grid step",
    "hub_profile_show_button": "Show profile",
    "hub_profile_edit_button": "Edit profile",
    "hub_lang_button": "Language",
    "hub_help_button": "Help",
    "hub_admin_user_button": "User card",
    "hub_admin_set_role_button": "Set role",
    "hub_admin_ban_button": "Ban user",
    "hub_admin_unban_button": "Unban user",
}
