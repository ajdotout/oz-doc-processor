from abc import ABC, abstractmethod
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
import os
import logging
from typing import Type, Any
from pydantic import BaseModel
from src.config import EXTRACTION_MODEL

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BaseExtractor(ABC):
    def __init__(self, model_name: str = EXTRACTION_MODEL):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        self.provider = GoogleProvider(api_key=self.api_key)
        self.model = GoogleModel(model_name, provider=self.provider)
        
        self.agent = Agent(
            self.model,
            instructions=self.get_system_prompt(),
            output_type=self.get_output_type(),
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Returns the system prompt for this specific agent."""
        pass

    @abstractmethod
    def get_output_type(self) -> Type[BaseModel]:
        """Returns the Pydantic model for the expected response."""
        pass

    def run(self, markdown_content: str) -> BaseModel:
        """Runs the extraction agency against the provided markdown content."""
        logging.info(f"Starting extraction with {self.__class__.__name__}...")
        
        try:
            result = self.agent.run_sync(f"Extract data from the following document:\n\n{markdown_content}")
            logging.info(f"Extraction successful for {self.__class__.__name__}.")
            return result.output
        except Exception as e:
            logging.error(f"Extraction failed for {self.__class__.__name__}: {e}")
            raise e

    async def run_async(self, markdown_content: str) -> BaseModel:
        """Runs the extraction agent asynchronously on the current event loop (concurrent, no threads)."""
        logging.info(f"Starting extraction with {self.__class__.__name__}...")
        prompt = f"Extract data from the following document:\n\n{markdown_content}"
        try:
            async with self.agent.iter(prompt) as agent_run:
                async for _ in agent_run:
                    pass
            out = agent_run.result.output
            logging.info(f"Extraction successful for {self.__class__.__name__}.")
            return out
        except Exception as e:
            logging.error(f"Extraction failed for {self.__class__.__name__}: {e}")
            raise
