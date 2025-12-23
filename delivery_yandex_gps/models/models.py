# from odoo import models, fields, api


# class delivery_yandex_gps(models.Model):
#     _name = 'delivery_yandex_gps.delivery_yandex_gps'
#     _description = 'delivery_yandex_gps.delivery_yandex_gps'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

