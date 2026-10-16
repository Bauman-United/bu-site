"""POST /partners — заявка «Стать партнёром» → личное сообщение владельцу от бота клуба."""

import logging
from typing import Annotated

from bu_core.settings import Settings, get_settings
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from bu_api.telegram_forms import FORM_RESPONSES, FormResult, deliver

log = logging.getLogger(__name__)
router = APIRouter()


class PartnerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    about: str = Field(min_length=10, max_length=2000)
    contact: str = Field(min_length=3, max_length=200)
    website: str = Field(default="", max_length=500)  # honeypot: люди его не видят


def format_message(form: PartnerRequest) -> str:
    return f"🤝 Заявка на партнёрство\nКонтакт: {form.contact}\nО себе и предложении:\n{form.about}"


@router.post("/partners", responses=FORM_RESPONSES)
def partners(
    form: PartnerRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FormResult:
    if form.website:
        log.info("partners: honeypot filled, dropped")
        return FormResult(ok=True)
    deliver(request, settings, "partners", format_message(form))
    return FormResult(ok=True)
