"""Vector database interface for storing and retrieving embeddings"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
import numpy as np
from loguru import logger


class VectorStore:
    """Interface for vector database operations"""
    
    def __init__(
        self,
        db_type: str = "chromadb",
        db_path: str = "./data/embeddings",
        collection_name: str = "autodevops_docs"
    ):
        """Initialize vector store
        
        Args:
            db_type: Type of vector database (chromadb, pinecone, weaviate)
            db_path: Path to database storage
            collection_name: Name of the collection
        """
        self.db_type = db_type
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        if db_type == "chromadb":
            self._init_chromadb()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _init_chromadb(self):
        """Initialize ChromaDB"""
        logger.info(f"Initializing ChromaDB at {self.db_path}")
        
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "AutoDevOps documentation embeddings"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ):
        """Add documents to vector store
        
        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: Optional metadata for each document
            ids: Optional IDs for documents
        """
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in documents]
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(documents)} documents to vector store")
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
        """Search for similar documents
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            Tuple of (documents, metadatas, distances)
        """
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        
        return documents, metadatas, distances
    
    def search_by_text(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
        """Search using text query (ChromaDB will embed it)
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            Tuple of (documents, metadatas, distances)
        """
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where
        )
        
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        
        return documents, metadatas, distances
    
    def delete_collection(self):
        """Delete the collection"""
        self.client.delete_collection(name=self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")
    
    def get_collection_count(self) -> int:
        """Get number of documents in collection
        
        Returns:
            Document count
        """
        return self.collection.count()
    
    def update_document(
        self,
        doc_id: str,
        document: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update a document in the collection
        
        Args:
            doc_id: Document ID
            document: Updated document text
            embedding: Updated embedding
            metadata: Updated metadata
        """
        update_data = {"ids": [doc_id]}
        
        if document is not None:
            update_data["documents"] = [document]
        if embedding is not None:
            update_data["embeddings"] = [embedding]
        if metadata is not None:
            update_data["metadatas"] = [metadata]
        
        self.collection.update(**update_data)
        logger.info(f"Updated document: {doc_id}")
    
    def delete_documents(self, doc_ids: List[str]):
        """Delete documents from collection
        
        Args:
            doc_ids: List of document IDs to delete
        """
        self.collection.delete(ids=doc_ids)
        logger.info(f"Deleted {len(doc_ids)} documents")
