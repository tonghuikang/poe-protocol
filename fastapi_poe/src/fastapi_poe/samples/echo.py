"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

import linecache
import sys
import traceback
from io import StringIO
from typing import AsyncIterable

from IPython import get_ipython
from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest

ipython = get_ipython()

if ipython is None:
    # This means the script is being run outside an IPython environment
    from IPython.terminal.embed import InteractiveShellEmbed

    ipython = InteractiveShellEmbed()


def execute_code(code):
    # Redirect stdout temporarily to capture the output of the code snippet
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # Execute the code with the silent parameter set to True
    result = ipython.run_cell(
        code, silent=True, store_history=False, shell_futures=False
    )

    # Restore the original stdout and retrieve the captured output
    captured_output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    # Check if there is an error and capture the error message
    captured_error = ""
    result_error = result.error_before_exec or result.error_in_exec
    if result_error is not None:
        etype, evalue, tb = type(result_error), result_error, result_error.__traceback__
        captured_error = "".join(traceback.format_exception(etype, evalue, tb))

        # Add additional lines of context for each traceback level
        tb_info = traceback.extract_tb(tb)
        if result.error_in_exec:
            captured_error += "\n\nAdditional context for each traceback level:\n"
            for level, (filename, lineno, func, _) in enumerate(tb_info[1:], start=1):
                context_before = max(1, lineno - 3)
                context_after = lineno + 3
                lines = [
                    linecache.getline(filename, i).rstrip()
                    for i in range(context_before, context_after + 1)
                ]
                formatted_lines = [
                    f"{i}: {line}" for i, line in enumerate(lines, start=context_before)
                ]
                captured_error += (
                    f"\nLevel {level} ({filename}, line {lineno}, in {func}):\n"
                    + "\n".join(formatted_lines)
                    + "\n"
                )

    return captured_output, captured_error


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
        captured_output, captured_error = execute_code(code)
        yield self.text_event(captured_output)


if __name__ == "__main__":
    run(EchoBot())
