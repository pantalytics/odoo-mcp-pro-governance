"""Map legacy auditlog.rule scope (two m2m lists) onto x_scope.

Before this version a rule's scope was implicit:
  - both x_user_ids and x_apikey_ids empty -> log everything
  - only x_user_ids filled                -> log browser sessions for these users
  - only x_apikey_ids filled              -> log API calls from these keys
  - both filled                           -> compose per channel

The new model is explicit: x_scope in {all, browser, api, users}. The
user-scope semantics also changed -- listed users now have *both* their
browser sessions and their API key calls logged (no longer browser-only).

Mapping rules:
  both empty               -> 'all'
  only x_apikey_ids filled -> 'api'
  any x_user_ids filled    -> 'users'  (x_apikey_ids retained but unused;
                                        we log a warning when both were set
                                        because the old apikey scoping is
                                        dropped)
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Default everything to 'all' first (handles freshly added column +
    # any rule that has neither list filled).
    cr.execute(
        "UPDATE auditlog_rule SET x_scope = 'all' WHERE x_scope IS NULL"
    )

    # 'api' scope: only the apikey list was filled.
    cr.execute(
        """
        UPDATE auditlog_rule r
           SET x_scope = 'api'
         WHERE EXISTS (
                 SELECT 1 FROM x_auditlog_rule_apikey_rel a
                  WHERE a.rule_id = r.id
               )
           AND NOT EXISTS (
                 SELECT 1 FROM x_auditlog_rule_user_rel u
                  WHERE u.rule_id = r.id
               )
        """
    )

    # 'users' scope: any user list filled (takes precedence over apikey list).
    cr.execute(
        """
        UPDATE auditlog_rule r
           SET x_scope = 'users'
         WHERE EXISTS (
                 SELECT 1 FROM x_auditlog_rule_user_rel u
                  WHERE u.rule_id = r.id
               )
        """
    )

    cr.execute(
        """
        SELECT r.id, r.name
          FROM auditlog_rule r
         WHERE EXISTS (
                 SELECT 1 FROM x_auditlog_rule_user_rel u
                  WHERE u.rule_id = r.id
               )
           AND EXISTS (
                 SELECT 1 FROM x_auditlog_rule_apikey_rel a
                  WHERE a.rule_id = r.id
               )
        """
    )
    rows = cr.fetchall()
    for rid, rname in rows:
        _logger.warning(
            "MCP Pro 19.0.1.17.0: auditlog.rule id=%s (%r) had both x_user_ids "
            "and x_apikey_ids set under the old scope model. Mapped to "
            "scope='users'; the API key list is no longer applied as a filter. "
            "Review the rule and split into two rules if you need both the "
            "user-scoped activity and additional specific keys.",
            rid,
            rname,
        )
