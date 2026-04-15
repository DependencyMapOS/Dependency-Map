-- Harden dm_swap: explicit column list (no SELECT *), omit id so live rows get fresh UUIDs

create or replace function public.dm_swap_cross_repo_edges(p_org_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.cross_repo_edges where org_id = p_org_id;
  insert into public.cross_repo_edges (
    org_id,
    source_repo_id,
    target_repo_id,
    source_path,
    target_package,
    edge_type,
    branch,
    created_at
  )
  select
    org_id,
    source_repo_id,
    target_repo_id,
    source_path,
    target_package,
    edge_type,
    branch,
    created_at
  from public.cross_repo_edges_staging
  where org_id = p_org_id;
  delete from public.cross_repo_edges_staging where org_id = p_org_id;
end;
$$;
