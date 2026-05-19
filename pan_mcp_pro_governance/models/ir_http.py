"""Clear the API-key role thread-local at the start of every request.

Odoo workers reuse threads between requests. Without an explicit reset at
request boundaries, a thread-local set during an API-key request could
still be visible when the same worker thread serves a subsequent UI
session request — narrowing a UI user who has not opted in. We belt this
with a `_dispatch` override that resets the thread-local first thing.

The API-key auth path will then set the thread-local fresh during its own
`_check_credentials` override.
"""

from odoo import models

from .res_users_apikeys import clear_thread_api_key_role_id


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _dispatch(cls, endpoint):
        clear_thread_api_key_role_id()
        return super()._dispatch(endpoint)
