# from odoo import http


# class DeliveryYandexGps(http.Controller):
#     @http.route('/delivery_yandex_gps/delivery_yandex_gps', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/delivery_yandex_gps/delivery_yandex_gps/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('delivery_yandex_gps.listing', {
#             'root': '/delivery_yandex_gps/delivery_yandex_gps',
#             'objects': http.request.env['delivery_yandex_gps.delivery_yandex_gps'].search([]),
#         })

#     @http.route('/delivery_yandex_gps/delivery_yandex_gps/objects/<model("delivery_yandex_gps.delivery_yandex_gps"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('delivery_yandex_gps.object', {
#             'object': obj
#         })

