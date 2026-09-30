from backend.evaluation import score_case, summarize_results
from langchain_core.documents import Document


def test_score_case_checks_expected_section_and_abstention() -> None:
    result = score_case(
        answer="I don't know based on the available support information.",
        context=[Document(page_content="Section: Pricing > Refund Policy")],
        expected_section="Refund Policy",
        should_abstain=True,
    )

    assert result == {
        "section_hit": True,
        "abstained": True,
        "abstention_correct": True,
    }


def test_summarize_results_reports_rates_latency_and_failures() -> None:
    results = [
        {
            "section_hit": True,
            "abstention_correct": True,
            "latency_seconds": 2.0,
            "error": None,
        },
        {
            "section_hit": None,
            "abstention_correct": False,
            "latency_seconds": 4.0,
            "error": "model unavailable",
        },
    ]

    assert summarize_results(results) == {
        "cases": 2,
        "section_hit_rate": 1.0,
        "abstention_accuracy": 0.5,
        "average_latency_seconds": 3.0,
        "failures": 1,
    }
