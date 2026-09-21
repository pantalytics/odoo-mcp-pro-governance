from odoo import fields, models

from .. import compat


class WizardCreateRoleFromUser(models.TransientModel):
    _name = "wizard.create.role.from.user"
    _description = "Create role from user wizard"

    name = fields.Char(required=True)
    # MCP Pro (issue #26): the upstream "Assign to user" option is gone.
    # It created a res.users.role.line for the user the wizard was run
    # from, which is the assignment surface this module deliberately no
    # longer exposes -- a role here scopes an API key
    # (res_users_apikeys.x_role_id), it does not manage a person's rights.
    # Reading a user's groups into a fresh role stays useful, so the rest
    # of the wizard is untouched. Do not re-add the option when
    # re-vendoring OCA base_user_role.

    def create_from_user(self):
        self.ensure_one()

        user_ids = self.env.context.get("active_ids", [])
        assert len(user_ids) == 1

        user_id = user_ids[0]

        role_obj = self.env["res.users.role"]
        user_obj = self.env["res.users"]

        user = user_obj.browse(user_id)

        role = role_obj.create(
            {
                "name": self.name,
            }
        )

        role.implied_ids = [fields.Command.set(compat.user_groups(user).ids)]

        return {
            "context": self.env.context,
            "name": "User Role",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "res.users.role",
            "res_id": role.id,
            "target": "current",
            "type": "ir.actions.act_window",
        }
