EN: dict[str, str] = {
    "/start": (
        "Hello!\n\n"
        "I am a booking bot for appointments with a specialist.\n\n"
        "Available commands:\n"
        "/profile - authorization\n"
        "/book — book an appointment\n"
        "/my_bookings — my appointments\n"
        "/help — help\n"
        "/lang — interface language"
    ),
    "/start_master": (
        "Hello!\n\n"
        "You are signed in as a specialist.\n\n"
        "Commands:\n"
        "/today — today's appointments\n"
        "/schedule — weekly working hours\n"
        "/time_off — days off / absences\n"
        "/services — my services\n"
        "/add_service — add a service\n"
        "/lang — interface language\n"
        "/help — help"
    ),
    "/start_admin": (
        "Hello!\n\n"
        "You are a bot administrator.\n\n"
        "Commands:\n"
        "/book — book an appointment\n"
        "/my_bookings — my appointments\n"
        "/user — user profile\n"
        "/set_role — change role\n"
        "/ban — ban user\n"
        "/unban — unban user\n"
        "/lang — interface language\n"
        "/help — help"
    ),
    "/help": (
        "I help you book a service and manage appointments.\n\n"
        "Commands:\n"
        "/start — restart the bot\n"
        "/profile - authorization\n"
        "/book — book an appointment\n"
        "/my_bookings — my appointments\n"
        "/lang — interface language\n"
        "/help — this help"
    ),
    "/help_master": (
        "You are a specialist. Booking management:\n\n"
        "/today — today's appointments (confirm / cancel)\n"
        "/schedule — weekly working hours\n"
        "/time_off — block days off (absences)\n"
        "/services — list of services\n"
        "/add_service — add a service\n"
        "/lang — interface language\n"
        "/help — this help"
    ),
    "/help_admin": (
        "You are a bot administrator.\n\n"
        "Commands:\n"
        "/start — restart the bot\n"
        "/book — book an appointment\n"
        "/my_bookings — my appointments\n"
        "/user &lt;id|@username&gt; — user profile\n"
        "/set_role &lt;id|@username&gt; &lt;role&gt; — change role\n"
        "/ban &lt;id|@username&gt; — ban user\n"
        "/unban &lt;id|@username&gt; — unban user\n"
        "/lang — interface language\n"
        "/help — this help"
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
    "lang_saved": (
        "The language has been saved and will be used for the bot interface.\n\n"
        "You can send /help"
    ),
    "lang_cancelled": (
        "OK, your language is still: {}.\n\n"
        "You can send /help"
    ),
    "/start_description": "Restart the bot",
    "/lang_description": "Configure the interface language",
    "/help_description": "View help",
    "/book": "Choose a service",
    "/book_description": "Book an appointment",
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
    "/today_description": "Today's appointments",
    "master_today_header": "📅 Today's appointments:",
    "master_today_empty": "No appointments for today.",
    "master_today_item": (
        "{time} — {title} ({status})\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}"
    ),
    "master_today_item_past": (
        "{time} — {title} ({status})\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}\n"
        "✓ Appointment time has already passed"
    ),
    "status_pending": "pending",
    "status_confirmed": "confirmed",
    "status_cancelled": "cancelled",
    "master_confirm_button": "✅ Confirm",
    "master_cancel_button": "❌ Cancel",
    "master_confirmed": "Appointment #{id} confirmed.",
    "master_cancelled": "Appointment #{id} cancelled.",
    "master_action_failed": "Failed to perform action.",
    "master_close_button": "Close",
    "master_action_past": "Cannot change this appointment: the time has already passed.",
    "master_new_booking": (
        "🔔 New booking\n\n"
        "Service: {title}\n"
        "Date and time: {when}\n"
        "Client: {client_name}\n"
        "Phone: {client_phone}\n\n"
        "Today's appointments: /today"
    ),
    "/services_description": "My services",
    "services_list_header": "📋 Your services:",
    "services_list_item": "• {title} — {duration} min, {price} ({status})",
    "services_price_empty": "price to be confirmed",
    "services_status_active": "active",
    "services_status_inactive": "inactive",
    "services_empty": (
        "You have no services yet.\n\n"
        "Add one: /add_service"
    ),
    "services_add_hint": "Add a service: /add_service",
    "add_service_enter_title": (
        "Enter the service name\n"
        "Example: Manicure\n\n"
        "Cancel: /cancel"
    ),
    "add_service_enter_duration": (
        "Enter the duration in minutes\n"
        "Example: 60\n\n"
        "Cancel: /cancel"
    ),
    "add_service_enter_price": (
        "Enter the price (number) or «-» for no price\n"
        "Example: 1500 or 1500.50\n\n"
        "Cancel: /cancel"
    ),
    "add_service_invalid_title": "Name must not be empty (max 100 characters).",
    "add_service_invalid_duration": "Enter a whole number of minutes greater than 0.",
    "add_service_invalid_price": "Invalid price format. Use a number or «-».",
    "add_service_ok": "Service added: {title}, {duration} min, {price}.",
    "add_service_cancelled": "Adding a service was cancelled.",
    "/add_service_description": "Add a service",
    "/my_bookings_description": "My appointments",
    "my_bookings_header": "🗓 Your appointments:",
    "my_bookings_empty": (
        "You have no active appointments.\n\n"
        "Book one: /book"
    ),
    "my_bookings_item": "{when} — {title} ({status})",
    "my_bookings_cancel_button": "❌ Cancel appointment",
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
    "/user_description": "User card",
    "/set_role_description": "Change role",
    "/ban_description": "Ban a user",
    "/unban_description": "Unban a user",
    "admin_usage_user": "Usage: /user &lt;id|@username&gt;",
    "admin_usage_ban": "Usage: /ban &lt;id|@username&gt;",
    "admin_usage_unban": "Usage: /unban &lt;id|@username&gt;",
    "admin_usage_set_role": "Usage: /set_role &lt;id|@username&gt; &lt;role&gt;",
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
        "Enter user id or @username\n\n"
        "Cancel: /cancel"
    ),
    "admin_hub_ask_role": (
        "Choose a new role for user {user_id}\n\n"
        "Cancel: /cancel"
    ),
    "admin_hub_cancelled": "Moderation cancelled.",
    "admin_role_client_button": "client",
    "admin_role_master_button": "master",
    "admin_role_admin_button": "admin",
    "/profile_description": "My profile",
    "profile_ask_first_name": "What is your first name?",
    "profile_ask_last_name": "What is your last name?",
    "profile_ask_phone": (
        "Share a phone number so the specialist can contact you.\n"
        "Tap the button below or type the number manually (+1...)."
    ),
    "profile_share_phone_button": "📱 Share phone number",
    "profile_invalid_name": "That value is too short. Please try again.",
    "profile_invalid_phone": (
        "Could not read that number. "
        "Share a contact via the button or type it like +79001234567."
    ),
    "profile_saved": "Profile saved.",
    "profile_saved_continue_book": "You can book now: /book",
    "profile_cancelled": "Profile setup cancelled.",
    "profile_card": (
        "Your profile:\n\n"
        "First name: {first_name}\n"
        "Last name: {last_name}\n"
        "Phone: {phone}"
    ),
    "profile_edit_hint": "To update your details, send: /edit_profile",
    "/schedule_description": "My working hours",
    "schedule_header": "🗓 Your weekly schedule:",
    "schedule_list_item": "• {weekday} {starts}–{ends}",
    "schedule_empty": (
        "No working hours yet.\n\n"
        "Add an interval with the button below."
    ),
    "schedule_add_button": "➕ Add",
    "schedule_close_button": "Close",
    "schedule_closed": "Schedule closed.",
    "schedule_weekday_1": "Mon",
    "schedule_weekday_2": "Tue",
    "schedule_weekday_3": "Wed",
    "schedule_weekday_4": "Thu",
    "schedule_weekday_5": "Fri",
    "schedule_weekday_6": "Sat",
    "schedule_weekday_7": "Sun",
    "schedule_enter_starts": (
        "Enter the start time as HH:MM\n"
        "Example: 09:00\n\n"
        "Cancel: /cancel"
    ),
    "schedule_enter_ends": (
        "Enter the end time as HH:MM\n"
        "Example: 18:00\n\n"
        "Cancel: /cancel"
    ),
    "schedule_choose_weekdays": (
        "Select weekdays for {starts}–{ends}.\n"
        "Tap a day to toggle, then Save."
    ),
    "schedule_invalid_time": "Invalid time format. Use HH:MM",
    "schedule_invalid_range": "End time must be after start time.",
    "schedule_need_weekday": "Select at least one weekday.",
    "schedule_add_ok": "Added: {starts}–{ends} ({days}).",
    "schedule_cancelled": "Schedule editing cancelled.",
    "schedule_save_button": "Save",
    "schedule_back_button": "← Back",
    "schedule_cancel_button": "Cancel",
    "schedule_delete_button": "🗑 {item}",
    "schedule_confirm_delete": "Delete {item}?",
    "schedule_confirm_yes": "Yes",
    "schedule_confirm_no": "No",
    "schedule_deleted": "Interval removed.",
    "schedule_delete_not_found": "Interval not found.",
    "/time_off_description": "Time off / absences",
    "time_off_header": "🚫 Upcoming time off:",
    "time_off_list_item": "• {when}{note}",
    "time_off_empty": (
        "No upcoming time off.\n\n"
        "Block days with the button below."
    ),
    "time_off_add_button": "➕ Add",
    "time_off_close_button": "Close",
    "time_off_closed": "Time off list closed.",
    "time_off_enter_starts": (
        "Enter the first day off as DD.MM.YYYY\n"
        "Example: 20.09.2026\n\n"
        "Cancel: /cancel"
    ),
    "time_off_enter_ends": (
        "Enter the last day off as DD.MM.YYYY\n"
        "Same date = one day. Example: 22.09.2026\n\n"
        "Cancel: /cancel"
    ),
    "time_off_invalid_date": "Invalid date format. Use DD.MM.YYYY",
    "time_off_invalid_range": "The end date must be on or after the start date.",
    "time_off_add_ok": "Time off added: {when}.",
    "time_off_cancelled": "Time off editing cancelled.",
    "time_off_delete_button": "🗑 {item}",
    "time_off_confirm_delete": "Delete {item}?",
    "time_off_confirm_yes": "Yes",
    "time_off_confirm_no": "No",
    "time_off_deleted": "Time off removed.",
    "time_off_delete_not_found": "Time off not found.",
    "services_add_button": "➕ Add",
    "services_close_button": "Close",
    "services_back_button": "← Back",
    "services_closed": "Services list closed.",
    "services_card": (
        "{title}\n"
        "Duration: {duration} min\n"
        "Price: {price}\n"
        "Status: {status}"
    ),
    "services_not_found": "Service not found.",
    "services_deactivate_button": "⏸ Deactivate",
    "services_activate_button": "▶️ Activate",
    "services_deactivated": "Service deactivated.",
    "services_activated": "Service activated.",
    "services_edit_button": "✏️ Edit",
    "edit_service_enter_title": (
        "Enter the new service name\n"
        "Current: {title}\n\n"
        "Cancel: /cancel"
    ),
    "edit_service_enter_duration": (
        "Enter the new duration in minutes\n"
        "Current: {duration}\n\n"
        "Cancel: /cancel"
    ),
    "edit_service_enter_price": (
        "Enter the new price (or - to clear)\n"
        "Current: {price}\n\n"
        "Cancel: /cancel"
    ),
    "edit_service_ok": "Service updated: {title}, {duration} min, {price}.",
    "edit_service_cancelled": "Editing cancelled.",
    "hub_title": "Main menu",
    "hub_settings_title": "Settings",
    "hub_profile_title": "Profile",
    "hub_schedule_title": "Schedule",
    "hub_moderation_title": "Moderation",
    "hub_back_button": "← Back",
    "hub_home_button": "⌂ Menu",
    "hub_book_button": "Book",
    "hub_my_bookings_button": "My bookings",
    "hub_today_button": "Today",
    "hub_services_button": "Services",
    "hub_schedule_section_button": "Schedule",
    "hub_profile_section_button": "Profile",
    "hub_settings_section_button": "Settings",
    "hub_moderation_section_button": "Moderation",
    "hub_working_hours_button": "Working hours",
    "hub_time_off_button": "Time off",
    "hub_profile_show_button": "Show profile",
    "hub_profile_edit_button": "Edit profile",
    "hub_lang_button": "Language",
    "hub_help_button": "Help",
    "hub_admin_user_button": "User card",
    "hub_admin_set_role_button": "Set role",
    "hub_admin_ban_button": "Ban user",
    "hub_admin_unban_button": "Unban user",
    "hub_my_bookings_opened": "Your bookings are below. Tap ⌂ Menu to return.",
    "hub_today_opened": "Today's appointments are below. Tap ⌂ Menu to return.",
    "hub_profile_edit_started": "Update your profile below. Tap ⌂ Menu to return.",
    "hub_profile_incomplete": "Your profile is incomplete. Fill it in below.",
    "/menu_description": "Open the main menu",
}
