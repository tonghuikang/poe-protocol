from fastapi_poe import run

from .poe import LangChainCatBot

if __name__ == "__main__":
    run(LangChainCatBot())
