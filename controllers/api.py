from odoo import _, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from odoo.addons.student_details_19.controllers.api import (  # noqa: F401
    _is_manager, _need_attendance, api)

from ..models.timetable import WEEKDAYS


def _need_manager():
    if not _is_manager():
        raise AccessError(_("Only administrators can change the timetable."))


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
            'can_edit': _is_manager(),
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

    @api('/timetable/save', methods=('POST',))
    def save(self, body=None):
        _need_manager()
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
        _need_manager()
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
