{
    "name": "Delivery: Yandex Route + GPS",
    "summary": "Open batch delivery routes in Yandex Maps.",
    "version": "19.0.1.0.0",
    "category": "Inventory/Delivery",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "stock_picking_batch",
        "base",
        "web",
        "bus"
    ],
    "data": [
        "views/stock_picking_batch_views.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "delivery_yandex_gps/static/src/js/courier_tracker.js",
            "delivery_yandex_gps/static/src/js/courier_map.js",
            "delivery_yandex_gps/static/src/xml/courier_tracker.xml",
            "delivery_yandex_gps/static/src/xml/courier_map.xml",
        ],
    },
    "installable": True,
    "application": True,
}
