from .. import compat
from . import (
    auditlog_http_request,
    auditlog_http_session,
    auditlog_log,
    auditlog_rule,
    get_started,
    ir_http,
    res_users,
    res_users_apikeys,
    res_users_apikeys_description,
    res_users_apikeys_show,
    res_users_role,
)

# Odoo 20 merged ir.model.access + ir.rule into ir.access. Importing a module
# registers its model classes, so the 17-19 overrides must not be imported on
# 20 (their _inherit targets no longer exist), and vice versa.
if compat.ODOO_VERSION >= 20:
    from . import ir_access
else:
    from . import ir_model_access, ir_rule
