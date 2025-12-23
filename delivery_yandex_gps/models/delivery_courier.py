from odoo import api, fields, models


class DeliveryCourier(models.Model):
    _name = "delivery.courier"
    _description = "Courier (Live GPS)"
    _rec_name = "user_id"

    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")

    is_tracking = fields.Boolean(default=False, index=True)

    last_latitude = fields.Float(digits=(10, 7))
    last_longitude = fields.Float(digits=(10, 7))
    last_accuracy_m = fields.Float()
    last_speed_mps = fields.Float()
    last_heading = fields.Float()
    last_update = fields.Datetime(index=True)

    is_online = fields.Boolean(compute="_compute_is_online", store=False)

    @api.depends("last_update")
    def _compute_is_online(self):
        now = fields.Datetime.now()
        for r in self:
            r.is_online = bool(r.last_update and (now - r.last_update).total_seconds() <= 120)
