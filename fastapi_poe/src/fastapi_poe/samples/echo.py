"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import textwrap
from collections import defaultdict
from typing import AsyncIterable

import openai
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest

key_cache = {}
conversation_cache = defaultdict(
    lambda: [{"role": "system", "content": "You are a helpful AI assistant."}]
)

VALID_KEY_MESSAGE = textwrap.dedent(
    """
    Your key is valid.
    Please remember to DELETE the key at https://platform.openai.com/account/api-keys after use.
""".strip()
)


def is_key_valid(api_key):
    try:
        openai.api_key = api_key
        models = openai.Model.list()
    except openai.error.AuthenticationError:
        return False
    return True


def process_message_with_gpt(message_history: list[dict[str, str]]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=message_history, temperature=0.1
    )
    bot_statement = response["choices"][0]["message"]["content"]
    return bot_statement


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        if query.user_id not in key_cache:
            api_key = query.query[-1].content.strip()
            if is_key_valid(api_key):
                yield self.text_event(VALID_KEY_MESSAGE)
                key_cache[query.user_id] = api_key
            else:
                yield self.text_event("Please enter your OpenAI API key.")
            return
        else:
            api_key = key_cache[query.user_id]
            if not is_key_valid(api_key):
                yield self.text_event(
                    "Your key has expired. Please enter your OpenAI API key."
                )
                del key_cache[query.user_id]
                return

        user_statement = query.query[-1].content

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
    run(EchoBot())
