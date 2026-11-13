# Limitations — APICN002

## Corpus and Index

The Income Tax Act 1961 (~171 MB) exceeds GitHub's file-size limit and is distributed separately via repository Release assets. Users must download it and place it in `data/` before running ingestion. The embedding index must be rebuilt from scratch after any corpus change; incremental updates are not supported.

## Answer Generation

The LLM answers exclusively from retrieved context. If a relevant provision does not appear in the top-k results, the answer will be incomplete or will correctly report that the information is not found. The model is not instructed to verify multi-step tax calculations, so slab arithmetic and surcharge computations may contain errors.

The generation budget is 700 tokens per response. Detailed step-by-step calculations for complex questions (such as computing tax under both regimes for a taxpayer with multiple income heads) may be truncated.

## Speech

The `faster-whisper` model cold-starts in 5–15 seconds on first use. Background noise degrades transcription accuracy in VITO and VIVO modes. TTS is sentence-chunked sequential, not streaming: the first audio output does not begin until LLM generation is complete.

## Latency

Local inference with `llama3.2:latest` on CPU-only hardware produces TITO latencies of approximately 20–60 seconds per question. This is hardware-dependent and cannot be optimised purely in software.
