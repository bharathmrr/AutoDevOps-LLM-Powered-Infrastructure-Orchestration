"""Document retrieval logic for RAG system"""

from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore


class DocumentRetriever:
    """Retrieve relevant documents for RAG"""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.75
    ):
        """Initialize document retriever
        
        Args:
            vector_store: Vector store instance
            embedding_generator: Embedding generator instance
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score
        """
        self.vector_store = vector_store or VectorStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        logger.info("Document retriever initialized")
    
    def retrieve(
        self,
        query: str,
        provider: Optional[str] = None,
        iac_type: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query
        
        Args:
            query: Search query
            provider: Cloud provider filter (aws, azure, gcp)
            iac_type: IaC type filter (terraform, kubernetes, ansible)
            top_k: Number of results (overrides default)
            
        Returns:
            List of retrieved documents with metadata
        """
        k = top_k or self.top_k
        
        # Build metadata filter
        filter_metadata = {}
        if provider:
            filter_metadata["provider"] = provider.lower()
        if iac_type:
            filter_metadata["iac_type"] = iac_type.lower()
        
        # Search using text query
        documents, metadatas, distances = self.vector_store.search_by_text(
            query_text=query,
            top_k=k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        # Filter by similarity threshold
        results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            # Convert distance to similarity (ChromaDB uses L2 distance)
            similarity = 1 / (1 + distance)
            
            if similarity >= self.similarity_threshold:
                results.append({
                    "content": doc,
                    "metadata": metadata,
                    "similarity": similarity,
                    "distance": distance
                })
        
        logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
        return results
    
    def retrieve_with_context(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Retrieve documents with conversation context
        
        Args:
            query: Search query
            conversation_history: Previous conversation turns
            **kwargs: Additional retrieval parameters
            
        Returns:
            List of retrieved documents
        """
        # Enhance query with conversation context
        enhanced_query = query
        
        if conversation_history:
            # Extract relevant context from history
            context_parts = [query]
            for turn in conversation_history[-3:]:  # Last 3 turns
                if turn.get("role") == "user":
                    context_parts.append(turn.get("content", ""))
            
            enhanced_query = " ".join(context_parts)
        
        return self.retrieve(enhanced_query, **kwargs)
    
    def retrieve_multi_query(
        self,
        queries: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Retrieve documents for multiple queries and merge results
        
        Args:
            queries: List of search queries
            **kwargs: Additional retrieval parameters
            
        Returns:
            Merged list of unique documents
        """
        all_results = []
        seen_contents = set()
        
        for query in queries:
            results = self.retrieve(query, **kwargs)
            
            for result in results:
                content = result["content"]
                if content not in seen_contents:
                    seen_contents.add(content)
                    all_results.append(result)
        
        # Sort by similarity
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top_k results
        k = kwargs.get("top_k", self.top_k)
        return all_results[:k]
    
    def get_relevant_examples(
        self,
        query: str,
        example_type: str = "terraform",
        top_k: int = 3
    ) -> List[str]:
        """Get relevant code examples
        
        Args:
            query: Search query
            example_type: Type of examples to retrieve
            top_k: Number of examples
            
        Returns:
            List of example code snippets
        """
        results = self.retrieve(
            query=query,
            iac_type=example_type,
            top_k=top_k
        )
        
        return [result["content"] for result in results]
    
    def get_documentation(
        self,
        topic: str,
        provider: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """Get relevant documentation for a topic
        
        Args:
            topic: Documentation topic
            provider: Cloud provider
            top_k: Number of documents to retrieve
            
        Returns:
            Combined documentation text
        """
        results = self.retrieve(
            query=topic,
            provider=provider,
            top_k=top_k
        )
        
        # Combine documentation
        docs = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "Unknown")
            docs.append(f"[Source {i}: {source}]\n{result['content']}\n")
        
        return "\n---\n".join(docs)
