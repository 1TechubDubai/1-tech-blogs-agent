import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    chromadb = None

from config.settings import settings

logger = logging.getLogger("seo_agent.services.vector_store")

# Vector store configuration
VECTOR_DB_PATH = Path(settings.TEST_STORAGE_PATH) / "vector_db"
VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)


class VectorStore:
    """Manages vector embeddings of generated content using Chroma."""
    
    def __init__(self):
        """Initialize vector store."""
        if not CHROMA_AVAILABLE:
            logger.warning("Chroma not installed. Using mock vector store.")
            self.client = None
            self.collections = {}
        else:
            try:
                # Initialize Chroma client
                chroma_settings = Settings(
                    chroma_db_impl="duckdb",
                    persist_directory=str(VECTOR_DB_PATH),
                    anonymized_telemetry=False,
                )
                self.client = chromadb.Client(chroma_settings)
                logger.info(f"✅ Vector store initialized at {VECTOR_DB_PATH}")
            except Exception as e:
                logger.warning(f"Failed to initialize Chroma: {e}. Using mock vector store.")
                self.client = None
                self.collections = {}
    
    def _get_or_create_collection(self, collection_name: str):
        """Get or create a collection."""
        if self.client is None:
            # Mock collection
            if collection_name not in self.collections:
                self.collections[collection_name] = {
                    "embeddings": [],
                    "documents": [],
                    "ids": []
                }
            return self.collections[collection_name]
        
        try:
            return self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            return None
    
    def add_blog(self, blog_id: str, title: str, content: str, metadata: Dict = None) -> bool:
        """Add a blog to the vector store."""
        try:
            collection = self._get_or_create_collection("blog_posts")
            if collection is None:
                return False
            
            # Create a summary embedding text
            embedding_text = f"{title}\n{content[:500]}"
            
            if self.client is None:
                # Mock: store as JSON
                collection["embeddings"].append(embedding_text)
                collection["documents"].append({
                    "title": title,
                    "content": content[:1000],
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow().isoformat()
                })
                collection["ids"].append(blog_id)
            else:
                # Real Chroma
                collection.add(
                    ids=[blog_id],
                    documents=[embedding_text],
                    metadatas=[{
                        "title": title,
                        "source": "generated_blog",
                        **(metadata or {})
                    }]
                )
            
            logger.info(f"✅ Added blog to vector store: {blog_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding blog to vector store: {e}")
            return False
    
    def find_similar_blogs(self, query: str, threshold: float = 0.7, top_k: int = 3) -> List[Dict]:
        """Find similar blogs by semantic similarity."""
        try:
            collection = self._get_or_create_collection("blogs")
            if collection is None:
                return []
            
            if self.client is None:
                # Mock: simple substring matching
                similar = []
                query_lower = query.lower()
                for doc_id, doc in zip(collection["ids"], collection["documents"]):
                    if query_lower in doc.get("title", "").lower() or \
                       query_lower in doc.get("content", "").lower():
                        similar.append({
                            "id": doc_id,
                            "title": doc.get("title", ""),
                            "similarity": 0.8,
                            "created_at": doc.get("created_at")
                        })
                return similar[:top_k]
            else:
                # Real Chroma
                results = collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
                
                similar = []
                for idx, (distance, metadata) in enumerate(
                    zip(results["distances"][0], results["metadatas"][0])
                ):
                    # Convert distance to similarity (lower distance = higher similarity)
                    similarity = 1 - distance
                    
                    if similarity >= threshold:
                        similar.append({
                            "id": results["ids"][0][idx],
                            "title": metadata.get("title", ""),
                            "similarity": similarity,
                            "created_at": metadata.get("created_at")
                        })
                
                return similar
        except Exception as e:
            logger.error(f"Error querying similar blogs: {e}")
            return []
    
    def add_keyword(self, keyword: str, industry: str, metadata: Dict = None) -> bool:
        """Add a keyword to the vector store."""
        try:
            collection = self._get_or_create_collection("keywords")
            if collection is None:
                return False
            
            keyword_id = hashlib.md5(f"{keyword}_{industry}".encode()).hexdigest()[:12]
            
            if self.client is None:
                # Mock storage
                collection["embeddings"].append(keyword)
                collection["documents"].append({
                    "keyword": keyword,
                    "industry": industry,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow().isoformat()
                })
                collection["ids"].append(keyword_id)
            else:
                # Real Chroma
                collection.add(
                    ids=[keyword_id],
                    documents=[keyword],
                    metadatas=[{
                        "keyword": keyword,
                        "industry": industry,
                        **(metadata or {})
                    }]
                )
            
            logger.info(f"✅ Added keyword to vector store: {keyword}")
            return True
        except Exception as e:
            logger.error(f"Error adding keyword to vector store: {e}")
            return False
    
    def find_similar_keywords(self, keyword: str, threshold: float = 0.6, top_k: int = 5) -> List[Dict]:
        """Find similar keywords already used."""
        try:
            collection = self._get_or_create_collection("keywords")
            if collection is None:
                return []
            
            if self.client is None:
                # Mock: substring matching
                similar = []
                keyword_lower = keyword.lower()
                for kw_id, doc in zip(collection["ids"], collection["documents"]):
                    if keyword_lower in doc.get("keyword", "").lower() or \
                       doc.get("keyword", "").lower() in keyword_lower:
                        similar.append({
                            "id": kw_id,
                            "keyword": doc.get("keyword", ""),
                            "industry": doc.get("industry", ""),
                            "similarity": 0.8,
                            "created_at": doc.get("created_at")
                        })
                return similar[:top_k]
            else:
                # Real Chroma
                results = collection.query(
                    query_texts=[keyword],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
                
                similar = []
                for idx, distance in enumerate(results["distances"][0]):
                    similarity = 1 - distance
                    
                    if similarity >= threshold:
                        metadata = results["metadatas"][0][idx]
                        similar.append({
                            "id": results["ids"][0][idx],
                            "keyword": metadata.get("keyword", ""),
                            "industry": metadata.get("industry", ""),
                            "similarity": similarity,
                            "created_at": metadata.get("created_at")
                        })
                
                return similar
        except Exception as e:
            logger.error(f"Error querying similar keywords: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Get vector store statistics."""
        try:
            stats = {
                "vector_db_available": CHROMA_AVAILABLE and self.client is not None,
                "storage_path": str(VECTOR_DB_PATH),
            }
            
            if self.client is None:
                # Mock statistics
                stats["blogs_stored"] = len(self.collections.get("blogs", {}).get("ids", []))
                stats["keywords_stored"] = len(self.collections.get("keywords", {}).get("ids", []))
            else:
                try:
                    blogs_col = self.client.get_collection("blogs")
                    stats["blogs_stored"] = blogs_col.count()
                except:
                    stats["blogs_stored"] = 0
                
                try:
                    keywords_col = self.client.get_collection("keywords")
                    stats["keywords_stored"] = keywords_col.count()
                except:
                    stats["keywords_stored"] = 0
            
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}


# Global instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
