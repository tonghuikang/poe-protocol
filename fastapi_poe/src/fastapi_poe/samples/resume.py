"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeHandler, run
from fastapi_poe.types import QueryRequest
from fastapi_poe.samples.assets.messages import IMAGE_PARSE_FAILURE_REPLY, UPDATE_IMAGE_PARSING, UPDATE_LLM_QUERY
from fastapi_poe.samples.assets.prompts import RESUME_PROMPT

class EchoHandler(PoeHandler):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        last_message = query.query[-1].content
        yield self.text_event(last_message)


if __name__ == "__main__":
    run(EchoHandler())


async def parse_document_from_url(url) -> Tuple[bool, str]:
    print(url)
    result = await asyncio.create_subprocess_exec('tesseract', url.strip(), '-', '--psm', '4',
                                                  stdout=subprocess.PIPE)
    stdout, _ = await result.communicate()
    if result.returncode != 0:
        return False, ""
    extracted_text = stdout.decode()
    return True, extracted_text


def process_message_with_gpt(message_history: List[dict[str, str]]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_history,
    )
    bot_statement = response['choices'][0]['message']['content']
    return bot_statement


async def handle_query(request: web.Request, params: dict[str, Any]) -> web.Response:
    user_statement: str = params["query"][-1]["content"]
    async with sse_response(request, response_cls=SSEResponse) as resp:
        meta = {
            "content_type": "text/markdown",
            "linkify": True,
            "refetch_settings": False,
            "server_message_id": request.app["message_id"],
        }
        request.app["message_id"] += 1
        await resp.send(json.dumps(meta), event="meta")

        if params['conversation'] not in image_url_cache:
            # TODO: validate user_statement is not malicious
            await resp.send(json.dumps({"text": UPDATE_IMAGE_PARSING}), event="text")
            success, resume_string = await parse_document_from_url(user_statement)
            if not success:
                await resp.send(json.dumps({"text": IMAGE_PARSE_FAILURE_REPLY}), event="text")
                await resp.send("{}", event="done")
                return
            await resp.send(json.dumps({"text": UPDATE_LLM_QUERY}), event="text")
            image_url_cache[params['conversation']] = user_statement
            user_statement = RESUME_PROMPT.format(resume_string)

        conversation_cache[params['conversation']].append(
            {"role": "user", "content": user_statement},
        )

        if openai.api_key:
            message_history = conversation_cache[params['conversation']]
            bot_statement = process_message_with_gpt(message_history)
            await resp.send(json.dumps({"text": bot_statement}), event="text")

            conversation_cache[params['conversation']].append(
                {"role": "assistant", "content": bot_statement},
            )

        await resp.send("{}", event="done")
