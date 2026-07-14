"""Nyaya AI — Colab GPU Re-Ingestion Script (Hybrid Vectors).

Run this script on Google Colab with a T4 GPU to re-encode and re-index
all 33,603 statutory sections with both dense (BGE-M3 1024d) and sparse
(BGE-M3 lexical weights) vectors.

INSTRUCTIONS:
=============
1. Open Google Colab (https://colab.research.google.com)
2. Set runtime to GPU: Runtime → Change runtime type → T4 GPU
3. Upload this file OR copy-paste into a notebook cell
4. Run the script — it will:
   a. Install dependencies
   b. Download the mratanusarkar/Indian-Laws dataset from HuggingFace
   c. Encode all sections with BGE-M3 (dense + sparse, single pass)
   d. Create a local Qdrant collection with hybrid named vectors
   e. Upsert all points
   f. Zip the qdrant_data/ directory for download
5. Download the generated 'qdrant_data_hybrid.zip'
6. On your local machine:
   a. Delete the existing qdrant_data/ directory
   b. Unzip qdrant_data_hybrid.zip → qdrant_data/
   c. Run: python query.py  (to verify it works)

ESTIMATED TIME: ~45-60 minutes on T4 GPU
"""

import subprocess
import sys
import os
import time
import json
import shutil
import zipfile
from pathlib import Path

# ===================================================================
# Step 0: Install dependencies
# ===================================================================
print("=" * 60)
print("STEP 0: Installing dependencies...")
print("=" * 60)

subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "qdrant-client>=1.7.0",
    "FlagEmbedding>=1.2.0",
    "datasets>=2.14.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
])

import numpy as np
from datasets import load_dataset
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from pydantic import BaseModel, Field
import uuid

# ===================================================================
# Configuration
# ===================================================================
COLLECTION_NAME = "nyaya_corpus"
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
QDRANT_PATH = "./qdrant_data"
EMBED_BATCH_SIZE = 8  # Conservative for Colab T4 GPU memory
UPSERT_BATCH_SIZE = 100

CORPUS_VERSION = "v1"
HF_DATASET = "mratanusarkar/Indian-Laws"


# ===================================================================
# Schema (minimal — matches CorpusChunk.to_payload())
# ===================================================================
class CorpusChunk(BaseModel):
    """Minimal schema for statutory corpus chunks."""
    act_name: str
    section_number: str = ""
    section_title: str = ""
    text: str
    source: str = HF_DATASET
    version: str = CORPUS_VERSION

    def to_payload(self) -> dict:
        return {
            "act_name": self.act_name,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "text": self.text,
            "source": self.source,
            "version": self.version,
        }


# ===================================================================
# Step 1: Load dataset
# ===================================================================
print("\n" + "=" * 60)
print("STEP 1: Loading mratanusarkar/Indian-Laws from HuggingFace...")
print("=" * 60)

ds = load_dataset(HF_DATASET, split="train")
print(f"  Raw rows: {len(ds)}")

# Dedup and filter
seen = set()
chunks = []
skipped_empty = 0
skipped_dedup = 0

for row in ds:
    act_name = (row.get("Act") or row.get("act") or "").strip()
    section_number = str(row.get("Section") or row.get("section") or "").strip()
    section_title = (row.get("Section_Title") or row.get("section_title") or "").strip()
    text = (row.get("Description") or row.get("description") or "").strip()

    # Skip empty
    if not text or not act_name:
        skipped_empty += 1
        continue

    # Dedup by (act_name, section_number)
    key = (act_name.lower(), section_number.lower())
    if key in seen:
        skipped_dedup += 1
        continue
    seen.add(key)

    chunks.append(CorpusChunk(
        act_name=act_name,
        section_number=section_number,
        section_title=section_title,
        text=text,
    ))

act_names = set(c.act_name for c in chunks)
print(f"  After filtering: {len(chunks)} sections from {len(act_names)} Acts")
print(f"  Skipped: {skipped_empty} empty, {skipped_dedup} duplicate")


# ===================================================================
# Step 2: Load BGE-M3 model
# ===================================================================
print("\n" + "=" * 60)
print("STEP 2: Loading BGE-M3 model (dense + sparse)...")
print("=" * 60)

model = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=True)
print("  Model loaded successfully.")


# ===================================================================
# Step 3: Encode all chunks (dense + sparse in one pass)
# ===================================================================
print("\n" + "=" * 60)
print(f"STEP 3: Encoding {len(chunks)} sections (batch_size={EMBED_BATCH_SIZE})...")
print("=" * 60)

texts = [c.text for c in chunks]
all_dense = []
all_sparse = []

start_time = time.time()

