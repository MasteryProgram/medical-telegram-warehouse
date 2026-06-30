import subprocess
from pathlib import Path

from dagster import Definitions, job, op

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(command: str) -> str:
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), shell=True, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {command}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")
    return completed.stdout


@op
def execute_pipeline(context) -> str:
    steps = [
        "python src/scraper.py --demo --path data --limit 15",
        "python src/load_to_postgress.py --path data",
        "python src/yolo_detect.py --path data --output data/yolo_results.csv",
        "python src/load_to_postgress.py --path data",
        "cd medical_warehouse && dbt run && dbt test",
    ]
    for step in steps:
        context.log.info(f"Running step: {step}")
        output = _run(step)
        context.log.info(output)
    return "Pipeline completed successfully"


@job
def telegram_pipeline_job():
    execute_pipeline()


defs = Definitions(job=telegram_pipeline_job)
