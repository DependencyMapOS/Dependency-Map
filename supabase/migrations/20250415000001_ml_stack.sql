-- ML stack: pgvector, AST snapshots, embeddings, feedback, model artifacts; ast_graph on snapshots

create extension if not exists vector;

alter table public.dependency_snapshots
  add column if not exists ast_graph_json jsonb;

create table public.ast_graph_snapshots (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  branch text not null default 'main',
  commit_sha text not null,
  ast_graph_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (repo_id, branch, commit_sha)
);

create index ast_graph_snapshots_repo_branch on public.ast_graph_snapshots (repo_id, branch, created_at desc);

alter table public.ast_graph_snapshots enable row level security;

create policy "Members see ast_graph_snapshots"
  on public.ast_graph_snapshots for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = ast_graph_snapshots.repo_id and m.user_id = auth.uid()
    )
  );

-- Embeddings: 1536 dims for text-embedding-3-small (GNN projects in application code)
create table public.node_embeddings (
  id uuid primary key default gen_random_uuid(),
  node_id text not null,
  repo_id uuid not null references public.repositories (id) on delete cascade,
  commit_sha text,
  embedding vector(1536) not null,
  content_hash text not null,
  search_text tsvector,
  created_at timestamptz not null default now(),
  unique (repo_id, node_id, content_hash)
);

create index node_embeddings_repo on public.node_embeddings (repo_id);
-- ANN index (ivfflat/hnsw) can be added after sufficient rows for production workloads

alter table public.node_embeddings enable row level security;

create policy "Members see node_embeddings"
  on public.node_embeddings for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = node_embeddings.repo_id and m.user_id = auth.uid()
    )
  );

create table public.review_feedback (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  analysis_id uuid references public.pr_analyses (id) on delete set null,
  comment_node_id text not null,
  comment_type text not null,
  action text not null check (
    action in ('addressed', 'dismissed', 'thumbs_up', 'thumbs_down')
  ),
  created_at timestamptz not null default now()
);

create index review_feedback_org on public.review_feedback (org_id, created_at desc);

alter table public.review_feedback enable row level security;

create policy "Members see review_feedback"
  on public.review_feedback for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.org_id = review_feedback.org_id and m.user_id = auth.uid()
    )
  );

create table public.model_artifacts (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  model_name text not null,
  version text not null default '1',
  state_dict bytea,
  metrics jsonb not null default '{}'::jsonb,
  feedback_pairs_accumulated int not null default 0,
  last_feedback_training_at timestamptz,
  created_at timestamptz not null default now(),
  unique (org_id, model_name, version)
);

alter table public.model_artifacts enable row level security;

create policy "Members see model_artifacts"
  on public.model_artifacts for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.org_id = model_artifacts.org_id and m.user_id = auth.uid()
    )
  );
