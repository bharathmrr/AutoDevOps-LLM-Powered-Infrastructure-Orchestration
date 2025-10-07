"""LLM Configuration"""

from pydantic import BaseModel, Field
from typing import Optional


class LLMConfig(BaseModel):
    """Configuration for LLM models"""
    
    # Ollama Configuration
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server host")
    ollama_model: str = Field(default="gemma2:2b", description="Ollama model name")
    
    # OpenAI Configuration (fallback)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")
    
    # Generation Parameters
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2000, ge=1, le=8000, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Model Selection
    use_ollama: bool = Field(default=True, description="Use Ollama instead of OpenAI")
    
    # Fine-tuning
    fine_tuned_model_path: Optional[str] = Field(default=None, description="Path to fine-tuned model")
    
    class Config:
        env_prefix = "LLM_"
