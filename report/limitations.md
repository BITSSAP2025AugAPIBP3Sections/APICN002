# Limitations — APICN002

## Corpus and Index

The Income Tax Act 1961 (~171 MB) exceeds GitHub's file-size limit and is distributed separately via repository Release assets. Users must download it and place it in `data/` before running ingestion. The embedding index must be rebuilt from scratch after any corpus change; incremental updates are not supported.

## Retrieval Quality

Semantic search using `nomic-embed-text` embeddings retrieves passages that are semantically close to the query. It can miss relevant provisions when the query uses different terminology from the document (for example, querying "crypto tax" when the Act says "Virtual Digital Assets"). Context is limited to the top-k chunks (default k = 5), which may be insufficient for complex multi-part questions that span many sections.

There is no reranking step. All five chunks are given equal weight in the context, so a highly relevant chunk appearing after a less relevant one receives no priority boost.

## Answer Generation

The LLM answers exclusively from retrieved context. If a relevant provision does not appear in the top-k results, the answer will be incomplete or will correctly report that the information is not found. The model is not instructed to verify multi-step tax calculations, so slab arithmetic and surcharge computations may contain errors.

The generation budget is 700 tokens per response. Detailed step-by-step calculations for complex questions (such as computing tax under both regimes for a taxpayer with multiple income heads) may be truncated.

## Speech

The `faster-whisper` model cold-starts in 5–15 seconds on first use. Background noise degrades transcription accuracy in VITO and VIVO modes. TTS is sentence-chunked sequential, not streaming: the first audio output does not begin until LLM generation is complete.

## Latency

Local inference with `llama3.2:latest` on CPU-only hardware produces TITO latencies of approximately 20–60 seconds per question. This is hardware-dependent and cannot be optimised purely in software.
