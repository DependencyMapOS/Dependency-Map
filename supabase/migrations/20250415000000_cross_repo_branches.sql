-- Cross-repo packages, cross-repo edges (with staging swap), branch-scoped snapshots, drift SHAs, org settings

-- Org-level tunables (fan-out caps, RLHF threshold, etc.)
alter table public.organizations
  add column if not exists settings jsonb not null default '{}'::jsonb;

-- Per-branch dependency snapshots (replaces unique on repo_id+commit_sha only)
alter table public.dependency_snapshots
  add column if not exists branch text not null default 'main';

alter table public.dependency_snapshots
  drop constraint if exists dependency_snapshots_repo_id_commit_sha_key;

alter table public.dependency_snapshots
  add constraint dependency_snapshots_repo_branch_commit_sha_key
    unique (repo_id, branch, commit_sha);

create index if not exists dependency_snapshots_repo_branch_created
  on public.dependency_snapshots (repo_id, branch, created_at desc);

-- Published package names per repo branch (from package.json / workspaces)
create table public.repo_packages (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  branch text not null default 'main',
  package_name text not null,
  package_version text not null default '',
  workspace_path text,
  updated_at timestamptz not null default now(),
  unique (repo_id, branch, package_name)
);

create index repo_packages_org_lookup on public.repo_packages (repo_id, branch);

alter table public.repo_packages enable row level security;

create policy "Members see repo_packages"
  on public.repo_packages for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = repo_packages.repo_id and m.user_id = auth.uid()
    )
  );

-- Cross-repo import edges (org-wide); populated via staging + transaction swap
create table public.cross_repo_edges (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  source_repo_id uuid not null references public.repositories (id) on delete cascade,
  target_repo_id uuid not null references public.repositories (id) on delete cascade,
  source_path text not null,
  target_package text not null,
  edge_type text not null default 'import' check (edge_type in ('import', 'manifest')),
  branch text not null default 'main',
  created_at timestamptz not null default now()
);

create index cross_repo_edges_org_branch on public.cross_repo_edges (org_id, branch);
create index cross_repo_edges_target on public.cross_repo_edges (org_id, target_repo_id);

alter table public.cross_repo_edges enable row level security;

create policy "Members see cross_repo_edges"
  on public.cross_repo_edges for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.org_id = cross_repo_edges.org_id and m.user_id = auth.uid()
    )
  );

create table public.cross_repo_edges_staging (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  source_repo_id uuid not null references public.repositories (id) on delete cascade,
  target_repo_id uuid not null references public.repositories (id) on delete cascade,
  source_path text not null,
  target_package text not null,
  edge_type text not null default 'import' check (edge_type in ('import', 'manifest')),
  branch text not null default 'main',
  created_at timestamptz not null default now()
);

create index cross_repo_edges_staging_org on public.cross_repo_edges_staging (org_id);

-- Drift: resolved SHAs for audit trail
alter table public.branch_drift_signals
  add column if not exists base_sha text;

alter table public.branch_drift_signals
  add column if not exists head_sha text;

alter table public.branch_drift_signals
  add column if not exists drift_type text check (
    drift_type is null or drift_type in ('structural', 'file-level', 'dependency')
  );

create index branch_drift_repo_branches on public.branch_drift_signals (repo_id, branch_a, branch_b);

-- Allow service role / worker writes on edges (RLS: no member insert — backend uses service role)
alter table public.dependency_edges
  add column if not exists branch text not null default 'main';

-- Atomic swap staging -> live (single transaction inside function)
create or replace function public.dm_swap_cross_repo_edges(p_org_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.cross_repo_edges where org_id = p_org_id;
  insert into public.cross_repo_edges
  select * from public.cross_repo_edges_staging where org_id = p_org_id;
  delete from public.cross_repo_edges_staging where org_id = p_org_id;
end;
$$;

revoke all on function public.dm_swap_cross_repo_edges(uuid) from public;
grant execute on function public.dm_swap_cross_repo_edges(uuid) to service_role;

alter table public.pr_analyses
  add column if not exists cross_repo boolean not null default false;
