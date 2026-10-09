from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

WEEKDAYS = [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
            ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')]


def fmt_time(value):
    h, m = divmod(round((value or 0) * 60), 60)
    return '%02d:%02d' % (h % 24, m)


class OtmTimetable(models.Model):
    _name = 'otm.timetable'
    _description = 'Timetable Slot'
    _order = 'weekday, start_time, batch_id'

    name = fields.Char(compute='_compute_name', store=True)
    batch_id = fields.Many2one('student.batch', string="Batch", required=True, index=True,
                               ondelete='cascade')
    subject_id = fields.Many2one('otm.exam.subject', string="Subject", required=True)
    faculty_id = fields.Many2one('otm.faculty.details', string="Faculty")
    classroom_id = fields.Many2one('otm.classroom', string="Classroom")
    weekday = fields.Selection(WEEKDAYS, string="Day", required=True, default='0', index=True)
    start_time = fields.Float(string="Start", required=True, default=9.0)
    end_time = fields.Float(string="End", required=True, default=10.0)
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid To")
    active = fields.Boolean(default=True)

    @api.depends('batch_id', 'subject_id', 'weekday', 'start_time')
    def _compute_name(self):
        days = dict(WEEKDAYS)
        for rec in self:
            rec.name = '%s - %s %s - %s' % (rec.batch_id.name or '', days.get(rec.weekday, ''),
                                            fmt_time(rec.start_time), rec.subject_id.name or '')

    # ------------------------------------------------------------- validation
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if not (0 <= rec.start_time < 24 and 0 < rec.end_time <= 24):
                raise ValidationError(_("Time must be between 00:00 and 24:00."))
            if rec.end_time <= rec.start_time:
                raise ValidationError(_("End time must be after the start time."))

    @api.constrains('valid_from', 'valid_to')
    def _check_validity(self):
        for rec in self:
            if rec.valid_from and rec.valid_to and rec.valid_to < rec.valid_from:
                raise ValidationError(_("'Valid To' cannot be before 'Valid From'."))

    @api.constrains('batch_id', 'faculty_id', 'classroom_id', 'weekday', 'start_time', 'end_time',
                    'valid_from', 'valid_to', 'active')
    def _check_clash(self):
        for rec in self.filtered('active'):
            others = self.sudo().search([
                ('id', '!=', rec.id), ('weekday', '=', rec.weekday), ('active', '=', True),
                ('start_time', '<', rec.end_time), ('end_time', '>', rec.start_time)])
            others = others.filtered(lambda o: (not o.valid_to or not rec.valid_from or o.valid_to >= rec.valid_from)
                                     and (not rec.valid_to or not o.valid_from or o.valid_from <= rec.valid_to))
            for o in others:
                when = '%s %s-%s' % (dict(WEEKDAYS)[o.weekday], fmt_time(o.start_time), fmt_time(o.end_time))
                if o.batch_id == rec.batch_id:
                    raise ValidationError(_("Batch %(b)s already has a class at %(w)s (%(s)s).",
                                            b=rec.batch_id.name, w=when, s=o.subject_id.name))
                if rec.faculty_id and o.faculty_id == rec.faculty_id:
                    raise ValidationError(_("%(f)s is already teaching %(bt)s at %(w)s.",
                                            f=rec.faculty_id.name, bt=o.batch_id.name, w=when))
                if rec.classroom_id and o.classroom_id == rec.classroom_id:
                    raise ValidationError(_("Classroom %(c)s is already used by %(bt)s at %(w)s.",
                                            c=rec.classroom_id.name, bt=o.batch_id.name, w=when))

    # -------------------------------------------------------------------- api
    def _api_dict(self):
        self.ensure_one()
        return {
            'id': self.id, 'weekday': self.weekday, 'start': self.start_time, 'end': self.end_time,
            'time': '%s - %s' % (fmt_time(self.start_time), fmt_time(self.end_time)),
            'batch': {'id': self.batch_id.id, 'name': self.batch_id.name},
            'subject': {'id': self.subject_id.id, 'name': self.subject_id.name},
            'faculty': {'id': self.faculty_id.id, 'name': self.faculty_id.sudo().name} if self.faculty_id else None,
            'classroom': {'id': self.classroom_id.id, 'name': self.classroom_id.name} if self.classroom_id else None,
            'valid_from': fields.Date.to_string(self.valid_from) if self.valid_from else '',
            'valid_to': fields.Date.to_string(self.valid_to) if self.valid_to else '',
            'active': self.active,
        }
