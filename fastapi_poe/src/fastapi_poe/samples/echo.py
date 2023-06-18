"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import AsyncIterable
from urllib.parse import urlparse, urlunparse

import openai
import requests
from bs4 import BeautifulSoup
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest

if os.environ.get("OPENAI_API_KEY"):
    openai.api_key = os.environ["OPENAI_API_KEY"]
else:
    print("You need an OpenAI API key to start this API bot.")
    sys.exit(1)

try:
    models = openai.Model.list()
except openai.error.AuthenticationError:
    print("You need a valid OpenAI API key")
    sys.exit(1)


SYSTEM_PROMPT = """
You are a copywriter that writes a meaningful question and an authentic promoted answer on Quora.

Always reply in the following format

<question>
---
<answer>
""".strip()


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
- Include a [markdown](backlink) to the product at the end of the answer.

Reply exactly in the following format

<question>
---
<answer>""".strip()


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


conversation_cache = defaultdict(lambda: [{"role": "system", "content": SYSTEM_PROMPT}])


def process_message_with_gpt(message_history: list[dict[str, str]]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=message_history, temperature=0.1
    )
    bot_statement = response["choices"][0]["message"]["content"]
    return bot_statement


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        if query.conversation_id not in conversation_cache:
            url = query.query[-1].content.strip()
            url = resolve_url_scheme(url)
            content = extract_readable_text(url)
            if content is None:
                yield self.text_event(
                    "Please submit an URL that you want to create a promoted answer for."
                )
                return
            user_statement = PROMPT_TEMPLATE.format(content=content, url=url)

        else:
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
