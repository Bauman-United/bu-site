"""POST /join — заявка «Хочу в команду» → личное сообщение владельцу от бота клуба."""

import logging
from typing import Annotated, Literal

from bu_core.settings import Settings, get_settings
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from bu_api.telegram_forms import FORM_RESPONSES, FormResult, deliver

log = logging.getLogger(__name__)
router = APIRouter()


class JoinRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    position: Literal["Вратарь", "Защитник", "Полузащитник", "Нападающий", "Пока не знаю"]
    experience: str = Field(min_length=10, max_length=1500)
    bauman: Literal["Да, учусь", "Выпускник", "Нет"]
    age: int = Field(ge=14, le=70)
    contact: str = Field(min_length=3, max_length=200)
    website: str = Field(default="", max_length=500)  # honeypot: люди его не видят


def format_message(form: JoinRequest) -> str:
    return (
        "⚽ Новая заявка в команду\n"
        f"Имя: {form.name}\n"
        f"Позиция: {form.position}\n"
        f"Возраст: {form.age}\n"
        f"Бауманка: {form.bauman}\n"
        f"Контакт: {form.contact}\n"
        f"Опыт:\n{form.experience}"
    )


@router.post("/join", responses=FORM_RESPONSES)
def join(
    form: JoinRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FormResult:
    if form.website:
        log.info("join: honeypot filled, dropped")
        return FormResult(ok=True)
    deliver(request, settings, "join", format_message(form))
    return FormResult(ok=True)
