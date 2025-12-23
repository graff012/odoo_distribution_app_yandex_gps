from odoo import api, fields, models
from datetime import timedelta


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

    tracking_status = fields.Selection(
        selection=[
            ("tracking", "Tracking"),
            ("stopped", "Stopped"),
            ("stale", "Stale (no updates)"),
        ],
        compute="_compute_tracking_status",
        store=False,
    )

    @api.depends("is_tracking", "last_update")
    def _compute_tracking_status(self):
        cutoff = fields.Datetime.now() - timedelta(minutes=3)
        for r in self:
            if not r.is_tracking:
                r.tracking_status = "stopped"
            elif r.last_update and r.last_update < cutoff:
                r.tracking_status = "stale"
            else:
                r.tracking_status = "tracking"
