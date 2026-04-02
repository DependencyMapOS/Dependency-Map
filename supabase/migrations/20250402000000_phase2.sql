-- Phase 2: dependency_edges, drift signals, risk hotspots

create table public.dependency_edges (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  commit_sha text not null,
  source_path text not null,
  target_path text not null,
  edge_type text not null default 'import',
  created_at timestamptz not null default now()
);

create index dependency_edges_repo_sha on public.dependency_edges (repo_id, commit_sha);

alter table public.dependency_edges enable row level security;

create policy "Members see dependency_edges"
  on public.dependency_edges for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = dependency_edges.repo_id and m.user_id = auth.uid()
    )
  );

create table public.branch_drift_signals (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  branch_a text not null,
  branch_b text not null,
  overlap_score real,
  signal_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index branch_drift_repo_created on public.branch_drift_signals (repo_id, created_at desc);

alter table public.branch_drift_signals enable row level security;

create policy "Members see drift signals"
  on public.branch_drift_signals for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = branch_drift_signals.repo_id and m.user_id = auth.uid()
    )
  );

create table public.risk_hotspots (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  file_path text not null,
  score real not null default 0,
  reason text,
  created_at timestamptz not null default now()
);

create index risk_hotspots_repo on public.risk_hotspots (repo_id, created_at desc);

alter table public.risk_hotspots enable row level security;

create policy "Members see risk_hotspots"
  on public.risk_hotspots for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = risk_hotspots.repo_id and m.user_id = auth.uid()
    )
  );
