"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

from collections import defaultdict
from typing import AsyncIterable

import openai
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeHandler, run
from fastapi_poe.samples.assets.messages import (
    MULTIPLE_WORDS_FAILURE_REPLY,
    PARSE_FAILURE_REPLY,
    UPDATE_IMAGE_PARSING,
    UPDATE_LLM_QUERY,
)
from fastapi_poe.samples.assets.prompts import RESUME_PROMPT, SYSTEM_PROMPT
from fastapi_poe.samples.utils import (
    parse_image_document_from_url,
    parse_pdf_document_from_url,
    process_message_with_gpt,
)
from fastapi_poe.types import QueryRequest

assert openai.api_key


SETTINGS = {
    "report_feedback": True,
    "context_clear_window_secs": 60 * 60,
    "allow_user_context_clear": True,
}

conversation_cache = defaultdict(lambda: [{"role": "system", "content": SYSTEM_PROMPT}])

url_cache = {}


class ResumeHandler(PoeHandler):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement: str = query.query[-1].content
        print(query.conversation_id, user_statement)

        if query.conversation_id not in url_cache:
            # TODO: validate user_statement is not malicious
            if len(user_statement.strip().split()) > 1:
                yield self.text_event(MULTIPLE_WORDS_FAILURE_REPLY)
                return

            content_url = user_statement.strip()
            content_url = content_url.split("?")[0]  # remove query_params

            yield self.text_event(UPDATE_IMAGE_PARSING)

            if content_url.endswith(".pdf"):
                success, resume_string = await parse_pdf_document_from_url(content_url)
            else:  # assume image
                success, resume_string = await parse_image_document_from_url(
                    content_url
                )

            if not success:
                yield self.text_event(PARSE_FAILURE_REPLY)
                return
            yield self.text_event(UPDATE_LLM_QUERY)
            url_cache[query.conversation_id] = content_url
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
