consolidate_prompt = """Consolidate and output a single JSON object in the paper_queries_pds format using the results you are provided.
Include:
paper_title: the title of the paper
queries: a list where each item contains:
query
data_identifier
data_identifier_type
pds_metadata_fields (with fields)
tool_validation (tools_used, constraints_summary, match_count)
Return JSON only and include no additional keys beyond the schema."""