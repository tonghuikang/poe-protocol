from fastapi_poe import run
from fastapi_poe.samples.resume import ResumeHandler

if __name__ == "__main__":
    run(ResumeHandler(), allow_without_key=True)
