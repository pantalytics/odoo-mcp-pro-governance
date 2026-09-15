# Role narrowing on Odoo 17

> Written 2026-09-15 after Pressure Control Solutions reported that a
> role-bound API key kept full admin rights on their Odoo 17 staging.

## What the design assumes

From Odoo 18 on, every permission path resolves a user's groups through a
single method:

```python
res.users._get_group_ids()   # 18+
```

`ir.model.access._get_allowed_models`, `ir.rule._get_rules` and
`res.users._has_group` all go through it. Overriding that one method is
enough to narrow an entire request to an API key's role, which is what
`models/res_users.py` does.

## Why Odoo 17 is different

Odoo 17 has no such method. Each call site runs its own SQL against
`res_groups_users_rel`, keyed on `uid`:

| Seam | 17 | 18 | 19 |
|---|---|---|---|
| `res.users._get_group_ids` | absent | present | present |
| `ir.model.access._get_allowed_models` | own SQL on `uid` | `_get_group_ids()` | `_get_group_ids()` |
| `ir.rule._get_rules` | own SQL on `uid` | `_get_group_ids()` | `_get_group_ids()` |
| `res.users._has_group` | own SQL on `uid` | `_get_group_ids()` | `_get_group_ids()` |
| `ir.rule._compute_domain` group filter | `user.groups_id` | `user.groups_id` | `user.all_group_ids` |
| `res.users` RPC credential cache | classmethod `check(db, uid, passwd)` | `_check_uid_passwd` | `_check_uid_passwd` |
| `env.execute_query` | absent | present | present |
| `ir.model.access._make_access_error` | absent | present | present |

Until 17.0.1.21.0 this meant a role-bound key on 17 was authenticated and
then never narrowed. The only narrowing that ran at all was our
`_get_allowed_models` override, and that crashed on `env.execute_query`,
which is where the customer's
`AttributeError: 'Environment' object has no attribute 'execute_query'`
came from.

## What we do instead

All version-gated in the shared source, no per-branch Python:

- `_get_group_ids` gets a plain fallback below 18, because core provides
  no implementation to call.
- `_has_group` and `ir.rule._get_rules` are overridden below 18 to answer
  from the role's groups.
- `res.users.check(db, uid, passwd)` is overridden below 18. It is the 17
  equivalent of `_check_uid_passwd`: `ormcache('uid', 'passwd')`, so on a
  cache hit the `_check_credentials` chain that normally sets the role is
  skipped. Without the override a key narrowed only on its first call per
  worker, which is why the customer saw the failure intermittently.
- `ir.rule._compute_domain` is reimplemented below 19. Core reads
  `self.env.user.groups_id` there — a stored-field read with no seam.
  **This gap affected Odoo 18 as well**, and in the direction that
  matters: rules bound to the user's non-role groups were dropped from
  the domain, so a narrowed key saw *more* rows than its role allowed.

`_make_access_error` stays as is. On 17 core builds the access-error text
inline in `check()`, so the role-aware wording is not shown there. The
access decision itself is narrowed on every version; only the message
wording differs.

## What breaks on the next major upgrade

`_mcp_compute_domain_narrowed` in `models/ir_rule.py` mirrors core's
17.0/18.0 `_compute_domain` body (they are byte-identical). It is dead
code from 19 on. If a future version changes how rules intersect with
groups below 19, this is the method to check. Add it to the major-upgrade
checklist in `CLAUDE.md`.

## How this is kept honest

`tests/test_role_narrowing.py` asks Odoo the questions Odoo asks itself
during a real RPC call, rather than calling our own methods and asserting
on their return values. The latter is why the 17.0 branch could report
"0 failed of 72" while narrowing did nothing at all.

Verified against the stock community images:

```bash
docker run -d --name mcp17db --network mcp17 \
  -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo postgres:15

docker run --rm --network mcp17 -e HOST=mcp17db -e USER=odoo -e PASSWORD=odoo \
  -v "$PWD/pan_mcp_pro_governance:/mnt/extra-addons/pan_mcp_pro_governance" \
  -v "$PWD/pan_mcp_auditlog:/mnt/extra-addons/pan_mcp_auditlog" \
  -v "$PWD/pan_mcp_user_role:/mnt/extra-addons/pan_mcp_user_role" \
  odoo:17 odoo -d v17test \
  --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons \
  -i pan_mcp_pro_governance --test-enable \
  --test-tags=/pan_mcp_pro_governance,/pan_mcp_auditlog,/pan_mcp_user_role \
  --stop-after-init --without-demo=all
```

Results on 2026-09-15:

| Version | Result |
|---|---|
| 17 | 0 failed of 87 |
| 18 | 0 failed of 80 (models + test ported onto the 18.0 branch) |
| 19 | new tests pass; 2 failures that are also on unmodified trunk |

Negative control: with `models/` restored to 17.0.1.20.0 and the new test
file kept, 4 of 7 narrowing tests fail on Odoo 17, including the exact
`execute_query` AttributeError the customer reported.
