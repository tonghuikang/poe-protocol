"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import random
from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest

# introduction to be added https://i.imgur.com/xbXviUO.gif

EMOJI_MAP = {
    "🔥": ["https://i.imgur.com/lPHtYl9.gif", "https://i.imgur.com/aJ9Pnas.gif"],
    "💥": ["https://i.imgur.com/lPHtYl9.gif", "https://i.imgur.com/aJ9Pnas.gif"],
    "🧙‍♀️": ["https://i.imgur.com/lPHtYl9.gif", "https://i.imgur.com/aJ9Pnas.gif"],
    "😱": ["https://i.imgur.com/3YY02tm.gif", "https://i.imgur.com/hgphb9b.gif"],
    "🤗": ["https://i.imgur.com/nx8WjtW.gif"],
    "🙏": ["https://i.imgur.com/h9vDS5V.gif"],
    "🤩": ["https://i.imgur.com/RGlKI4T.gif"],
    "😎": ["https://i.imgur.com/4KeeXni.gif"],
    "🙈": ["https://i.imgur.com/zJKBaIP.gif"],
    "😍": ["https://i.imgur.com/7PzO0Tk.gif"],
    "👍": ["https://i.imgur.com/WA2STCk.gif"],
    "💪": ["https://i.imgur.com/WA2STCk.gif"],
}

AVAILABLE_EMOJIS = "\n".join(EMOJI_MAP.keys())

EMOJI_PROMPT_TEMPLATE = """
You will summarize the character reply with one of the following single emojis

{emoji_list}

<user_statement>
{user_statement}
</user_statement>

<character_reply>
{character_reply}
</character_reply>

Do not use the 🧙‍♀️ emoji.
""".strip()


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement = query.query[-1].content
        character_reply = ""
        async for msg in stream_request(query, "MeguminHelper", query.api_key):
            # Note: See https://poe.com/MeguminHelper for the system prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                character_reply += msg.text
                yield self.replace_response_event(character_reply)

        query.query[-1].content = EMOJI_PROMPT_TEMPLATE.format(
            user_statement=user_statement,
            character_reply=character_reply,
            emoji_list=AVAILABLE_EMOJIS,
        )
        query.query = [query.query[-1]]

        emoji_classification = ""
        async for msg in stream_request(query, "EmojiClassifier", query.api_key):
            # Note: See https://poe.com/EmojiClassifier for the system prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                emoji_classification += msg.text

        emoji_classification = emoji_classification.strip()
        print(emoji_classification)

        image_url_selection = EMOJI_MAP.get(emoji_classification)
        print(image_url_selection)
        if image_url_selection:
            image_url = random.choice(image_url_selection)
            yield self.text_event(f"\n![{emoji_classification}]({image_url})")


if __name__ == "__main__":
    run(EchoBot())
