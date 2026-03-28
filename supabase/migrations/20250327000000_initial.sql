-- Dependency Map MVP schema: orgs, repos, analyses, RLS

create extension if not exists "pgcrypto";

-- Profiles (linked to auth.users)
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Users insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Organizations & membership
create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  created_at timestamptz not null default now()
);

alter table public.organizations enable row level security;

create table public.organization_members (
  org_id uuid not null references public.organizations (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('owner', 'admin', 'member')),
  primary key (org_id, user_id)
);

alter table public.organization_members enable row level security;

create policy "Members see org"
  on public.organizations for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.org_id = organizations.id and m.user_id = auth.uid()
    )
  );

create policy "Members see membership"
  on public.organization_members for select
  using (user_id = auth.uid());

-- GitHub App installation metadata
create table public.github_installations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  installation_id bigint not null unique,
  account_login text not null,
  created_at timestamptz not null default now()
);

alter table public.github_installations enable row level security;

create policy "Org members see installations"
  on public.github_installations for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.org_id = github_installations.org_id and m.user_id = auth.uid()
    )
  );

-- Linked repositories
create table public.repositories (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  github_repo_id bigint not null,
  full_name text not null,
  default_branch text not null default 'main',
  created_at timestamptz not null default now(),
  unique (github_repo_id)
);

alter table public.repositories enable row level security;

create policy "Members see repos"
  on public.repositories for select
  using (
    exists (
      select 1 from public.organization_members m
      where m.org_id = repositories.org_id and m.user_id = auth.uid()
    )
  );

-- PR / commit analyses
create table public.pr_analyses (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  pr_number int,
  base_sha text,
  head_sha text,
  status text not null check (status in ('pending', 'running', 'completed', 'failed')),
  summary_json jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now()
);

create index pr_analyses_repo_created on public.pr_analyses (repo_id, created_at desc);

alter table public.pr_analyses enable row level security;

create policy "Members see analyses"
  on public.pr_analyses for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = pr_analyses.repo_id and m.user_id = auth.uid()
    )
  );

-- Optional graph cache
create table public.dependency_snapshots (
  id uuid primary key default gen_random_uuid(),
  repo_id uuid not null references public.repositories (id) on delete cascade,
  commit_sha text not null,
  graph_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (repo_id, commit_sha)
);

alter table public.dependency_snapshots enable row level security;

create policy "Members see snapshots"
  on public.dependency_snapshots for select
  using (
    exists (
      select 1 from public.repositories r
      join public.organization_members m on m.org_id = r.org_id
      where r.id = dependency_snapshots.repo_id and m.user_id = auth.uid()
    )
  );

-- Pre-CI / machine API keys (hashed at rest; accessed via service role only)
create table public.api_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations (id) on delete cascade,
  name text not null,
  key_prefix text not null,
  key_hash text not null,
  created_at timestamptz not null default now(),
  last_used_at timestamptz
);

alter table public.api_keys enable row level security;

-- Auto-create profile on signup (name scoped to avoid colliding with other templates)
create or replace function public.dm_handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id) values (new.id);
  return new;
end;
$$;

drop trigger if exists dm_profiles_after_user_insert on auth.users;
create trigger dm_profiles_after_user_insert
  after insert on auth.users
  for each row execute function public.dm_handle_new_user();
