"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import AsyncIterable

import openai
import pytesseract
import requests
from PIL import Image
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeHandler, run
from fastapi_poe.samples.assets.messages import (
    IMAGE_PARSE_FAILURE_REPLY,
    UPDATE_IMAGE_PARSING,
    UPDATE_LLM_QUERY,
)
from fastapi_poe.samples.assets.prompts import RESUME_PROMPT, SYSTEM_PROMPT
from fastapi_poe.types import QueryRequest

assert openai.api_key


SETTINGS = {
    "report_feedback": True,
    "context_clear_window_secs": 60 * 60,
    "allow_user_context_clear": True,
}

conversation_cache = defaultdict(lambda: [{"role": "system", "content": SYSTEM_PROMPT}])

image_url_cache = {}


class ResumeHandler(PoeHandler):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement = query.query[-1].content
        print(query.conversation_id, user_statement)

        if query.conversation_id not in image_url_cache:
            # TODO: validate user_statement is not malicious
            yield self.text_event(UPDATE_IMAGE_PARSING)
            success, resume_string = await parse_document_from_url(user_statement)
            if not success:
                yield self.text_event(IMAGE_PARSE_FAILURE_REPLY)
                return
            yield self.text_event(UPDATE_LLM_QUERY)
            image_url_cache[query.conversation_id] = user_statement
            user_statement = RESUME_PROMPT.format(resume_string)

        conversation_cache[query.conversation_id].append(
            {"role": "user", "content": user_statement}
        )

        message_history = conversation_cache[query.conversation_id]
        bot_statement = process_message_with_gpt(message_history)
        yield self.text_event(bot_statement)

        conversation_cache[query.conversation_id].append(
            {"role": "assistant", "content": bot_statement}
        )


if __name__ == "__main__":
    run(ResumeHandler())


async def parse_document_from_url(image_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(image_url.strip())
        img = Image.open(BytesIO(response.content))

        custom_config = "--psm 4"
        text = pytesseract.image_to_string(img, config=custom_config)
        return True, text
    except requests.exceptions.MissingSchema:
        return False, ""


def process_message_with_gpt(message_history: list[dict[str, str]]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=message_history, temperature=0.1
    )
    bot_statement = response["choices"][0]["message"]["content"]
    return bot_statement
