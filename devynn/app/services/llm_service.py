"""
LLM service – thin wrapper around model.inference for future extensibility
(e.g. batching, caching, metrics).
"""

from model.inference import generate_output

__all__ = ["generate_output"]
