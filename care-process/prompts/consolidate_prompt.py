consolidate_prompt = """Consolidate and output a single JSON object in the QueryGenerationAgentSchema format using the results you are provided.

Include:
paper_title: the title of the paper
queries: a list where each item contains:
- query
- data_identifier
- data_identifier_type
- pds_metadata_fields (with fields)
- tool_validation (tools_used, constraints_summary, initial_match_count, final_match_count)

Rules:
- Do NOT hallucinate identifiers: data_identifier must be copied verbatim from the provided tool-validated results (no guessing or fabricating).
- Preserve counts from the provided results. If a count is missing, set initial_match_count to -1 and final_match_count to -1.
- Return JSON only and include no additional keys beyond the schema.
"""