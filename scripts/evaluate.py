import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app"))

from backend.evaluation import score_case, summarize_results
from backend.retrieval import run_llm
from settings import Settings


def main() -> None:
    dataset_path = PROJECT_ROOT / "evals" / "dataset.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    settings = Settings()
    results = []

    for case in tqdm(cases, desc="Evaluating support cases", unit="case"):
        started_at = perf_counter()
        try:
            response = run_llm(case["question"], settings)
            answer = response["answer"]
            context = response["context"]
            error = None
        except Exception as exception:  # noqa: BLE001
            answer = ""
            context = []
            error = type(exception).__name__

        latency_seconds = perf_counter() - started_at
        scores = score_case(
            answer=answer,
            context=context,
            expected_section=case["expected_section"],
            should_abstain=case["should_abstain"],
        )
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "answer": answer,
                "expected_section": case["expected_section"],
                "should_abstain": case["should_abstain"],
                **scores,
                "latency_seconds": round(latency_seconds, 3),
                "error": error,
            }
        )

    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "chat_model": settings.ollama.llm_model,
        "embedding_model": settings.ollama.embedding_model,
        "top_k": 4,
        "summary": summarize_results(results),
        "results": results,
    }
    results_dir = PROJECT_ROOT / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = results_dir / f"evaluation_{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2))
    print(f"Report written to {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
