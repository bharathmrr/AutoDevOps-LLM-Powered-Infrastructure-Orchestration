"""LLM Model initialization and inference"""

import os
from typing import Optional, Dict, Any, List
import ollama
from openai import OpenAI
from loguru import logger

from .config import LLMConfig
from .prompt_templates import PromptTemplate


class LLMModel:
    """Wrapper for LLM model interactions"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM model
        
        Args:
            config: LLM configuration object
        """
        self.config = config or LLMConfig()
        self.prompt_template = PromptTemplate()
        
        # Initialize clients
        if self.config.use_ollama:
            self.client_type = "ollama"
            logger.info(f"Using Ollama model: {self.config.ollama_model}")
        else:
            self.client_type = "openai"
            self.openai_client = OpenAI(api_key=self.config.openai_api_key)
            logger.info(f"Using OpenAI model: {self.config.openai_model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate text from prompt
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            context: Additional context for generation
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        try:
            if self.client_type == "ollama":
                return self._generate_ollama(prompt, system_prompt, context, **kwargs)
            else:
                return self._generate_openai(prompt, system_prompt, context, **kwargs)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict[str, Any]],
        **kwargs
    ) -> str:
        """Generate using Ollama"""
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"Context:\n{context_str}"
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        response = ollama.chat(
            model=self.config.ollama_model,
            messages=messages,
            options={
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }
        )
        
        return response['message']['content']
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[Dict[str, Any]],
        **kwargs
    ) -> str:
        """Generate using OpenAI"""
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"Context:\n{context_str}"
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        response = self.openai_client.chat.completions.create(
            model=self.config.openai_model,
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
            frequency_penalty=kwargs.get("frequency_penalty", self.config.frequency_penalty),
            presence_penalty=kwargs.get("presence_penalty", self.config.presence_penalty),
        )
        
        return response.choices[0].message.content
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary into string"""
        lines = []
        for key, value in context.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    def generate_iac(
        self,
        user_request: str,
        provider: str,
        iac_type: str,
        retrieved_docs: Optional[List[str]] = None
    ) -> str:
        """Generate Infrastructure-as-Code from user request
        
        Args:
            user_request: Natural language infrastructure request
            provider: Cloud provider (aws, azure, gcp, etc.)
            iac_type: Type of IaC (terraform, kubernetes, ansible, docker)
            retrieved_docs: Retrieved documentation from RAG
            
        Returns:
            Generated IaC code
        """
        system_prompt = self.prompt_template.get_system_prompt(iac_type, provider)
        
        context = {
            "provider": provider,
            "iac_type": iac_type,
        }
        
        if retrieved_docs:
            context["documentation"] = retrieved_docs
        
        formatted_prompt = self.prompt_template.format_iac_prompt(
            user_request,
            provider,
            iac_type
        )
        
        return self.generate(
            prompt=formatted_prompt,
            system_prompt=system_prompt,
            context=context
        )
    
    def validate_and_improve(
        self,
        code: str,
        validation_errors: List[str]
    ) -> str:
        """Improve code based on validation errors
        
        Args:
            code: Original code
            validation_errors: List of validation errors
            
        Returns:
            Improved code
        """
        prompt = self.prompt_template.format_improvement_prompt(code, validation_errors)
        return self.generate(prompt=prompt)
