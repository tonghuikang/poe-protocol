"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent
from wasmtime import Config, Engine, Linker, Module, Store, WasiConfig

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest

STDIO_PREFIXES = [
    "./src/fastapi_poe/samples/test001",
    "./src/fastapi_poe/samples/test002",
    "./src/fastapi_poe/samples/test003",
]
TOTAL_FUEL = 4_000_000_000


def run_code(code, stdin_file=None):
    fuel = TOTAL_FUEL

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


def validate_output(captured_output, expected_output) -> bool:
    return captured_output.strip() == expected_output.strip()


def format_output(
    captured_output, captured_error, fuel_consumed, output_correctness
) -> str:
    lines = []
    if output_correctness:
        line = "Output is CORRECT"
        lines.append(line)
    elif fuel_consumed >= TOTAL_FUEL:
        line = "Time Limit Exceeded"
        lines.append(line)
    else:
        line = "Output is WRONG"
        lines.append(line)

    if captured_output:
        line = f"\n```output\n{captured_output}\n```"
        lines.append(line)

    if captured_error:
        line = f"\n```error\n{captured_error}\n```"
        lines.append(line)

    line = f"Fuel consumed: {fuel_consumed:_}"
    lines.append(line)

    return "\n".join(lines)


async def judge_case(code, stdio_prefix=None):
    stdin_file = stdio_prefix + ".in"
    expected_stdout_file = stdio_prefix + ".out"

    (captured_output, captured_error, size, data_len, fuel_consumed) = run_code(
        code, stdin_file
    )

    with open(expected_stdout_file) as f:
        expected_output = f.read()

    output_correctness = validate_output(captured_output, expected_output)

    return format_output(
        captured_output, captured_error, fuel_consumed, output_correctness
    )


async def judge_cases(code):
    # Redirect stdout temporarily to capture the output of the code snippet

    tasks = [
        asyncio.create_task(judge_case(code, stdio_prefix))
        for stdio_prefix in STDIO_PREFIXES
    ]

    results = await asyncio.gather(*tasks)

    return "\n\n---\n".join(results)


def strip_code(code):
    if len(code.strip()) < 6:
        return code
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3]
    return code


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        code = query.query[-1].content
        code = strip_code(code)
        reply_string = await judge_cases(code)
        yield self.text_event(reply_string)


if __name__ == "__main__":
    run(EchoBot())
