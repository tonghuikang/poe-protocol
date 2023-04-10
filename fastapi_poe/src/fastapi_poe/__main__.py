from fastapi_poe import run_multiple
from fastapi_poe.samples.resume import ResumeHandler

if __name__ == "__main__":
    run_multiple({"resume": ResumeHandler(), "paper": ResumeHandler()})
