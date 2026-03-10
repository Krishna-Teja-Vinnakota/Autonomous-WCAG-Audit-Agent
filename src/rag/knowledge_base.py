"""
STEP 4: WCAG RAG Knowledge Base
=================================
Handles embedding and retrieval of WCAG knowledge using:
  - Vertex AI text-embedding for generating embeddings
  - Pinecone for vector storage and retrieval

Two modes:
  1. Build: Embed all WCAG chunks and upsert to Pinecone (one-time)
  2. Query: Search for relevant WCAG techniques given an issue

API Keys Needed:
  - GCP credentials (for Vertex AI embeddings) — from .env
  - PINECONE_API_KEY — from .env
"""

import time
from typing import List, Dict, Optional
from loguru import logger

from config.settings import (
    GCP_PROJECT_ID, GCP_REGION,
    PINECONE_API_KEY, PINECONE_INDEX_NAME,
)
from src.rag.wcag_data_loader import WCAGChunk


# Embedding model config
EMBEDDING_MODEL = "text-embedding-005"
EMBEDDING_DIMENSION = 768
BATCH_SIZE = 20  # Vertex AI embedding batch limit


class WCAGKnowledgeBase:
    """
    WCAG knowledge base backed by Pinecone vector database.
    
    Usage:
        kb = WCAGKnowledgeBase()
        
        # One-time: Build the index
        kb.build_index(chunks)
        
        # During audit: Query for relevant techniques
        results = kb.query("Images missing alt text", criterion="1.1.1", top_k=5)
    """

    def __init__(self):
        self._pc = None
        self._index = None
        self._embed_model = None
        self._initialized = False

    def _init_pinecone(self):
        """Initialize Pinecone client and index."""
        if self._pc is not None:
            return

        from pinecone import Pinecone

        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not set in .env")

        self._pc = Pinecone(api_key=PINECONE_API_KEY)

        # Check if index exists
        existing = [idx.name for idx in self._pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            logger.info(f"  Creating Pinecone index: {PINECONE_INDEX_NAME}")
            from pinecone import ServerlessSpec
            self._pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            # Wait for index to be ready
            while not self._pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
                logger.info("  ⏳ Waiting for Pinecone index to be ready...")
                time.sleep(2)

        self._index = self._pc.Index(PINECONE_INDEX_NAME)
        logger.info(f"  ✅ Pinecone index ready: {PINECONE_INDEX_NAME}")

    def _init_embeddings(self):
        """Initialize Vertex AI embedding model."""
        if self._embed_model is not None:
            return

        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)
        self._embed_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
        logger.info(f"  ✅ Vertex AI embedding model ready: {EMBEDDING_MODEL}")

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts using Vertex AI."""
        self._init_embeddings()

        all_embeddings = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            embeddings = self._embed_model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])

            if i + BATCH_SIZE < len(texts):
                time.sleep(0.5)  # Rate limit

        return all_embeddings

    # ─── Build Index (One-Time) ───────────────────────────

    def build_index(self, chunks: List[WCAGChunk]):
        """
        Embed all WCAG chunks and upsert to Pinecone.
        Call this once to set up the knowledge base.
        """
        self._init_pinecone()
        self._init_embeddings()

        logger.info(f"\n📚 Building WCAG knowledge base ({len(chunks)} chunks)...")

        # Prepare texts for embedding
        texts = [chunk.text for chunk in chunks]

        # Embed in batches
        logger.info(f"  🔄 Embedding {len(texts)} chunks...")
        embeddings = self._embed_texts(texts)
        logger.info(f"  ✅ Embedded {len(embeddings)} chunks")

        # Prepare Pinecone vectors
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vectors.append({
                "id": chunk.chunk_id,
                "values": embedding,
                "metadata": {
                    "text": chunk.text[:4000],  # Pinecone metadata limit
                    "criterion_id": chunk.criterion_id,
                    "criterion_name": chunk.criterion_name,
                    "wcag_level": chunk.wcag_level,
                    "principle": chunk.principle,
                    "chunk_type": chunk.chunk_type,
                    "technique_id": chunk.technique_id,
                    "source_url": chunk.source_url,
                },
            })

        # Upsert in batches of 50
        logger.info(f"  🔄 Upserting to Pinecone...")
        for i in range(0, len(vectors), 50):
            batch = vectors[i:i + 50]
            self._index.upsert(vectors=batch)

        # Verify
        time.sleep(2)
        stats = self._index.describe_index_stats()
        logger.info(f"  ✅ Pinecone index stats: {stats.total_vector_count} vectors")
        logger.info(f"  ✅ Knowledge base built successfully!")

    # ─── Query (During Audit) ─────────────────────────────

    def query(
        self,
        issue_description: str,
        criterion_id: str = "",
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Query the knowledge base for relevant WCAG techniques/understanding.
        
        Args:
            issue_description: Description of the accessibility issue
            criterion_id: Optional WCAG criterion ID to filter by (e.g., "1.1.1")
            top_k: Number of results to return
            
        Returns:
            List of dicts with 'text', 'criterion_id', 'technique_id', 'score', etc.
        """
        self._init_pinecone()

        # Build query text
        query_text = issue_description
        if criterion_id:
            query_text = f"WCAG {criterion_id}: {issue_description}"

        # Embed query
        query_embedding = self._embed_texts([query_text])[0]

        # Build filter
        filter_dict = {}
        if criterion_id:
            filter_dict["criterion_id"] = {"$eq": criterion_id}

        # Query Pinecone
        results = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None,
        )

        # Parse results
        hits = []
        for match in results.matches:
            meta = match.metadata or {}
            hits.append({
                "text": meta.get("text", ""),
                "criterion_id": meta.get("criterion_id", ""),
                "criterion_name": meta.get("criterion_name", ""),
                "wcag_level": meta.get("wcag_level", ""),
                "principle": meta.get("principle", ""),
                "chunk_type": meta.get("chunk_type", ""),
                "technique_id": meta.get("technique_id", ""),
                "source_url": meta.get("source_url", ""),
                "score": match.score,
            })

        return hits

    def query_for_issue(
        self,
        title: str,
        description: str,
        wcag_criterion: str = "",
        top_k: int = 3,
    ) -> Dict:
        """
        High-level query for enriching an accessibility issue with WCAG knowledge.
        
        Returns a dict with:
          - techniques: List of relevant WCAG techniques
          - understanding: Understanding text for the criterion
          - fix_suggestions: Specific fix suggestions from techniques
        """
        query_text = f"{title}. {description}"

        # Query with criterion filter first
        results = self.query(query_text, criterion_id=wcag_criterion, top_k=top_k)

        # If few results with filter, try without
        if len(results) < 2 and wcag_criterion:
            broader = self.query(query_text, top_k=top_k)
            # Add non-duplicate broader results
            seen_ids = {r["technique_id"] for r in results if r["technique_id"]}
            for r in broader:
                if r["technique_id"] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r["technique_id"])

        # Organize results
        techniques = []
        understanding = ""
        fix_suggestions = []

        for r in results:
            if r["chunk_type"] == "technique" and r["score"] > 0.5:
                techniques.append({
                    "technique_id": r["technique_id"],
                    "text": r["text"],
                    "source_url": r["source_url"],
                })
                # Extract fix suggestion from technique text
                fix_text = r["text"]
                if "Example:" in fix_text:
                    fix_suggestions.append(fix_text[fix_text.index("Example:"):])
                elif "Fix:" in fix_text:
                    fix_suggestions.append(fix_text[fix_text.index("Fix:"):])

            elif r["chunk_type"] == "understanding" and r["score"] > 0.5:
                if not understanding:
                    understanding = r["text"]

            elif r["chunk_type"] == "failure" and r["score"] > 0.5:
                techniques.append({
                    "technique_id": r["technique_id"],
                    "text": r["text"],
                    "source_url": r["source_url"],
                })

        return {
            "techniques": techniques[:3],
            "understanding": understanding[:500] if understanding else "",
            "fix_suggestions": fix_suggestions[:2],
        }

    # ─── Status Check ─────────────────────────────────────

    def is_available(self) -> bool:
        """Check if the knowledge base is properly configured and has data."""
        if not PINECONE_API_KEY:
            return False
        try:
            self._init_pinecone()
            stats = self._index.describe_index_stats()
            return stats.total_vector_count > 0
        except Exception as e:
            logger.debug(f"RAG not available: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get knowledge base statistics."""
        self._init_pinecone()
        stats = self._index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "index_name": PINECONE_INDEX_NAME,
            "dimension": EMBEDDING_DIMENSION,
        }