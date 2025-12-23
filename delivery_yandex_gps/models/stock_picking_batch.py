from odoo import models, _
from odoo.exceptions import UserError
from urllib.parse import quote

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    def _yandex_coord(self, partner, label):
        """Return 'lat,lon' string for Yandex rtext."""
        if not partner:
            raise UserError(_("Missing partner for: %s") % label)

        lat = partner.partner_latitude
        lon = partner.partner_longitude
        if lat is None or lon is None:
            raise UserError(_("Missing coordinates for %s: %s") % (label, partner.display_name))
        return f"{float(lat)},{float(lon)}"

    def action_open_yandex_route(self):
        self.ensure_one()

        # --- START POINT: warehouse address (preferred), fallback to company address ---
        warehouse = (
            self.picking_type_id.warehouse_id
            or self.picking_ids[:1].picking_type_id.warehouse_id
        )
        start_partner = (warehouse and warehouse.partner_id) or self.company_id.partner_id
        start = self._yandex_coord(start_partner, _("Start (Warehouse)"))

        # --- DESTINATIONS: unique delivery partners from pickings ---
        points = []
        seen_partner_ids = set()

        for picking in self.picking_ids:
            partner = picking.partner_id.commercial_partner_id or picking.partner_id
            if not partner:
                continue
            if partner.id in seen_partner_ids:
                continue
            seen_partner_ids.add(partner.id)
            points.append(self._yandex_coord(partner, _("Destination")))

        if not points:
            raise UserError(_("No deliveries in this batch."))

        # rtext format: lat,lon~lat,lon~lat,lon ... (multiple waypoints supported)
        rtext = "~".join([start] + points)

        # Use your region domain if you prefer:
        base_url = "https://yandex.uz/maps/"
        url = f"{base_url}?mode=routes&rtext={quote(rtext)}&rtt=auto"

        # Optional: center the map around the warehouse.
        # NOTE: Yandex `ll` typically uses "lon,lat" ordering (opposite of rtext).
        # Example patterns show ll=lon,lat while rtext is lat,lon. :contentReference[oaicite:2]{index=2}
        url += f"&ll={float(start_partner.partner_longitude)},{float(start_partner.partner_latitude)}&z=12"

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
