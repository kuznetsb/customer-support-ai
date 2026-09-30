from langchain_core.documents import Document

ABSTENTION_PHRASE = "don't know based on the available support information"


def score_case(
    *,
    answer: str,
    context: list[Document],
    expected_section: str | None,
    should_abstain: bool,
) -> dict[str, bool | None]:
    """Score section retrieval and the expected abstention behavior."""
    section_hit = (
        None
        if expected_section is None
        else any(
            expected_section.casefold() in document.page_content.casefold()
            for document in context
        )
    )
    abstained = ABSTENTION_PHRASE in answer.casefold()
    return {
        "section_hit": section_hit,
        "abstained": abstained,
        "abstention_correct": abstained == should_abstain,
    }


def summarize_results(results: list[dict]) -> dict[str, float | int | None]:
    """Summarize section retrieval, abstention, latency, and failures."""
    section_results = [result["section_hit"] for result in results]
    section_results = [hit for hit in section_results if hit is not None]
    abstention_results = [result["abstention_correct"] for result in results]

    return {
        "cases": len(results),
        "section_hit_rate": (
            sum(section_results) / len(section_results) if section_results else None
        ),
        "abstention_accuracy": (
            sum(abstention_results) / len(abstention_results)
            if abstention_results
            else None
        ),
        "average_latency_seconds": (
            sum(result["latency_seconds"] for result in results) / len(results)
            if results
            else None
        ),
        "failures": sum(result["error"] is not None for result in results),
    }
