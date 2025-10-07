"""Load and process documentation for RAG system"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from loguru import logger

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore


class DocumentLoader:
    """Load and process documentation files"""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """Initialize document loader
        
        Args:
            vector_store: Vector store instance
            embedding_generator: Embedding generator instance
        """
        self.vector_store = vector_store or VectorStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
        logger.info("Document loader initialized")
    
    def load_directory(
        self,
        directory: str,
        provider: Optional[str] = None,
        iac_type: Optional[str] = None,
        file_extensions: List[str] = [".md", ".txt", ".json"]
    ) -> int:
        """Load all documents from a directory
        
        Args:
            directory: Directory path
            provider: Cloud provider tag
            iac_type: IaC type tag
            file_extensions: List of file extensions to process
            
        Returns:
            Number of documents loaded
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return 0
        
        documents = []
        metadatas = []
        ids = []
        
        # Recursively find all matching files
        for ext in file_extensions:
            for file_path in dir_path.rglob(f"*{ext}"):
                try:
                    content = self._load_file(file_path)
                    
                    if content:
                        # Split large documents into chunks
                        chunks = self._chunk_document(content)
                        
                        for i, chunk in enumerate(chunks):
                            doc_id = f"{file_path.stem}_{i}"
                            
                            metadata = {
                                "source": str(file_path),
                                "filename": file_path.name,
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            }
                            
                            if provider:
                                metadata["provider"] = provider.lower()
                            if iac_type:
                                metadata["iac_type"] = iac_type.lower()
                            
                            documents.append(chunk)
                            metadatas.append(metadata)
                            ids.append(doc_id)
                
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {e}")
        
        if documents:
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(documents)} document chunks...")
            embeddings = self.embedding_generator.generate_embeddings(documents)
            
            # Add to vector store
            self.vector_store.add_documents(
                documents=documents,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Loaded {len(documents)} document chunks from {directory}")
        
        return len(documents)
    
    def _load_file(self, file_path: Path) -> str:
        """Load content from a file
        
        Args:
            file_path: Path to file
            
        Returns:
            File content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content.strip()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""
    
    def _chunk_document(
        self,
        content: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """Split document into overlapping chunks
        
        Args:
            content: Document content
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
            
        Returns:
            List of document chunks
        """
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence ending
                for delimiter in ['. ', '.\n', '! ', '?\n']:
                    last_delimiter = content[start:end].rfind(delimiter)
                    if last_delimiter != -1:
                        end = start + last_delimiter + len(delimiter)
                        break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def load_json_examples(
        self,
        json_file: str,
        provider: Optional[str] = None,
        iac_type: Optional[str] = None
    ) -> int:
        """Load examples from JSON file
        
        Args:
            json_file: Path to JSON file
            provider: Cloud provider tag
            iac_type: IaC type tag
            
        Returns:
            Number of examples loaded
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = []
            metadatas = []
            ids = []
            
            for i, example in enumerate(data):
                doc_id = f"example_{i}"
                
                # Combine prompt and response
                content = f"Prompt: {example.get('prompt', '')}\n\nResponse:\n{example.get('response', '')}"
                
                metadata = {
                    "source": json_file,
                    "type": "example",
                    "example_id": i
                }
                
                if provider:
                    metadata["provider"] = provider.lower()
                if iac_type:
                    metadata["iac_type"] = iac_type.lower()
                
                # Add any additional metadata from example
                if "metadata" in example:
                    metadata.update(example["metadata"])
                
                documents.append(content)
                metadatas.append(metadata)
                ids.append(doc_id)
            
            if documents:
                # Generate embeddings
                embeddings = self.embedding_generator.generate_embeddings(documents)
                
                # Add to vector store
                self.vector_store.add_documents(
                    documents=documents,
                    embeddings=embeddings.tolist(),
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"Loaded {len(documents)} examples from {json_file}")
            
            return len(documents)
        
        except Exception as e:
            logger.error(f"Error loading JSON examples: {e}")
            return 0
    
    def clear_all_documents(self):
        """Clear all documents from vector store"""
        self.vector_store.delete_collection()
        logger.info("Cleared all documents from vector store")
