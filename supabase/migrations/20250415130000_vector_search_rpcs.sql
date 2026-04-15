-- RPC functions for hybrid retrieval: pgvector similarity + keyword search

-- Cosine similarity search via pgvector
create or replace function match_node_embeddings(
  query_embedding vector(1536),
  match_repo_id uuid,
  match_threshold float default 0.5,
  match_count int default 20
)
returns table (
  node_id text,
  similarity float
)
language plpgsql stable
as $$
begin
  return query
  select
    ne.node_id,
    1 - (ne.embedding <=> query_embedding) as similarity
  from public.node_embeddings ne
  where ne.repo_id = match_repo_id
    and 1 - (ne.embedding <=> query_embedding) > match_threshold
  order by ne.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Full-text keyword search over node code snippets via tsvector
create or replace function keyword_search_nodes(
  search_query text,
  match_repo_id uuid,
  match_count int default 20
)
returns table (
  node_id text,
  rank float
)
language plpgsql stable
as $$
begin
  return query
  select
    ne.node_id,
    ts_rank(ne.search_text, websearch_to_tsquery('english', search_query))::float as rank
  from public.node_embeddings ne
  where ne.repo_id = match_repo_id
    and ne.search_text is not null
    and ne.search_text @@ websearch_to_tsquery('english', search_query)
  order by rank desc
  limit match_count;
end;
$$;

-- Add HNSW index for pgvector (faster ANN search at scale)
create index if not exists node_embeddings_vector_idx
  on public.node_embeddings
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- GIN index for tsvector keyword search
create index if not exists node_embeddings_search_text_idx
  on public.node_embeddings
  using gin (search_text);
