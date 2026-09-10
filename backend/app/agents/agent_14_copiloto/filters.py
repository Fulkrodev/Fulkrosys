"""Deterministic filter detection from user questions for ENS copilot."""
import re
from dataclasses import dataclass, field

# ENS measure code pattern: org.N, op.pl.N, op.acc.N, mp.if.N, etc.
_MEASURE_CODE_RE = re.compile(
    r'\b(org\.\d+|op\.(?:pl|acc|exp|ext|nub|cont|mon)\.\d+|mp\.(?:if|per|eq|com|si|sw|info|s)\.\d+)\b',
    re.IGNORECASE,
)

# "medida" keyword (singular or plural)
_MEDIDA_KW_RE = re.compile(r'\bmedidas?\b', re.IGNORECASE)

# RD 311/2022 or "el RD" or "Real Decreto"
_RD_311_RE = re.compile(
    r'\b(?:RD\s*311[/ ]2022|el\s+RD|Real\s+Decreto)\b',
    re.IGNORECASE,
)

# CCN-STIC followed by a 3-4 digit guide number
_CCN_STIC_RE = re.compile(r'\bCCN[-\s]?STIC[-\s]?(\d{3,4})\b', re.IGNORECASE)

# Other frameworks
_FRAMEWORK_MAP = {
    'NIST': re.compile(r'\bNIST\b', re.IGNORECASE),
    'RGPD': re.compile(r'\bRGPD\b', re.IGNORECASE),
    'MAGERIT': re.compile(r'\bMAGERIT\b', re.IGNORECASE),
    'DORA': re.compile(r'\bDORA\b', re.IGNORECASE),
    'NIS2': re.compile(r'\bNIS[-\s]?2\b', re.IGNORECASE),
}


@dataclass
class DetectedFilters:
    """Filters detected from a user question."""

    only_with_measure_code: bool = False
    source_codes: list[str] = field(default_factory=list)
    measure_codes_mentioned: list[str] = field(default_factory=list)


def detect_filters(question: str) -> DetectedFilters:
    """Analyze a user question and return deterministic search filters.

    Detects ENS measure codes, RD 311/2022 references, CCN-STIC guide
    numbers, and other framework keywords. Returns a DetectedFilters
    object that can be unpacked into corpus_search() parameters.
    """
    result = DetectedFilters()

    # 1. Detect measure codes
    measure_matches = _MEASURE_CODE_RE.findall(question)
    if measure_matches:
        result.only_with_measure_code = True
        result.measure_codes_mentioned = [m.lower() for m in measure_matches]

    # 2. "medida" keyword implies measure-code filter
    if _MEDIDA_KW_RE.search(question):
        result.only_with_measure_code = True

    # 3. RD 311/2022
    if _RD_311_RE.search(question):
        if 'RD_311_2022' not in result.source_codes:
            result.source_codes.append('RD_311_2022')

    # 4. CCN-STIC guides
    ccn_matches = _CCN_STIC_RE.findall(question)
    for guide_num in ccn_matches:
        code = f'CCN_STIC_{guide_num}'
        if code not in result.source_codes:
            result.source_codes.append(code)

    # 5. Other frameworks
    for fw_name, pattern in _FRAMEWORK_MAP.items():
        if pattern.search(question):
            if fw_name not in result.source_codes:
                result.source_codes.append(fw_name)

    return result
