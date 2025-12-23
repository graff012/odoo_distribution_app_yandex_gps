from datetime import timedelta

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError


class DeliveryYandexGPSController(http.Controller):

    @http.route("/delivery_yandex_gps/yandex_key", type="jsonrpc", auth="user", methods=["POST"])
    def yandex_key(self):
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_manager"):
            raise AccessError(_("You are not allowed to view the live map."))
        return request.env["ir.config_parameter"].sudo().get_param("delivery_yandex_gps.yandex_api_key") or ""

    @http.route("/delivery_yandex_gps/location/update", type="jsonrpc", auth="user", methods=["POST"])
    def update_location(self, latitude, longitude, accuracy_m=None, speed_mps=None, heading=None):
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_courier"):
            raise AccessError(_("You are not allowed to send courier location."))

        Courier = request.env["delivery.courier"]
        courier = Courier.search([("user_id", "=", request.env.user.id)], limit=1)
        if not courier:
            courier = Courier.create({"user_id": request.env.user.id})

        courier.write({
            "last_latitude": float(latitude),
            "last_longitude": float(longitude),
            "last_accuracy_m": float(accuracy_m) if accuracy_m is not None else False,
            "last_speed_mps": float(speed_mps) if speed_mps is not None else False,
            "last_heading": float(heading) if heading is not None else False,
            "last_update": fields.Datetime.now(),
            "is_tracking": True,
        })
        return {"ok": True}

    @http.route("/delivery_yandex_gps/location/stop", type="jsonrpc", auth="user", methods=["POST"])
    def stop_location(self):
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_courier"):
            raise AccessError(_("You are not allowed to stop tracking."))

        Courier = request.env["delivery.courier"]
        courier = Courier.search([("user_id", "=", request.env.user.id)], limit=1)
        if courier:
            courier.write({
                "is_tracking": False,
                "last_update": fields.Datetime.now(),
            })
        return {"ok": True}

    @http.route("/delivery_yandex_gps/location/list", type="jsonrpc", auth="user", methods=["POST"])
    def list_locations(self):
        if not request.env.user.has_group("delivery_yandex_gps.group_delivery_gps_manager"):
            raise AccessError(_("You are not allowed to read courier locations."))

        # Fallback: hide couriers who haven't updated recently (e.g., closed browser without pressing Stop)
        cutoff = fields.Datetime.now() - timedelta(minutes=3)

        couriers = request.env["delivery.courier"].search([
            ("is_tracking", "=", True),
            ("last_update", ">=", cutoff),
            ("last_latitude", "!=", False),
            ("last_longitude", "!=", False),
        ])

        return [{
            "courier_id": c.id,
            "name": c.user_id.name,
            "lat": c.last_latitude,
            "lon": c.last_longitude,
            "last_update": c.last_update.isoformat() if c.last_update else None,
        } for c in couriers]
