import asyncio
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from typing import AsyncIterable

import openai
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.callbacks.manager import AsyncCallbackManager
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot
from fastapi_poe.types import QueryRequest

template = """You are an automated cat.

You can assist with a wide range of tasks, but you always respond in the style of a cat,
and you are easily distracted."""

key_cache = {}
conversation_start_index_map = defaultdict(int)

VALID_KEY_MESSAGE = textwrap.dedent(
    """
    Your key is valid.
    Please remember to DELETE the key at https://platform.openai.com/account/api-keys after use.
""".strip()
)


def is_key_valid(api_key):
    try:
        openai.api_key = api_key
        _ = openai.Model.list()
    except openai.error.AuthenticationError:
        return False
    return True


@dataclass
class LangChainCatBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        if query.user_id not in key_cache:
            api_key = query.query[-1].content.strip()
            if is_key_valid(api_key):
                yield self.text_event(VALID_KEY_MESSAGE)
                key_cache[query.user_id] = api_key
                conversation_start_index_map[query.conversation_id] = len(query.query)
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

        conversation_start_index = conversation_start_index_map[query.conversation_id]

        messages = [SystemMessage(content=template)]
        for message in query.query[conversation_start_index:]:
            if message.role == "bot":
                messages.append(AIMessage(content=message.content))
            elif message.role == "user":
                messages.append(HumanMessage(content=message.content))
        handler = AsyncIteratorCallbackHandler()
        chat = ChatOpenAI(
            openai_api_key=api_key,
            streaming=True,
            callback_manager=AsyncCallbackManager([handler]),
            temperature=0,
        )
        asyncio.create_task(chat.agenerate([messages]))
        async for token in handler.aiter():
            yield self.text_event(token)
