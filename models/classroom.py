from odoo import fields, models


class OtmClassroom(models.Model):
    _name = 'otm.classroom'
    _description = 'Classroom'
    _order = 'name'

    name = fields.Char(string="Classroom", required=True)
    code = fields.Char(string="Code")
    capacity = fields.Integer(string="Capacity")
    branch = fields.Selection(lambda self: self.env['student.details']._fields['branch'].selection,
                              string="Branch")
    note = fields.Char(string="Location / Notes")
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('unique(name)', 'A classroom with this name already exists.')
