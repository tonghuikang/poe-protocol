from fastapi_poe import run
from fastapi_poe.samples.resume import EchoHandler

if __name__ == "__main__":
    run(EchoHandler())
