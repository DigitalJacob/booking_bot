import re

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.profile import get_phone_kb, remove_kb
from app.bot.states.states import ProfileSG
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


profile_router = Router(name="client_profile")

_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def _profile_card(user: User, i18n: dict[str, str]) -> str:
    return i18n.get("profile_card").format(
        first_name=user.first_name or "-",
        last_name=user.last_name or "-",
        phone=user.phone or "-",
    )


async def _save_profile(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        phone: str,
) -> None:
    if user is None:
        await state.clear()
        await message.answer(
            text=i18n.get("book_need_start"),
            reply_markup=remove_kb(),
        )
        return

    data = await state.get_data()
    await repos.users.update_profile(
        user_id=user.user_id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=phone,
    )
    resume_book = bool(data.get("resume_book"))
    await state.clear()
    await message.answer(
        text=i18n.get("profile_saved"),
        reply_markup=remove_kb(),
    )
    if resume_book:
        await message.answer(text=i18n.get("profile_saved_continue_book"))


async def start_profile_flow(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        resume_book: bool = False,
) -> None:
    await state.clear()
    await state.set_state(ProfileSG.first_name)
    await state.update_data(resume_book=resume_book)
    await message.answer(text=i18n.get("profile_ask_first_name"))


@profile_router.message(Command(commands="profile"))
async def process_profile_command(
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return

    if user.profile_complete:
        await state.clear()
        await message.answer(text=_profile_card(user, i18n))
        await message.answer(text=i18n.get("profile_edit_hint"))
        return

    await start_profile_flow(
        message=message,
        state=state,
        i18n=i18n,
        resume_book=False,
    )


@profile_router.message(Command(commands="edit_profile"))
async def process_edit_profile_command(
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return
    await start_profile_flow(
        message=message,
        state=state,
        i18n=i18n,
        resume_book=False,
    )


@profile_router.message(Command(commands="cancel"), StateFilter(ProfileSG))
async def process_profile_cancel(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.clear()
    await message.answer(
        text=i18n.get("profile_cancelled"),
        reply_markup=remove_kb(),
    )


@profile_router.message(
    StateFilter(ProfileSG.first_name),
    F.text,
    ~F.text.startswith("/"),
)
async def process_first_name(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    first_name = (message.text or "").strip()
    if len(first_name) < 2:
        await message.answer(text=i18n.get("profile_invalid_name"))
        return
    await state.update_data(first_name=first_name)
    await state.set_state(ProfileSG.last_name)
    await message.answer(text=i18n.get("profile_ask_last_name"))


@profile_router.message(
    StateFilter(ProfileSG.last_name),
    F.text,
    ~F.text.startswith("/"),
)
async def process_last_name(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    last_name = (message.text or "").strip()
    if len(last_name) < 2:
        await message.answer(text=i18n.get("profile_invalid_name"))
        return
    await state.update_data(last_name=last_name)
    await state.set_state(ProfileSG.phone)
    await message.answer(
        text=i18n.get("profile_ask_phone"),
        reply_markup=get_phone_kb(i18n),
    )


@profile_router.message(StateFilter(ProfileSG.phone), F.contact)
async def process_phone_contact(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    contact = message.contact
    if contact is None or not contact.phone_number:
        await message.answer(text=i18n.get("profile_invalid_phone"))
        return

    if user is not None and contact.user_id and contact.user_id != user.user_id:
        await message.answer(text=i18n.get("profile_invalid_phone"))
        return

    await _save_profile(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        phone=contact.phone_number,
    )


@profile_router.message(
    StateFilter(ProfileSG.phone),
    F.text,
    ~F.text.startswith("/"),
)
async def process_phone_text(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    raw = (message.text or "").strip().replace(" ", "").replace("-", "")
    if not _PHONE_RE.match(raw):
        await message.answer(text=i18n.get("profile_invalid_phone"))
        return

    await _save_profile(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        phone=raw,
    )
