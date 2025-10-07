"""Fine-tuning scripts for LLM models"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import Dataset


class FineTuner:
    """Fine-tune LLM models for IaC generation"""
    
    def __init__(
        self,
        base_model: str = "mistralai/Mistral-7B-v0.1",
        output_dir: str = "./models/fine-tuned"
    ):
        """Initialize fine-tuner
        
        Args:
            base_model: Base model to fine-tune
            output_dir: Directory to save fine-tuned model
        """
        self.base_model = base_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing fine-tuner with base model: {base_model}")
        
        self.tokenizer = None
        self.model = None
    
    def load_training_data(
        self,
        prompts_dir: str,
        responses_dir: str
    ) -> List[Dict[str, str]]:
        """Load training data from directories
        
        Args:
            prompts_dir: Directory containing prompt files
            responses_dir: Directory containing response files
            
        Returns:
            List of training examples
        """
        prompts_path = Path(prompts_dir)
        responses_path = Path(responses_dir)
        
        training_data = []
        
        for prompt_file in prompts_path.glob("*.txt"):
            response_file = responses_path / prompt_file.name
            
            if response_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as pf:
                    prompt = pf.read().strip()
                
                with open(response_file, 'r', encoding='utf-8') as rf:
                    response = rf.read().strip()
                
                training_data.append({
                    "prompt": prompt,
                    "response": response,
                    "text": f"### Instruction:\n{prompt}\n\n### Response:\n{response}"
                })
        
        logger.info(f"Loaded {len(training_data)} training examples")
        return training_data
    
    def prepare_dataset(
        self,
        training_data: List[Dict[str, str]],
        max_length: int = 2048
    ) -> Dataset:
        """Prepare dataset for training
        
        Args:
            training_data: List of training examples
            max_length: Maximum sequence length
            
        Returns:
            Prepared dataset
        """
        if not self.tokenizer:
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                max_length=max_length,
                padding="max_length"
            )
        
        dataset = Dataset.from_list(training_data)
        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )
        
        return tokenized_dataset
    
    def fine_tune(
        self,
        dataset: Dataset,
        num_epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 2e-5,
        save_steps: int = 500,
        eval_steps: int = 500,
        warmup_steps: int = 100
    ):
        """Fine-tune the model
        
        Args:
            dataset: Prepared dataset
            num_epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate
            save_steps: Save checkpoint every N steps
            eval_steps: Evaluate every N steps
            warmup_steps: Number of warmup steps
        """
        logger.info("Loading base model...")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            logging_steps=100,
            save_steps=save_steps,
            eval_steps=eval_steps,
            save_total_limit=3,
            fp16=True,
            gradient_accumulation_steps=4,
            dataloader_pin_memory=True,
            report_to="none"
        )
        
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator
        )
        
        logger.info("Starting fine-tuning...")
        trainer.train()
        
        logger.info("Saving fine-tuned model...")
        trainer.save_model(str(self.output_dir / "final"))
        self.tokenizer.save_pretrained(str(self.output_dir / "final"))
        
        logger.info(f"Fine-tuning complete. Model saved to {self.output_dir / 'final'}")
    
    def evaluate(
        self,
        test_prompts: List[str],
        model_path: Optional[str] = None
    ) -> List[str]:
        """Evaluate fine-tuned model
        
        Args:
            test_prompts: List of test prompts
            model_path: Path to model (uses latest if None)
            
        Returns:
            List of generated responses
        """
        if model_path is None:
            model_path = str(self.output_dir / "final")
        
        logger.info(f"Loading model from {model_path}")
        model = AutoModelForCausalLM.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        responses = []
        for prompt in test_prompts:
            formatted_prompt = f"### Instruction:\n{prompt}\n\n### Response:\n"
            inputs = tokenizer(formatted_prompt, return_tensors="pt")
            
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True
            )
            
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            responses.append(response)
        
        return responses


def create_training_example(
    prompt: str,
    response: str,
    output_dir: str,
    filename: str
):
    """Create a training example file pair
    
    Args:
        prompt: User prompt
        response: Expected response
        output_dir: Output directory
        filename: Base filename
    """
    output_path = Path(output_dir)
    prompts_dir = output_path / "prompts"
    responses_dir = output_path / "responses"
    
    prompts_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)
    
    with open(prompts_dir / f"{filename}.txt", 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    with open(responses_dir / f"{filename}.txt", 'w', encoding='utf-8') as f:
        f.write(response)
    
    logger.info(f"Created training example: {filename}")
