from .extraction_prompt import extraction_prompt
from .query_generation_prompt import query_generation_prompt
from .consolidate_prompt import consolidate_prompt


# expose all prompts in this module for easy import
__all__ = ["extraction_prompt", "query_generation_prompt", "consolidate_prompt"]