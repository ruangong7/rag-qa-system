# Vector Store

## Operational Considerations

- Keep metadata fields consistent with the chunking pipeline.
- Support index rebuilds without losing source traceability.
- Monitor storage growth, query latency, and recall quality.

## Purpose

The vector store persists dense embeddings for chunk-level semantic retrieval.

## Retrieval Role

The vector store supports semantic candidate recall for multilingual and cross-lingual queries, especially when lexical overlap is weak.

## Stored Elements

- Chunk embedding vectors
- Chunk text references
- Retrieval metadata such as source file, section path, and page number
