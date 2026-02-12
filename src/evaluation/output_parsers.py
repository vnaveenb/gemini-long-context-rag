"""LangChain output parsers for structured DQC evaluation results."""

from langchain_core.output_parsers import PydanticOutputParser

from src.models.dqc import DQCEvaluationResult

# Primary parser — validates against the Pydantic model
evaluation_parser = PydanticOutputParser(pydantic_object=DQCEvaluationResult)
