EN: dict[str, str] = {
    "/start": (
        "Hello!\n\n"
        "I am a booking bot for appointments with a specialist.\n\n"
        "Available commands:\n"
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
        "/add_slot — add a time slot\n"
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
        "/help — help\n"
        "/lang — interface language"
    ),
    "/help": (
        "I help you book a service and manage appointments.\n\n"
        "Commands:\n"
        "/start — restart the bot\n"
        "/book — book an appointment\n"
        "/my_bookings — my appointments\n"
        "/lang — interface language\n"
        "/help — this help"
    ),
    "/help_master": (
        "You are a specialist. Booking management:\n\n"
        "/today — today's appointments (confirm / cancel)\n"
        "/add_slot — add a free time slot\n"
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
        "/lang — interface language\n"
        "/help — this help"
    ),
    "client_booking_confirmed": (
        "Your appointment has been confirmed.\n\n"
        "Service: {title}\n"
        "When: {when}"
    ),
    "client_booking_cancelled_by_master": (
        "The specialist cancelled your appointment.\n\n"
        "Service: {title}\n"
        "When: {when}"
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
    "book_choose_slot": "Choose a time",
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
    "book_no_slots": "No free slots. Choose another day or service.",
    "book_use_buttons": "Please use the buttons below.",
    "book_back_button": "← Back",
    "book_cancel_button": "Cancel",
    "book_confirm_button": "Book",
    "service_button": "{title} · {duration} min",
    "book_slot_taken": "This slot is already taken. Please choose another time.",
    "book_slot_past": "This time has already passed.",
    "book_slot_not_found": "Slot not found.",
    "book_service_inactive": "This service is no longer available.",
    "book_service_not_found": "Service not found.",
    "book_mismatch": "This slot cannot be booked with the selected service.",
    "book_need_start": "Please send /start first",
    "/today_description": "Today's appointments",
    "master_today_header": "📅 Today's appointments:",
    "master_today_empty": "No appointments for today.",
    "master_today_item": "{time} — {title} ({status})\nClient: {client_id}",
    "status_pending": "pending",
    "status_confirmed": "confirmed",
    "status_cancelled": "cancelled",
    "master_confirm_button": "✅ Confirm",
    "master_cancel_button": "❌ Cancel",
    "master_confirmed": "Appointment #{id} confirmed.",
    "master_cancelled": "Appointment #{id} cancelled.",
    "master_action_failed": "Failed to perform action.",
    "master_close_button": "Close",
    "master_new_booking": (
        "🔔 New booking\n\n"
        "Service: {title}\n"
        "When: {when}\n"
        "Client: {client_id}\n\n"
        "Today's appointments: /today"
    ),
    "/add_slot_description": "Add a time slot",
    "add_slot_enter_date": (
        "Enter the slot date as DD.MM.YYYY\n"
        "Example: 05.09.2026\n\n"
        "Cancel: /cancel"
    ),
    "add_slot_enter_time": (
        "Enter the start time as HH:MM\n"
        "Example: 14:30\n\n"
        "Cancel: /cancel"
    ),
    "add_slot_enter_duration": (
        "Enter the slot duration in minutes\n"
        "Example: 60\n\n"
        "Cancel: /cancel"
    ),
    "add_slot_invalid_date": "Invalid date format. Use DD.MM.YYYY",
    "add_slot_invalid_time": "Invalid time format. Use HH:MM",
    "add_slot_invalid_duration": "Enter a whole number of minutes greater than 0",
    "add_slot_past": "Cannot create a slot in the past. Enter another date or time.",
    "add_slot_duplicate": "A slot at this time already exists.",
    "add_slot_ok": "Slot created: {when}, duration {duration} min.",
    "add_slot_cancelled": "Adding a slot was cancelled.",
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
    "book_slot_too_short": "This slot is shorter than the service duration. Choose another time.",
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
        "When: {when}\n"
        "Client: {client_id}"
    ),
}
