# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError


class DeliveryYandexGPSController(http.Controller):

    # -----------------------------
    # Helpers
    # -----------------------------
    def _check_courier(self):
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_courier"):
            raise AccessError(_("You are not allowed to send courier location."))

    def _my_courier(self):
        Courier = request.env["delivery.courier"]
        courier = Courier.search([("user_id", "=", request.env.user.id)], limit=1)
        if not courier:
            courier = Courier.create({"user_id": request.env.user.id})
        return courier

    # -----------------------------
    # Manager
    # -----------------------------
    @http.route("/delivery_yandex_gps/yandex_key", type="jsonrpc", auth="user", methods=["POST"])
    def yandex_key(self):
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_manager"):
            raise AccessError(_("You are not allowed to view the live map."))
        return request.env["ir.config_parameter"].sudo().get_param("delivery_yandex_gps.yandex_api_key") or ""

    @http.route("/delivery_yandex_gps/location/list", type="jsonrpc", auth="user", methods=["POST"])
    def list_locations(self):
        """
        Manager map feed.

        IMPORTANT:
        - We do NOT filter by heartbeat/last_update here.
        - Manager wants to see last known position even for stale/offline
          to know where disconnection happened.
        """
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_manager"):
            raise AccessError(_("You are not allowed to read courier locations."))

        couriers = request.env["delivery.courier"].search([
            ("is_tracking", "=", True),
            ("last_latitude", "!=", False),
            ("last_longitude", "!=", False),
        ])

        return [{
            "courier_id": c.id,
            "name": c.user_id.name,
            "lat": c.last_latitude,
            "lon": c.last_longitude,
            "tracking_status": c.tracking_status,  # tracking / stale / offline / gps_off / stopped
            "gps_status": c.gps_status,
            "last_update": c.last_update.isoformat() if c.last_update else None,
            "last_heartbeat": c.last_heartbeat.isoformat() if c.last_heartbeat else None,
        } for c in couriers]

    # -----------------------------
    # Courier
    # -----------------------------
    @http.route("/delivery_yandex_gps/location/state", type="jsonrpc", auth="user", methods=["POST"])
    def location_state(self):
        self._check_courier()
        c = self._my_courier()
        return {
            "is_tracking": c.is_tracking,
            "gps_status": c.gps_status,
            "last_update": c.last_update.isoformat() if c.last_update else None,
            "last_heartbeat": c.last_heartbeat.isoformat() if c.last_heartbeat else None,
        }

    @http.route("/delivery_yandex_gps/location/start", type="jsonrpc", auth="user", methods=["POST"])
    def start_location(self):
        self._check_courier()
        c = self._my_courier()
        now = fields.Datetime.now()
        c.write({
            "is_tracking": True,
            "last_heartbeat": now,
            "gps_status": "unknown",
            "last_error_code": False,
            "last_error_message": False,
        })
        return {"ok": True}

    @http.route("/delivery_yandex_gps/location/ping", type="jsonrpc", auth="user", methods=["POST"])
    def ping(self, gps_status=None, error_code=None, error_message=None, **kw):
        self._check_courier()
        c = self._my_courier()

        vals = {"last_heartbeat": fields.Datetime.now()}

        if gps_status in ("ok", "unavailable", "denied", "unknown"):
            vals["gps_status"] = gps_status

        if error_code is not None:
            vals["last_error_code"] = int(error_code)

        if error_message is not None:
            vals["last_error_message"] = str(error_message)[:512]

        c.write(vals)
        return {"ok": True}

    @http.route("/delivery_yandex_gps/location/update", type="jsonrpc", auth="user", methods=["POST"])
    def update_location(self, latitude, longitude, accuracy_m=None, speed_mps=None, heading=None, **kw):
        self._check_courier()
        c = self._my_courier()
        now = fields.Datetime.now()

        c.write({
            "last_latitude": float(latitude),
            "last_longitude": float(longitude),
            "last_accuracy_m": float(accuracy_m) if accuracy_m is not None else False,
            "last_speed_mps": float(speed_mps) if speed_mps is not None else False,
            "last_heading": float(heading) if heading is not None else False,
            "last_update": now,
            "last_heartbeat": now,
            "gps_status": "ok",
            "is_tracking": True,  # keep intent ON once updates start
            "last_error_code": False,
            "last_error_message": False,
        })
        return {"ok": True}

    @http.route("/delivery_yandex_gps/location/stop", type="jsonrpc", auth="user", methods=["POST"])
    def stop_location(self):
        self._check_courier()
        c = self._my_courier()
        c.write({
            "is_tracking": False,
            "last_heartbeat": fields.Datetime.now(),
            "gps_status": "unknown",
        })
        return {"ok": True}
