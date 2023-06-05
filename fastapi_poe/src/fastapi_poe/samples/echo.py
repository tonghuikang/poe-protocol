"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent
from wasmtime import Config, Engine, Linker, Module, Store, WasiConfig

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest

TESTCASE_FILES = ["test001", "test002"]


def run_code(code, stdin_file=None):
    fuel = 4_000_000_000

    engine_cfg = Config()
    engine_cfg.consume_fuel = True
    engine_cfg.cache = True

    linker = Linker(Engine(engine_cfg))
    linker.define_wasi()

    python_module = Module.from_file(linker.engine, "bin/python-3.11.1.wasm")

    config = WasiConfig()

    config.argv = ("python", "-c", code)
    config.preopen_dir(".", "/")

    with tempfile.TemporaryDirectory() as chroot:
        out_log = os.path.join(chroot, "out.log")
        err_log = os.path.join(chroot, "err.log")
        config.stdin_file = stdin_file
        config.stdout_file = out_log
        config.stderr_file = err_log

        store = Store(linker.engine)

        # Limits how many instructions can be executed:
        store.add_fuel(fuel)
        store.set_wasi(config)
        instance = linker.instantiate(store, python_module)

        # _start is the default wasi main function
        start = instance.exports(store)["_start"]

        mem = instance.exports(store)["memory"]

        error = None
        try:
            start(store)
        except Exception:
            with open(err_log) as f:
                error = f.read()

        with open(out_log) as f:
            result = f.read()

        return (
            result,
            error,
            mem.size(store),
            mem.data_len(store),
            store.fuel_consumed(),
        )


async def execute_code(code):
    # Redirect stdout temporarily to capture the output of the code snippet
    captured_output, captured_error = "", ""

    loop = asyncio.get_event_loop()
    (
        captured_output,
        captured_error,
        size,
        data_len,
        fuel_consumed,
    ) = await loop.run_in_executor(
        None, run_code, code, "./src/fastapi_poe/samples/test003.in"
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

        if captured_error:
            captured_error = strip_colors(captured_error)
            captured_error = wrap_text_in_code_block(captured_error)
            yield self.text_event(captured_error)


if __name__ == "__main__":
    run(EchoBot())
