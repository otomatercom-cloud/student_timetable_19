from odoo import api, fields, models

from .timetable import fmt_time


class StudentAttendance(models.Model):
    _inherit = 'st.attendance'

    def _api_extra(self):
        res = super()._api_extra()
        self.ensure_one()
        slot = self.env['otm.timetable'].sudo().browse(self.slot_no).exists() if self.slot_no else False
        if slot:
            res.update({
                'start': slot.start_time, 'end': slot.end_time,
                'time': '%s - %s' % (fmt_time(slot.start_time), fmt_time(slot.end_time)),
                'faculty': slot.faculty_id.sudo().name or '',
                'room': slot.classroom_id.name or '',
                'timetable_id': slot.id,
            })
        return res

    @api.model
    def _generate_for_batch(self, batch, day):
        day = fields.Date.to_date(day)
        slots = self.env['otm.timetable'].sudo().search([
            ('batch_id', '=', batch.id), ('weekday', '=', str(day.weekday())), ('active', '=', True),
        ]).filtered(lambda s: (not s.valid_from or s.valid_from <= day) and (not s.valid_to or s.valid_to >= day))
        if not slots:
            return super()._generate_for_batch(batch, day)
        # an untouched whole-day draft (created before the timetable existed) is replaced by the periods
        stale = self.sudo().search([('batch_id', '=', batch.id), ('date', '=', day), ('slot_no', '=', 0),
                                    ('state', '=', 'draft'), ('topic', '=', False)])
        stale.filtered(lambda a: not a.attendance_line_ids.filtered(lambda l: l.status != 'present')).unlink()
        made = 0
        for slot in slots.sorted('start_time'):
            if self.sudo().search_count([('batch_id', '=', batch.id), ('date', '=', day),
                                         ('session', '=', 'full_day'), ('slot_no', '=', slot.id)]):
                continue
            self.sudo().create({
                'batch_id': batch.id, 'date': day, 'session': 'full_day', 'slot_no': slot.id,
                'subject_id': slot.subject_id.id, 'coordinator_id': False,
            })
            made += 1
        return made

    @api.model
    def _dashboard_timetable(self, day):
        day = fields.Date.to_date(day)
        Slot = self.env['otm.timetable']
        slots = Slot.search([('weekday', '=', str(day.weekday())), ('active', '=', True)]).filtered(
            lambda s: (not s.valid_from or s.valid_from <= day) and (not s.valid_to or s.valid_to >= day)
            and not self.env['st.attendance.holiday']._off_reason(s.batch_id, day))
        sheets = self.sudo().search([('date', '=', day), ('slot_no', 'in', slots.ids)])
        state = {sh.slot_no: (sh.id, sh.state) for sh in sheets}
        out = []
        for s in slots.sorted(lambda x: (x.start_time, x.batch_id.name or '')):
            d = s._api_dict()
            d['sheet_id'], d['state'] = state.get(s.id, (False, 'pending'))
            out.append(d)
        return out