for i in range(0, len(texts), EMBED_BATCH_SIZE):
    batch = texts[i : i + EMBED_BATCH_SIZE]

    output = model.encode(
        batch,
        batch_size=EMBED_BATCH_SIZE,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    # Dense vectors
    dense_vecs = output["dense_vecs"].tolist()
    all_dense.extend(dense_vecs)

    # Sparse vectors: convert to {int_token_id: float_weight}
    for weights_dict in output["lexical_weights"]:
        converted = {}
        for key, value in weights_dict.items():
            if isinstance(key, str):
                token_ids = model.tokenizer.convert_tokens_to_ids([key])
                converted[token_ids[0]] = float(value)
            else:
                converted[int(key)] = float(value)
        all_sparse.append(converted)

    done = min(i + EMBED_BATCH_SIZE, len(texts))
    elapsed = time.time() - start_time
    rate = done / elapsed if elapsed > 0 else 0
    eta = (len(texts) - done) / rate if rate > 0 else 0
    print(f"  [{done:,}/{len(texts):,}] {elapsed:.0f}s elapsed, ~{eta:.0f}s remaining", end="\r")

encode_time = time.time() - start_time
print(f"\n  Encoding complete in {encode_time:.1f}s ({len(all_dense)} dense + {len(all_sparse)} sparse vectors)")


# ===================================================================
# Step 4: Create Qdrant collection and upsert
# ===================================================================
print("\n" + "=" * 60)
print("STEP 4: Creating Qdrant collection and upserting...")
print("=" * 60)

# Clean up any existing data
if os.path.exists(QDRANT_PATH):
    shutil.rmtree(QDRANT_PATH)
    print(f"  Removed existing {QDRANT_PATH}")

client = QdrantClient(path=QDRANT_PATH)

# Create collection with hybrid named vectors
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config={
        "dense": qmodels.VectorParams(
            size=EMBEDDING_DIM,
            distance=qmodels.Distance.COSINE,
        ),
    },
    sparse_vectors_config={
        "sparse": qmodels.SparseVectorParams(),
    },
)
print(f"  Created collection '{COLLECTION_NAME}' (dense={EMBEDDING_DIM}d + sparse)")

# Upsert in batches
upsert_start = time.time()
for i in range(0, len(chunks), UPSERT_BATCH_SIZE):
    batch_chunks = chunks[i : i + UPSERT_BATCH_SIZE]
    batch_dense = all_dense[i : i + UPSERT_BATCH_SIZE]
    batch_sparse = all_sparse[i : i + UPSERT_BATCH_SIZE]

    points = []
    for chunk, dense_vec, sparse_dict in zip(batch_chunks, batch_dense, batch_sparse):
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dense_vec,
                    "sparse": qmodels.SparseVector(
                        indices=list(sparse_dict.keys()),
                        values=list(sparse_dict.values()),
                    ),
                },
                payload=chunk.to_payload(),
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    done = min(i + UPSERT_BATCH_SIZE, len(chunks))
    print(f"  Upserted [{done:,}/{len(chunks):,}]", end="\r")

upsert_time = time.time() - upsert_start

# Verify
info = client.get_collection(collection_name=COLLECTION_NAME)
point_count = info.points_count or 0
print(f"\n  Upsert complete in {upsert_time:.1f}s — {point_count:,} points in collection")

# Close client to flush data
del client


# ===================================================================
# Step 5: Zip for download
# ===================================================================
print("\n" + "=" * 60)
print("STEP 5: Zipping qdrant_data/ for download...")
print("=" * 60)

zip_filename = "qdrant_data_hybrid.zip"

with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(QDRANT_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, ".")
            zf.write(file_path, arcname)

zip_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
print(f"  Created {zip_filename} ({zip_size_mb:.1f} MB)")


# ===================================================================
# Summary
# ===================================================================
total_time = time.time() - start_time

print("\n" + "=" * 60)
print("INGESTION COMPLETE — SUMMARY")
print("=" * 60)
print(f"  Acts ingested:        {len(act_names)}")
print(f"  Sections indexed:     {len(chunks):,}")
print(f"  Points in Qdrant:     {point_count:,}")
print(f"  Dense vector dim:     {EMBEDDING_DIM}")
print(f"  Sparse vectors:       lexical weights (BGE-M3)")
print(f"  Collection:           {COLLECTION_NAME}")
print(f"  Encoding time:        {encode_time:.1f}s")
print(f"  Upsert time:          {upsert_time:.1f}s")
print(f"  Total time:           {total_time:.1f}s")
print(f"  Output file:          {zip_filename} ({zip_size_mb:.1f} MB)")
print()
print("NEXT STEPS:")
print("  1. Download qdrant_data_hybrid.zip from this Colab")
print("  2. On your local machine:")
print("     a. Delete the existing qdrant_data/ directory")
print("     b. Unzip: qdrant_data_hybrid.zip → qdrant_data/")
print("     c. Run: python query.py")
print()

# Auto-download in Colab
try:
    from google.colab import files
    print("Triggering Colab download...")
    files.download(zip_filename)
except ImportError:
    print(f"(Not in Colab — manually download {zip_filename})")
