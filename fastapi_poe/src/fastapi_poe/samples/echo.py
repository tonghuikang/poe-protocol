"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

from typing import AsyncIterable
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest

PROMPT_TEMPLATE = """
You are given the the content from the url {url}.
The owner of the site wants to promote their site on Quora, a question-and-answer site.

<content>
{content}
</content>

Write a meaningful question
- Do not mention the product in the question.

Write an authentic answer
- Do not promote the product early.
- Break down the answer into smaller paragraphs.
- Include a [markdown](backlink) to the product at the end of the answer, organically.

Reply EXACTLY in the following markdown format. Do not add words.

<question>
---
<answer>""".strip()

conversation_cache = set()


def resolve_url_scheme(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme="https")
    resolved_url = urlunparse(parsed_url)
    resolved_url = resolved_url.replace(":///", "://")
    return resolved_url


def insert_newlines(element):
    block_level_elements = [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "figure",
    ]

    for tag in element.find_all(block_level_elements):
        if tag.get_text(strip=True):
            tag.insert_before("\n")
            tag.insert_after("\n")


def extract_readable_text(url):
    try:
        response = requests.get(url)
    except requests.exceptions.InvalidURL:
        print(f"URL is invalid: {url}")
        return None
    except Exception:
        print(f"Unable to load URL: {url}")
        return None

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        insert_newlines(soup)

        readable_text = soup.get_text()

        # Clean up extra whitespaces without collapsing newlines
        readable_text = "\n".join(
            " ".join(line.split()) for line in readable_text.split("\n")
        )

        return readable_text

    else:
        print(f"Request failed with status code {response.status_code}")
        return None


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        if query.conversation_id not in conversation_cache:
            url = query.query[-1].content.strip()
            url = resolve_url_scheme(url)
            yield self.replace_response_event(f"Attempting to load [{url}]({url}) ...")
            content = extract_readable_text(url)
            content = content[:8000]  # Trying to approximate the limit
            if content is None:
                yield self.replace_response_event(
                    "Please submit an URL that you want to create a promoted answer for."
                )
                return

            # replace last message with the prompt
            query.query[-1].content = PROMPT_TEMPLATE.format(content=content, url=url)
            conversation_cache.add(query.conversation_id)
            yield self.replace_response_event("")

        current_message = ""

        async for msg in stream_request(query, "AnswerPromoted", query.api_key):
            # Note: See https://poe.com/AnswerPromoted for the prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                current_message += msg.text
                yield self.replace_response_event(current_message)


if __name__ == "__main__":
    run(EchoBot())
