from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import AsyncIterable

import openai
import pdftotext
import pytesseract
import requests
from PIL import Image
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeHandler, run
from fastapi_poe.samples.assets.messages import (
    MULTIPLE_WORDS_FAILURE_REPLY,
    PARSE_FAILURE_REPLY,
    UPDATE_IMAGE_PARSING,
    UPDATE_LLM_QUERY,
)
from fastapi_poe.samples.assets.prompts import RESUME_PROMPT, SYSTEM_PROMPT
from fastapi_poe.types import QueryRequest

assert openai.api_key

async def parse_image_document_from_url(image_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(image_url.strip())
        img = Image.open(BytesIO(response.content))

        custom_config = "--psm 4"
        text = pytesseract.image_to_string(img, config=custom_config)
        return True, text
    except BaseException:
        return False, ""


async def parse_pdf_document_from_url(pdf_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(pdf_url)
        with BytesIO(response.content) as f:
            pdf = pdftotext.PDF(f)
        text = "\n\n".join(pdf)
        return True, text
    except requests.exceptions.MissingSchema:
        return False, ""
    except BaseException:
        return False, ""


def process_message_with_gpt(message_history: list[dict[str, str]]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=message_history, temperature=0.1
    )
    bot_statement = response["choices"][0]["message"]["content"]
    return bot_statement
