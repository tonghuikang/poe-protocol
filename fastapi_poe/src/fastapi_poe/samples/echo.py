"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import asyncio
import re
import sys
import traceback
from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent
from wasm_exec import WasmExecutor

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest


async def execute_code(code):
    # Redirect stdout temporarily to capture the output of the code snippet
    captured_output, captured_error = "", ""

    try:
        # Create an event loop and use it to run WasmExecutor asynchronously
        loop = asyncio.get_event_loop()
        wasm = WasmExecutor()
        result = await loop.run_in_executor(None, wasm.exec, code)
        captured_output = result.text
    except Exception:
        # Capture the exception and its traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()

        # Format the traceback as a string
        captured_error = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )

    return captured_output, captured_error


def strip_code(code):
    if len(code.strip()) < 6:
        return code
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3]
    return code


def strip_colors(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def wrap_text_in_code_block(text):
    return "\n```\n" + text + "\n```\n"


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        code = query.query[-1].content
        code = strip_code(code)
        captured_output, captured_error = await execute_code(code)

        if not captured_output and not captured_error:
            yield self.text_event("No output or error recorded.")

        if captured_output:
            captured_output = strip_colors(captured_output)
            captured_output = wrap_text_in_code_block(captured_output)
            yield self.text_event(captured_output)

        if not captured_output and captured_error:
            captured_error = strip_colors(captured_error)
            captured_error = wrap_text_in_code_block(captured_error)
            yield self.text_event(captured_error)


if __name__ == "__main__":
    run(EchoBot())
