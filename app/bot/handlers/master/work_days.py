from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.hub import get_hub_back_home_kb
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User


async def _hub_work_days(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        **_,
) -> None:
    """Placeholder until the monthly work-days FSM lands."""
    if user.role != UserRole.MASTER:
        return
    await state.update_data(
        hub_screen="work_days",
        hub_back="schedule",
        list_return="schedule",
    )
    await message.edit_text(
        text=i18n.get("work_days_stub"),
        reply_markup=get_hub_back_home_kb(i18n),
    )


register("work_days", _hub_work_days)
