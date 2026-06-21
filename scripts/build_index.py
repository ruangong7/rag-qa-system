"""CLI entrypoint for rebuilding the local RAG index."""
import argparse

from src.ingestion.indexer import build_index


def main():
    parser = argparse.ArgumentParser(description="Build local ChromaDB + BM25 index from source documents.")
    parser.add_argument(
        "--data-dir",
        default="./data/documents",
        help="Directory containing source documents.",
    )
    parser.add_argument(
        "--persist-dir",
        default="./chroma_data",
        help="Directory used to persist ChromaDB and BM25 artifacts.",
    )
    args = parser.parse_args()

    count = build_index(args.data_dir, persist_dir=args.persist_dir)
    print(f"documents_indexed={count}")


if __name__ == "__main__":
    main()
