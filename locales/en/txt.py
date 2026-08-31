EN: dict[str, str] = {
    "/start": (
        "Hello!\n\n"
        "I am a booking bot for appointments with a specialist.\n\n"
        "Available commands:\n"
        "/book — book an appointment\n"
        "/help — help\n"
        "/lang — interface language"
    ),
    "/help": (
        "I help you book a service and manage appointments.\n\n"
        "Commands:\n"
        "/start — restart the bot\n"
        "/book — book an appointment\n"
        "/lang — interface language\n"
        "/help — this help"
    ),
    "/help_admin": (
        "You are a bot administrator.\n\n"
        "Commands:\n"
        "/start — restart the bot\n"
        "/book — book an appointment\n"
        "/lang — interface language\n"
        "/help — this help"
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
}