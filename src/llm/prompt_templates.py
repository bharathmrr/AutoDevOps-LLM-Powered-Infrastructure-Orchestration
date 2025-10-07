"""Prompt engineering templates for LLM"""

from typing import List, Dict


class PromptTemplate:
    """Templates for LLM prompts"""
    
    SYSTEM_PROMPTS = {
        "terraform": """You are an expert DevOps engineer specializing in Terraform Infrastructure-as-Code.
Your task is to generate production-ready, secure, and well-structured Terraform configurations.

Guidelines:
- Use Terraform best practices and latest syntax
- Include proper resource naming and tagging
- Implement security best practices
- Add appropriate variables and outputs
- Include comments for clarity
- Follow the DRY principle
- Use modules where appropriate
- Ensure idempotency""",
        
        "kubernetes": """You are an expert Kubernetes engineer.
Your task is to generate production-ready Kubernetes manifests.

Guidelines:
- Use Kubernetes best practices
- Include resource limits and requests
- Implement health checks (liveness and readiness probes)
- Use proper labels and selectors
- Follow security best practices (security contexts, RBAC)
- Include appropriate ConfigMaps and Secrets references
- Use namespaces appropriately
- Add comments for clarity""",
        
        "ansible": """You are an expert in Ansible automation.
Your task is to generate production-ready Ansible playbooks.

Guidelines:
- Use Ansible best practices
- Implement idempotent tasks
- Use proper variable naming
- Include error handling
- Use roles and handlers appropriately
- Add tags for selective execution
- Include comments and documentation
- Follow YAML best practices""",
        
        "docker": """You are an expert in Docker containerization.
Your task is to generate production-ready Dockerfiles and docker-compose files.

Guidelines:
- Use multi-stage builds where appropriate
- Minimize image size
- Follow security best practices
- Use specific version tags
- Implement proper layer caching
- Add health checks
- Use non-root users
- Include comments for clarity"""
    }
    
    def get_system_prompt(self, iac_type: str, provider: str) -> str:
        """Get system prompt for specific IaC type
        
        Args:
            iac_type: Type of Infrastructure-as-Code
            provider: Cloud provider
            
        Returns:
            System prompt
        """
        base_prompt = self.SYSTEM_PROMPTS.get(iac_type.lower(), self.SYSTEM_PROMPTS["terraform"])
        provider_context = f"\n\nTarget Provider: {provider.upper()}"
        return base_prompt + provider_context
    
    def format_iac_prompt(
        self,
        user_request: str,
        provider: str,
        iac_type: str
    ) -> str:
        """Format Infrastructure-as-Code generation prompt
        
        Args:
            user_request: User's natural language request
            provider: Cloud provider
            iac_type: Type of IaC
            
        Returns:
            Formatted prompt
        """
        prompt = f"""Generate {iac_type} code for the following infrastructure request:

Request: {user_request}

Provider: {provider}

Requirements:
1. Generate complete, production-ready code
2. Include all necessary configurations
3. Add appropriate comments
4. Follow best practices for security and performance
5. Make the code modular and maintainable
6. Include variable definitions where appropriate
7. Add outputs for important resources

Please provide only the code without additional explanations unless necessary for understanding complex sections.
"""
        return prompt
    
    def format_improvement_prompt(
        self,
        code: str,
        validation_errors: List[str]
    ) -> str:
        """Format prompt for code improvement
        
        Args:
            code: Original code
            validation_errors: List of validation errors
            
        Returns:
            Formatted prompt
        """
        errors_str = "\n".join(f"- {error}" for error in validation_errors)
        
        prompt = f"""The following code has validation errors. Please fix them:

Original Code:
```
{code}
```

Validation Errors:
{errors_str}

Please provide the corrected code that addresses all validation errors while maintaining the original intent.
Only provide the corrected code without additional explanations.
"""
        return prompt
    
    def format_explanation_prompt(self, code: str) -> str:
        """Format prompt for code explanation
        
        Args:
            code: Code to explain
            
        Returns:
            Formatted prompt
        """
        prompt = f"""Explain the following Infrastructure-as-Code in simple terms:

```
{code}
```

Provide:
1. Overview of what this code does
2. Key resources created
3. Security considerations
4. Cost implications (if applicable)
5. Best practices followed
"""
        return prompt
    
    def format_optimization_prompt(self, code: str) -> str:
        """Format prompt for code optimization
        
        Args:
            code: Code to optimize
            
        Returns:
            Formatted prompt
        """
        prompt = f"""Optimize the following Infrastructure-as-Code for better performance, security, and cost:

```
{code}
```

Provide:
1. Optimized code
2. List of optimizations made
3. Expected improvements
"""
        return prompt
