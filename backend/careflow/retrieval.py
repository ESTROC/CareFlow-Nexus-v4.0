"""Transparent policy retrieval: TF-IDF-like lexical rank, no unverified generative citations."""
import math
import re
from collections import Counter
from .fixtures import POLICIES


def tokens(value: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9]+", value.lower())


def search_policies(query: str, limit: int = 2) -> list[dict]:
    query_terms = set(tokens(query))
    docs = [Counter(tokens(p["text"] + " " + p["name"])) for p in POLICIES]
    rankings = []
    for p, bag in zip(POLICIES, docs):
        score = 0.0
        length = max(sum(bag.values()), 1)
        for term in query_terms:
            df = sum(1 for d in docs if term in d)
            idf = math.log(1 + (len(docs) - df + .5) / (df + .5))
            tf = bag.get(term, 0)
            score += idf * (tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / 45))) if tf else 0
        rankings.append((score, p))
    return [dict(item, citation_id=item["id"], source_type="DEMO_POLICY") for score, item in
            sorted(rankings, key=lambda x: (-x[0], x[1]["id"]))[:limit] if score > 0]
