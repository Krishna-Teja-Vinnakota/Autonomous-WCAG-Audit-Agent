#!/usr/bin/env python3
"""
Build WCAG Knowledge Base
==========================
One-time setup script that:
  1. Loads WCAG 2.2 knowledge (criteria, techniques, understanding docs)
  2. Embeds all chunks using Vertex AI text-embedding-005
  3. Upserts to Pinecone vector database

Prerequisites:
  - .env configured with:
    - GCP_PROJECT_ID + GOOGLE_APPLICATION_CREDENTIALS (for Vertex AI embeddings)
    - PINECONE_API_KEY + PINECONE_INDEX_NAME (for vector storage)
  
Usage:
    python build_knowledge_base.py

After running this once, the RAG will be available during audits.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    validate_vertex_ai, print_config,
    PINECONE_API_KEY, PINECONE_INDEX_NAME,
)
from src.rag.wcag_data_loader import WCAGDataLoader
from src.rag.knowledge_base import WCAGKnowledgeBase


def main():
    print("""
╔══════════════════════════════════════════════════╗
║     WCAG Knowledge Base Builder                  ║
║     Embed WCAG 2.2 docs → Pinecone              ║
╚══════════════════════════════════════════════════╝
""")

    # Validate credentials
    validate_vertex_ai()

    if not PINECONE_API_KEY:
        print("❌ ERROR: PINECONE_API_KEY not set in .env")
        print("   Get a free API key at: https://www.pinecone.io/")
        sys.exit(1)

    print(f"  Pinecone Index:  {PINECONE_INDEX_NAME}")
    print_config()
    print()

    # 1. Load WCAG knowledge
    loader = WCAGDataLoader()
    chunks = loader.load_all()

    # Save chunks locally for inspection
    chunks_path = "./data/wcag_docs/chunks.json"
    loader.save_chunks(chunks, chunks_path)

    # 2. Build Pinecone index
    kb = WCAGKnowledgeBase()
    kb.build_index(chunks)

    # 3. Test query
    print("\n🧪 Testing RAG query...")
    results = kb.query("Images missing alternative text", criterion_id="1.1.1", top_k=3)
    print(f"  Query: 'Images missing alternative text' (criterion 1.1.1)")
    print(f"  Results: {len(results)} hits")
    for r in results:
        print(f"    [{r['score']:.3f}] [{r['chunk_type']}] {r['technique_id'] or r['criterion_id']}: {r['text'][:80]}...")

    # Test issue enrichment
    print("\n🧪 Testing issue enrichment...")
    enrichment = kb.query_for_issue(
        title="Images must have alternative text",
        description="Multiple images on the page lack alt attributes",
        wcag_criterion="1.1.1",
    )
    print(f"  Techniques found: {len(enrichment['techniques'])}")
    for t in enrichment['techniques']:
        print(f"    - {t['technique_id']}: {t['text'][:60]}...")
    print(f"  Understanding: {'Yes' if enrichment['understanding'] else 'No'}")
    print(f"  Fix suggestions: {len(enrichment['fix_suggestions'])}")

    stats = kb.get_stats()
    print(f"\n✅ Knowledge base built successfully!")
    print(f"  Total vectors: {stats['total_vectors']}")
    print(f"  Index: {stats['index_name']}")
    print(f"\n  You can now run audits with RAG enrichment:")
    print(f"  python run_step5.py https://example.com --max-pages 3")


if __name__ == "__main__":
    main()