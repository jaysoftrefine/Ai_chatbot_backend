import json
import logging
from pathlib import Path
from typing import Any
from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.document_chunk import DocumentChunk
from app.services.rag.chunker import chunk_text
from app.services.rag.extractor import extract_text_from_file

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSION = 768


class RAGService:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self._api_key.strip())
        return self._client

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        batch_size = 20  # Gemini embedContent batch size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                config = types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSION)
                response = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=config,
                )
                for item in response.embeddings:
                    embeddings.append(list(item.values))
            except Exception as e:
                logger.error(f"Failed to generate embeddings batch: {e}", exc_info=True)
                raise

        return embeddings

    def index_file(
        self,
        db: Session,
        user_id: str,
        file_id: str | None,
        file_name: str,
        file_path: Path | str,
    ) -> int:
        """
        Extracts, chunks, embeds, and saves file chunks into PostgreSQL with pgvector.
        Returns the number of chunks indexed.
        """
        text = extract_text_from_file(file_path)
        if not text or not text.strip():
            logger.info(f"No extractable text found in file {file_name}")
            return 0

        chunks = chunk_text(text, chunk_size=800, chunk_overlap=150)
        if not chunks:
            return 0

        logger.info(f"Indexing {len(chunks)} chunks for file {file_name} (user_id={user_id})")

        # Delete existing chunks if this file was previously indexed
        if file_id:
            db.query(DocumentChunk).filter(
                DocumentChunk.file_id == file_id,
                DocumentChunk.user_id == user_id,
            ).delete()
            db.commit()

        # Generate embeddings in batch
        embeddings = self.generate_embeddings(chunks)

        db_chunks = []
        for idx, (chunk_content, emb) in enumerate(zip(chunks, embeddings)):
            chunk_record = DocumentChunk(
                user_id=user_id,
                file_id=file_id,
                file_name=file_name,
                chunk_index=idx,
                content=chunk_content,
                embedding=emb,
            )
            db_chunks.append(chunk_record)

        db.add_all(db_chunks)
        db.commit()
        logger.info(f"Successfully stored {len(db_chunks)} chunks for {file_name}")
        return len(db_chunks)

    def search_relevant_chunks(
        self,
        db: Session,
        user_id: str,
        query: str,
        top_k: int = 4,
        distance_threshold: float = 0.55,
    ) -> list[dict[str, Any]]:
        """
        Retrieves the top_k most similar document chunks for the given user.
        Uses cosine distance (DocumentChunk.embedding.cosine_distance).
        Lower distance = higher similarity.
        """
        if not query or not query.strip():
            return []

        try:
            query_embeddings = self.generate_embeddings([query])
            if not query_embeddings:
                return []
            query_vector = query_embeddings[0]

            # If running on SQLite (e.g. unit tests), compute cosine distance in Python
            if db.bind and db.bind.dialect.name == "sqlite":
                chunks = db.query(DocumentChunk).filter(DocumentChunk.user_id == user_id).all()
                if not chunks:
                    return []
                import math

                def cosine_dist(v1, v2):
                    dot = sum(a * b for a, b in zip(v1, v2))
                    norm1 = math.sqrt(sum(a * a for a in v1))
                    norm2 = math.sqrt(sum(b * b for b in v2))
                    if norm1 == 0 or norm2 == 0:
                        return 1.0
                    return 1.0 - (dot / (norm1 * norm2))

                scored = []
                for chunk in chunks:
                    c_emb = chunk.embedding
                    if isinstance(c_emb, str):
                        c_emb = json.loads(c_emb)
                    dist = cosine_dist(query_vector, c_emb)
                    if dist <= distance_threshold:
                        scored.append({
                            "file_id": chunk.file_id,
                            "file_name": chunk.file_name,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "distance": float(dist),
                            "similarity_score": round(1.0 - (float(dist) / 2.0), 3),
                        })
                scored.sort(key=lambda x: x["distance"])
                return scored[:top_k]

            # Vector cosine distance query in pgvector (PostgreSQL)
            distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)

            stmt = (
                select(DocumentChunk, distance_expr.label("distance"))
                .filter(DocumentChunk.user_id == user_id)
                .order_by(distance_expr.asc())
                .limit(top_k)
            )

            results = db.execute(stmt).all()

            matched = []
            for chunk, distance in results:
                if distance <= distance_threshold:
                    matched.append({
                        "file_id": chunk.file_id,
                        "file_name": chunk.file_name,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "distance": float(distance),
                        "similarity_score": round(1.0 - (float(distance) / 2.0), 3),
                    })

            return matched

        except Exception as e:
            logger.error(f"Error searching relevant chunks: {e}", exc_info=True)
            return []


rag_service = RAGService()
