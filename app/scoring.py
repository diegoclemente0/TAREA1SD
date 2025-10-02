import difflib

def semantic_score(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()

def rouge_l_f1(a: str, b: str) -> float:
    seq = difflib.SequenceMatcher(None, a or "", b or "")
    lcs = sum(triple.size for triple in seq.get_matching_blocks())
    if lcs == 0:
        return 0.0
    prec = lcs / max(1, len(a or ""))
    rec = lcs / max(1, len(b or ""))
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)

def combined_score(a: str, b: str, alpha: float = 0.7):
    sem = semantic_score(a,b)
    rouge = rouge_l_f1(a,b)
    combined = alpha * sem + (1 - alpha) * rouge
    return combined, sem, rouge
