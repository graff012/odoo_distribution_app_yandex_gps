# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class DeliveryCourier(models.Model):
    _name = "delivery.courier"
    _description = "Courier (Live GPS)"
    _rec_name = "user_id"

    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        ondelete="cascade",
    )

    # Tracking intent (courier pressed Start and did not press Stop)
    is_tracking = fields.Boolean(default=False, index=True)

    last_latitude = fields.Float(digits=(10, 7))
    last_longitude = fields.Float(digits=(10, 7))
    last_accuracy_m = fields.Float()
    last_speed_mps = fields.Float()
    last_heading = fields.Float()
    last_update = fields.Datetime(index=True)

    # Heartbeat: proves the courier app is alive
    last_heartbeat = fields.Datetime(index=True)

    # GPS condition reported by the browser
    gps_status = fields.Selection(
        [
            ("ok", "OK"),
            ("unavailable", "Unavailable / GPS Off"),
            ("denied", "Permission Denied"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        index=True,
    )
    last_error_code = fields.Integer()
    last_error_message = fields.Char(size=512)

    is_online = fields.Boolean(compute="_compute_is_online", store=False)

    tracking_status = fields.Selection(
        [
            ("tracking", "Tracking"),
            ("gps_off", "GPS Off / Unavailable"),
            ("offline", "App Offline"),
            ("stale", "Stale (no GPS updates)"),
            ("stopped", "Stopped"),
        ],
        compute="_compute_tracking_status",
        store=False,
    )

    @api.depends("last_heartbeat")
    def _compute_is_online(self):
        cutoff = fields.Datetime.now() - timedelta(seconds=60)
        for r in self:
            r.is_online = bool(r.last_heartbeat and r.last_heartbeat >= cutoff)

    @api.depends("is_tracking", "last_update", "last_heartbeat", "gps_status")
    def _compute_tracking_status(self):
        now = fields.Datetime.now()
        gps_cutoff = now - timedelta(minutes=3)
        hb_cutoff = now - timedelta(seconds=60)

        for r in self:
            if not r.is_tracking:
                r.tracking_status = "stopped"
                continue

            # No heartbeat (or too old) => app is offline
            if not r.last_heartbeat or r.last_heartbeat < hb_cutoff:
                r.tracking_status = "offline"
                continue

            # App is online but GPS is not delivering
            if r.gps_status in ("unavailable", "denied"):
                r.tracking_status = "gps_off"
                continue

            # App is online, intent is on, but no recent fix
            if not r.last_update or r.last_update < gps_cutoff:
                r.tracking_status = "stale"
                continue

            r.tracking_status = "tracking"
