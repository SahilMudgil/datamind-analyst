import hashlib
import numpy as np
from typing import List
from config import settings

class EmbeddingService:
    def __init__(self):
        self.dimension = 768
        self.model_name = settings.EMBEDDING_MODEL

    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Generate a deterministic normalized 768-dim vector from text hash for offline/fallback use."""
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.randn(self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    async def get_embedding(self, text: str) -> List[float]:
        """Generate a 768-dimensional embedding vector for given text."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                import asyncio
                from google import genai
                from google.genai import types

                def _call_embed():
                    client = genai.Client(api_key=settings.GEMINI_API_KEY)
                    model_to_use = self.model_name or "text-embedding-004"
                    try:
                        config = types.EmbedContentConfig(output_dimensionality=self.dimension)
                        return client.models.embed_content(
                            model=model_to_use,
                            contents=text,
                            config=config
                        )
                    except Exception:
                        return client.models.embed_content(
                            model=model_to_use,
                            contents=text
                        )

                # Enforce a 4-second maximum timeout on the synchronous network call
                response = await asyncio.wait_for(asyncio.to_thread(_call_embed), timeout=4.0)

                values = None
                if response and hasattr(response, 'embedding') and hasattr(response.embedding, 'values'):
                    values = response.embedding.values
                elif response and hasattr(response, 'embeddings') and len(response.embeddings) > 0:
                    values = response.embeddings[0].values

                if values:
                    if len(values) > self.dimension:
                        values = values[:self.dimension]
                    elif len(values) < self.dimension:
                        values = list(values) + [0.0] * (self.dimension - len(values))
                    
                    arr = np.array(values, dtype=float)
                    norm = np.linalg.norm(arr)
                    if norm > 0:
                        return (arr / norm).tolist()
                    return list(values)
            except Exception:
                # If Gemini embedding hangs or fails, fall back to fast deterministic embedding
                pass

        return self._generate_fallback_embedding(text)

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = []
        for text in texts:
            emb = await self.get_embedding(text)
            embeddings.append(emb)
        return embeddings

embedding_service = EmbeddingService()
