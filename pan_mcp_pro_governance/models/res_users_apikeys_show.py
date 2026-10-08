"""The "API Key Ready" form names the rights the new key carries.

``res.users.apikeys.show`` is an abstract model with a single ``key``
field, filled from the action context by ``make_key``. The role rides
along the same way (``default_x_role_id``), so the form can show "Rights:
<role>" with the native arrow to the role, or "Same as your account".
"""

from odoo import fields, models


class ResUsersApikeysShow(models.AbstractModel):
    _inherit = "res.users.apikeys.show"

    x_role_id = fields.Many2one(
        comodel_name="res.users.role",
        string="Rights",
        readonly=True,
    )
