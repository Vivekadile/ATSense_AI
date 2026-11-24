from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

# The model truncates input at 256 word-pieces (~180 words), which would
# leave everything after the header of a resume unseen. Long text is split
# into word windows and the window embeddings are averaged.
CHUNK_WORDS = 150


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


def _chunks(text: str) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS)]


def get_embedding(text: str):
    vectors = get_model().encode(_chunks(text), normalize_embeddings=True)
    mean = np.mean(vectors, axis=0)
    return mean / (np.linalg.norm(mean) or 1.0)


def calculate_semantic_similarity(resume_text: str, job_description: str) -> float:
    if not resume_text.strip() or not job_description.strip():
        return 0.0

    similarity = float(np.dot(get_embedding(resume_text), get_embedding(job_description)))
    return round(max(0.0, min(1.0, similarity)) * 100, 2)
