"""Knowledge base with ChromaDB vector store and semantic search."""

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.logger import logger

# Optional imports — gracefully degrade if not installed
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed — falling back to in-memory BM25 search")

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    logger.warning("sentence-transformers not installed — embeddings disabled")

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import fitz  # pymupdf
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False


class DocumentChunk:
    """A chunk of a document with metadata."""

    def __init__(
        self,
        content: str,
        source: str,
        chunk_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.source = source
        self.chunk_id = chunk_id
        self.metadata = metadata or {}
        self.embedding: Optional[List[float]] = None
        self.uid = str(uuid.uuid4())


class KnowledgeBase:
    """Knowledge base backed by ChromaDB (semantic) with BM25 fallback."""

    COLLECTION_NAME = "qa_copilot_kb"

    def __init__(self, chunk_size: int = 512, overlap: int = 64, persist_dir: str = None):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[DocumentChunk] = []
        self._indexed_sources: set = set()

        # Determine persistence directory
        base = Path(__file__).parent.parent
        self.persist_dir = Path(persist_dir) if persist_dir else base / ".chroma_db"
        self.knowledge_dir = base / "knowledge"

        # Initialize ChromaDB
        self._chroma_client = None
        self._collection = None
        self._embedding_model = None
        self._init_vector_store()

        # Load default files from knowledge directory
        self._load_default_files()

    def _init_vector_store(self) -> None:
        if not _CHROMA_AVAILABLE:
            return
        try:
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialized at %s", self.persist_dir)
        except Exception as exc:
            logger.warning("ChromaDB init failed, using in-memory: %s", exc)
            self._chroma_client = None
            self._collection = None

        if _ST_AVAILABLE:
            try:
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Embedding model loaded: all-MiniLM-L6-v2")
            except Exception as exc:
                logger.warning("Embedding model load failed: %s", exc)

    def _load_default_files(self) -> None:
        if not self.knowledge_dir.exists():
            return
        for fp in self.knowledge_dir.glob("**/*"):
            if fp.is_file() and str(fp) not in self._indexed_sources:
                self._ingest_file(fp)

    def _ingest_file(self, file_path: Path) -> int:
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".pdf":
                return self.ingest_pdf(str(file_path))
            elif suffix == ".docx":
                return self.ingest_docx(str(file_path))
            elif suffix in {".md", ".txt", ".json", ".sql", ".yaml", ".yml", ".feature"}:
                return self.ingest_text(str(file_path))
        except Exception as exc:
            logger.warning("Failed to ingest '%s': %s", file_path, exc)
        return 0

    # ─── Text Chunking ────────────────────────────────────────────────────────

    def _chunk_text(self, text: str, source: str, metadata: Dict = None) -> List[DocumentChunk]:
        """Split text into overlapping sentence-aware chunks."""
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+|\n\n", text)
        chunks = []
        current = []
        current_len = 0
        chunk_id = 0

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if current_len + len(sent) > self.chunk_size and current:
                content = " ".join(current)
                chunks.append(
                    DocumentChunk(content, source, chunk_id, metadata=dict(metadata or {}))
                )
                chunk_id += 1
                # Keep overlap
                overlap_tokens = []
                overlap_len = 0
                for s in reversed(current):
                    if overlap_len + len(s) > self.overlap:
                        break
                    overlap_tokens.insert(0, s)
                    overlap_len += len(s)
                current = overlap_tokens
                current_len = overlap_len

            current.append(sent)
            current_len += len(sent)

        if current:
            chunks.append(
                DocumentChunk(" ".join(current), source, chunk_id, metadata=dict(metadata or {}))
            )

        return chunks

    def _embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        if self._embedding_model:
            try:
                return self._embedding_model.encode(texts, normalize_embeddings=True).tolist()
            except Exception as exc:
                logger.warning("Embedding failed: %s", exc)
        return None

    def _add_to_vector_store(self, chunks: List[DocumentChunk]) -> None:
        if not self._collection or not chunks:
            return
        try:
            texts = [c.content for c in chunks]
            embeddings = self._embed(texts)
            ids = [c.uid for c in chunks]
            metadatas = [{"source": c.source, "chunk_id": c.chunk_id, **c.metadata} for c in chunks]

            if embeddings:
                self._collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
            else:
                self._collection.add(ids=ids, documents=texts, metadatas=metadatas)
        except Exception as exc:
            logger.warning("Failed to add chunks to ChromaDB: %s", exc)

    # ─── Ingestion ────────────────────────────────────────────────────────────

    def ingest_pdf(self, file_path: str) -> int:
        fp = Path(file_path)
        if not fp.exists():
            return 0
        text = ""
        try:
            if _PYMUPDF_AVAILABLE:
                doc = fitz.open(str(fp))
                for page in doc:
                    text += page.get_text()
                doc.close()
            elif PyPDF2:
                with open(fp, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or ""
            else:
                logger.warning("No PDF library available for %s", fp)
                return 0
        except Exception as exc:
            logger.error("PDF parse error '%s': %s", fp, exc)
            return 0

        metadata = {"file_type": "pdf", "filename": fp.name}
        chunks = self._chunk_text(text, str(fp), metadata)
        self.chunks.extend(chunks)
        self._indexed_sources.add(str(fp))
        self._add_to_vector_store(chunks)
        logger.info("Ingested PDF '%s': %d chunks", fp.name, len(chunks))
        return len(chunks)

    def ingest_docx(self, file_path: str) -> int:
        if not DocxDocument:
            logger.warning("python-docx not installed")
            return 0
        fp = Path(file_path)
        if not fp.exists():
            return 0
        try:
            doc = DocxDocument(str(fp))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error("DOCX parse error '%s': %s", fp, exc)
            return 0

        metadata = {"file_type": "docx", "filename": fp.name}
        chunks = self._chunk_text(text, str(fp), metadata)
        self.chunks.extend(chunks)
        self._indexed_sources.add(str(fp))
        self._add_to_vector_store(chunks)
        logger.info("Ingested DOCX '%s': %d chunks", fp.name, len(chunks))
        return len(chunks)

    def ingest_text(self, file_path: str) -> int:
        fp = Path(file_path)
        if not fp.exists():
            return 0
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.error("Text file read error '%s': %s", fp, exc)
            return 0

        file_type = fp.suffix.lstrip(".")
        metadata = {"file_type": file_type, "filename": fp.name}
        chunks = self._chunk_text(text, str(fp), metadata)
        self.chunks.extend(chunks)
        self._indexed_sources.add(str(fp))
        self._add_to_vector_store(chunks)
        logger.info("Ingested text '%s' (%s): %d chunks", fp.name, file_type, len(chunks))
        return len(chunks)

    def ingest_swagger(self, file_path: str) -> int:
        """Ingest Swagger/OpenAPI JSON or YAML spec."""
        fp = Path(file_path)
        if not fp.exists():
            return 0
        try:
            raw = fp.read_text(encoding="utf-8")
            if fp.suffix in {".yaml", ".yml"}:
                try:
                    import yaml
                    data = yaml.safe_load(raw)
                    text = json.dumps(data, indent=2)
                except ImportError:
                    text = raw
            else:
                data = json.loads(raw)
                # Extract readable endpoint descriptions
                paths = data.get("paths", {})
                lines = [f"OpenAPI: {data.get('info', {}).get('title', 'Unknown')}"]
                for path, methods in paths.items():
                    for method, spec in methods.items():
                        if isinstance(spec, dict):
                            summary = spec.get("summary", "")
                            desc = spec.get("description", "")
                            lines.append(f"{method.upper()} {path}: {summary} {desc}".strip())
                text = "\n".join(lines)
        except Exception as exc:
            logger.error("Swagger parse error '%s': %s", fp, exc)
            return 0

        metadata = {"file_type": "swagger", "filename": fp.name}
        chunks = self._chunk_text(text, str(fp), metadata)
        self.chunks.extend(chunks)
        self._indexed_sources.add(str(fp))
        self._add_to_vector_store(chunks)
        return len(chunks)

    def ingest_postman(self, file_path: str) -> int:
        """Ingest Postman collection JSON."""
        fp = Path(file_path)
        if not fp.exists():
            return 0
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            lines = [f"Postman Collection: {data.get('info', {}).get('name', 'Unknown')}"]
            for item in data.get("item", []):
                self._flatten_postman(item, lines)
            text = "\n".join(lines)
        except Exception as exc:
            logger.error("Postman parse error '%s': %s", fp, exc)
            return 0

        metadata = {"file_type": "postman", "filename": fp.name}
        chunks = self._chunk_text(text, str(fp), metadata)
        self.chunks.extend(chunks)
        self._indexed_sources.add(str(fp))
        self._add_to_vector_store(chunks)
        return len(chunks)

    def _flatten_postman(self, item: dict, lines: list, depth: int = 0) -> None:
        indent = "  " * depth
        name = item.get("name", "")
        request = item.get("request", {})
        if request:
            method = request.get("method", "")
            url = request.get("url", {})
            raw_url = url.get("raw", "") if isinstance(url, dict) else str(url)
            lines.append(f"{indent}{method} {raw_url} — {name}")
        for sub in item.get("item", []):
            self._flatten_postman(sub, lines, depth + 1)

    def ingest_image_ocr(self, file_path: str) -> int:
        """Extract text from image using OCR."""
        if not _OCR_AVAILABLE:
            logger.warning("pytesseract/Pillow not installed — OCR disabled")
            return 0
        fp = Path(file_path)
        if not fp.exists():
            return 0
        try:
            image = Image.open(str(fp))
            text = pytesseract.image_to_string(image)
            if not text.strip():
                return 0
        except Exception as exc:
            logger.error("OCR error '%s': %s", fp, exc)
            return 0

        metadata = {"file_type": "image_ocr", "filename": fp.name}
        chunks = self._chunk_text(text, str(fp), metadata)
        self.chunks.extend(chunks)
        self._indexed_sources.add(str(fp))
        self._add_to_vector_store(chunks)
        return len(chunks)

    # ─── Search ───────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5, file_type: str = None) -> List[str]:
        """Semantic search using ChromaDB, falling back to BM25."""
        # Try vector search first
        if self._collection:
            try:
                where = {"file_type": file_type} if file_type else None
                embedding = self._embed([query])
                if embedding:
                    results = self._collection.query(
                        query_embeddings=embedding,
                        n_results=min(top_k, max(1, self._collection.count())),
                        where=where,
                    )
                else:
                    results = self._collection.query(
                        query_texts=[query],
                        n_results=min(top_k, max(1, self._collection.count())),
                        where=where,
                    )
                docs = results.get("documents", [[]])[0]
                if docs:
                    return docs
            except Exception as exc:
                logger.warning("ChromaDB search failed, using BM25: %s", exc)

        # BM25 fallback
        return self._bm25_search(query, top_k)

    def _bm25_search(self, query: str, top_k: int) -> List[str]:
        if not self.chunks:
            return []
        query_terms = set(query.lower().split())
        scores = []
        for chunk in self.chunks:
            chunk_terms = chunk.content.lower().split()
            term_freq = {}
            for t in chunk_terms:
                term_freq[t] = term_freq.get(t, 0) + 1
            score = sum(term_freq.get(t, 0) for t in query_terms) / max(len(chunk_terms), 1)
            scores.append((score, chunk.content))
        scores.sort(reverse=True, key=lambda x: x[0])
        return [c for _, c in scores[:top_k] if _ > 0]

    def context_for(self, query: str, top_k: int = 5) -> str:
        """Get formatted context string for LLM injection."""
        results = self.search(query, top_k)
        if not results:
            return ""
        header = "Relevant knowledge base context:\n"
        return header + "\n\n---\n\n".join(results)

    def get_statistics(self) -> Dict[str, Any]:
        chroma_count = 0
        if self._collection:
            try:
                chroma_count = self._collection.count()
            except Exception:
                pass
        return {
            "total_chunks_in_memory": len(self.chunks),
            "total_chunks_in_vector_store": chroma_count,
            "total_sources": len(self._indexed_sources),
            "indexed_files": list(self._indexed_sources),
            "vector_store_available": bool(self._collection),
            "embedding_model_available": bool(self._embedding_model),
        }

    def delete_source(self, source: str) -> bool:
        """Remove a source document from the knowledge base."""
        self.chunks = [c for c in self.chunks if c.source != source]
        self._indexed_sources.discard(source)
        if self._collection:
            try:
                self._collection.delete(where={"source": source})
            except Exception as exc:
                logger.warning("Failed to delete from ChromaDB: %s", exc)
        return True
