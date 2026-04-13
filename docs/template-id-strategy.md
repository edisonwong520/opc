# Agent Template ID Strategy

`AgentTemplate.id` is currently a global string primary key. This keeps the MVP simple because core roles use stable ids such as `ceo`, `coo`, `cto`, `cfo`, `cmo`, and `sre`.

For true multi-tenant production use, organizations need to reuse the same role ids independently. Django does not support composite primary keys in the style needed here, so the production-safe path is:

1. Add a new surrogate primary key such as `uuid`.
2. Move the current string `id` into a new field named `role_id`.
3. Add `unique_together = [("organization", "role_id")]`.
4. Update all `Workstream.agent_template` references through the new surrogate key.
5. Update API serialization so `id` remains the public `role_id` for compatibility.
6. Backfill existing templates with `role_id = old id` and keep all legacy rows in the `default` organization.

Until that migration is implemented, OPC treats role ids as globally unique. This is acceptable for local/default organization use and early single-tenant deployments.
