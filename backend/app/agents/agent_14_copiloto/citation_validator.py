"""Citation extraction and grounding assessment for ENS copilot responses."""
import re

# Pattern for citations like [RD 311/2022 medida op.acc.6] or [CCN-STIC 804 seccion 5.2]
_CITATION_RE = re.compile(
    r'\[([^\]]{5,80})\]',
)

# Phrases indicating information was not found in corpus
_NOT_FOUND_PHRASES = [
    "no encontrado en el corpus",
    "no se encuentra en el corpus",
    "no aparece en el corpus",
    "no disponible en el corpus",
    "no encontrado en el contexto",
    "no se encuentra en el contexto",
]


def extract_citations(text: str) -> list[str]:
    """Extract bracketed citations from an LLM response.

    Looks for patterns like [RD 311/2022 medida op.acc.6] and returns
    the inner text of each bracket pair. Filters out very short matches
    (under 5 chars) to avoid false positives.

    Returns:
        List of citation strings found in the text.
    """
    matches = _CITATION_RE.findall(text)
    # Filter out things that look like list markers or noise
    return [m.strip() for m in matches if not m.strip().isdigit()]


def is_not_in_corpus(text: str) -> bool:
    """Detect if the response indicates information was not found.

    Checks for standard "no encontrado en el corpus" phrases that the
    system prompt instructs the LLM to use.

    Returns:
        True if the response indicates the info was not in the corpus.
    """
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in _NOT_FOUND_PHRASES)


def assess_grounding(
    answer: str,
    chunks_in_context: list,
    min_citation_ratio: float = 0.3,
) -> bool:
    """Evaluate whether a response is adequately grounded in the provided context.

    A response is considered low-grounding-confidence if:
    - No citations were found AND the response is not a "not in corpus" reply
    - The answer is very long (>500 chars) but has zero citations

    Args:
        answer: The LLM response text.
        chunks_in_context: The RAG chunks that were provided as context.
        min_citation_ratio: Not currently used, reserved for future scoring.

    Returns:
        True if grounding confidence is LOW (i.e., potentially hallucinated).
    """
    if is_not_in_corpus(answer):
        # "Not found" responses are grounded by definition
        return False

    citations = extract_citations(answer)

    if not citations and len(answer) > 100:
        # Non-trivial answer with zero citations -> low confidence
        return True

    if not chunks_in_context and not is_not_in_corpus(answer):
        # No context was provided but LLM gave an answer -> suspicious
        return True

    return False
