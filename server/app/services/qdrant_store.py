from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from app.core.config import settings

COLLECTION = "knowledge"


class VectorStore:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)

    def ensure(self, dim: int = 1024):
        try:
            names = {c.name for c in self.client.get_collections().collections}
            if COLLECTION not in names:
                self.client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
                    optimizers_config=qm.OptimizersConfigDiff(indexing_threshold=20000),
                )
        except Exception:
            pass

    def upsert(self, ids, vectors, payloads):
        self.client.upsert(
            collection_name=COLLECTION,
            points=qm.Batch(ids=ids, vectors=vectors, payloads=payloads),
        )

    def search(self, vector, top_k=8, query_filter=None):
        return self.client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )


store = VectorStore()
