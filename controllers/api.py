from odoo import _, fields, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from odoo.addons.student_details_19.controllers.api import (  # noqa: F401
    _can_attendance, _is_manager, _need_attendance, api)

from ..models.timetable import WEEKDAYS


def _need_manager():
    if not _is_manager():
        raise AccessError(_("Only administrators can change this."))


def _need_edit():
    """Administrators, academic and course coordinators edit the timetable (record rules limit them to their batches)."""
    if not _can_attendance():
        raise AccessError(_("You cannot change the timetable."))


class TimetableApi(http.Controller):

    @api('/timetable/meta')
    def meta(self, body=None):
        _need_attendance()
        env = request.env
        return {
            'weekdays': [{'value': k, 'label': v} for k, v in WEEKDAYS],
            'subjects': [{'id': s.id, 'name': s.name} for s in env['otm.exam.subject'].search([])],
            'faculty': [{'id': f.id, 'name': f.name} for f in env['otm.faculty.details'].sudo().search([])],
            'classrooms': [{'id': c.id, 'name': c.name, 'capacity': c.capacity}
                           for c in env['otm.classroom'].search([])],
            'batches': [{'id': b.id, 'name': b.name} for b in env['student.batch'].search([])],
            'can_edit': _can_attendance(), 'is_manager': _is_manager(),
        }

    @api('/timetable')
    def timetable(self, body=None, batch_id=None, faculty_id=None, classroom_id=None, **kw):
        _need_attendance()
        domain = []
        if batch_id:
            domain.append(('batch_id', '=', int(batch_id)))
        if faculty_id:
            domain.append(('faculty_id', '=', int(faculty_id)))
        if classroom_id:
            domain.append(('classroom_id', '=', int(classroom_id)))
        rows = request.env['otm.timetable'].search(domain)
        return [r._api_dict() for r in rows]

    @api('/timetable/day')
    def day(self, body=None, date=None, batch_id=None, faculty_id=None, classroom_id=None, **kw):
        """Classes of one calendar date (weekday + validity), with holiday / weekly-off info per batch."""
        _need_attendance()
        env = request.env
        day = fields.Date.to_date(date) if date else fields.Date.context_today(env['otm.timetable'])
        domain = [('weekday', '=', str(day.weekday()))]
        for k, v in (('batch_id', batch_id), ('faculty_id', faculty_id), ('classroom_id', classroom_id)):
            if v:
                domain.append((k, '=', int(v)))
        slots = env['otm.timetable'].search(domain).filtered(
            lambda s: (not s.valid_from or s.valid_from <= day) and (not s.valid_to or s.valid_to >= day))
        Hol = env['st.attendance.holiday']
        rows, off = [], {}
        for s in slots:
            reason = Hol._off_reason(s.batch_id, day)
            if reason:
                off[s.batch_id.name] = reason
                continue
            rows.append(s._api_dict())
        return {'date': fields.Date.to_string(day), 'weekday': str(day.weekday()),
                'slots': rows, 'off': [{'batch': k, 'reason': v} for k, v in off.items()]}

    @api('/timetable/save', methods=('POST',))
    def save(self, body=None):
        _need_edit()
        T = request.env['otm.timetable']
        vals = {
            'batch_id': int(body['batch_id']), 'subject_id': int(body['subject_id']),
            'faculty_id': int(body['faculty_id']) if body.get('faculty_id') else False,
            'classroom_id': int(body['classroom_id']) if body.get('classroom_id') else False,
            'weekday': str(body['weekday']),
            'start_time': float(body['start']), 'end_time': float(body['end']),
            'valid_from': body.get('valid_from') or False, 'valid_to': body.get('valid_to') or False,
        }
        if body.get('id'):
            rec = T.browse(int(body['id']))
            rec.write(vals)
        else:
            rec = T.create(vals)
        return rec._api_dict()

    @api('/timetable/<int:slot_id>/delete', methods=('POST',))
    def delete(self, slot_id, body=None, **kw):
        _need_edit()
        request.env['otm.timetable'].browse(slot_id).unlink()
        return {'ok': True}

    @api('/classrooms')
    def classrooms(self, body=None, **kw):
        _need_attendance()
        rows = request.env['otm.classroom'].with_context(active_test=False).search([])
        return [{'id': c.id, 'name': c.name, 'code': c.code or '', 'capacity': c.capacity,
                 'branch': c.branch or '', 'note': c.note or '', 'active': c.active} for c in rows]

    @api('/classrooms/save', methods=('POST',))
    def classroom_save(self, body=None):
        _need_manager()
        C = request.env['otm.classroom'].with_context(active_test=False)
        if not (body.get('name') or '').strip():
            raise ValidationError(_("Classroom name is required."))
        vals = {'name': body['name'].strip(), 'code': body.get('code') or False,
                'capacity': int(body.get('capacity') or 0), 'branch': body.get('branch') or False,
                'note': body.get('note') or False, 'active': body.get('active', True)}
        rec = C.browse(int(body['id'])) if body.get('id') else C.create(vals)
        if body.get('id'):
            rec.write(vals)
        return {'id': rec.id}
