from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'student_timetable_19')
class TestTimetable(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.batch = cls.env['student.batch'].create({'name': 'TT Batch'})
        cls.batch2 = cls.env['student.batch'].create({'name': 'TT Batch 2'})
        for b in (cls.batch, cls.batch2):
            cls.env['student.details'].create({'name': 'S-' + b.name, 'batch_id': b.id,
                                               'joining_status': 'new', 'branch': 'kochi'})
        cls.sub1 = cls.env['otm.exam.subject'].create({'name': 'TT Subject 1'})
        cls.sub2 = cls.env['otm.exam.subject'].create({'name': 'TT Subject 2'})
        cls.fac = cls.env['otm.faculty.details'].create({
            'first_name': 'Fa', 'last_name': 'Culty', 'email': 'f@x.com', 'mobile': '9000000000',
            'bank_name': 'B', 'account_no': '1', 'ifsc_code': 'X'})
        cls.room = cls.env['otm.classroom'].create({'name': 'TT Room 1', 'capacity': 30})
        cls.T = cls.env['otm.timetable']
        cls.env['ir.config_parameter'].sudo().set_param('student_details.att_weekly_off', '6')

    def _slot(self, **kw):
        vals = {'batch_id': self.batch.id, 'subject_id': self.sub1.id, 'faculty_id': self.fac.id,
                'classroom_id': self.room.id, 'weekday': '0', 'start_time': 9.0, 'end_time': 10.0}
        vals.update(kw)
        return self.T.create(vals)

    def test_clashes(self):
        self._slot()
        with self.assertRaises(ValidationError):   # same faculty, other batch, overlapping time
            self._slot(batch_id=self.batch2.id, classroom_id=False, start_time=9.5, end_time=10.5)
        with self.assertRaises(ValidationError):   # same room
            self._slot(batch_id=self.batch2.id, faculty_id=False, start_time=9.5, end_time=10.5)
        with self.assertRaises(ValidationError):   # same batch
            self._slot(faculty_id=False, classroom_id=False, start_time=9.0, end_time=9.5)
        self._slot(start_time=10.0, end_time=11.0, subject_id=self.sub2.id)   # back to back is fine
        with self.assertRaises(ValidationError):
            self._slot(start_time=11.0, end_time=11.0, faculty_id=False, classroom_id=False)

    def test_generation_per_period(self):
        s1 = self._slot()
        s2 = self._slot(start_time=10.0, end_time=11.0, subject_id=self.sub2.id, faculty_id=False, classroom_id=False)
        Att = self.env['st.attendance']
        mon = date(2026, 10, 12)   # Monday
        Att._auto_generate(mon)
        sheets = Att.search([('batch_id', '=', self.batch.id), ('date', '=', mon)])
        self.assertEqual(set(sheets.mapped('slot_no')), {s1.id, s2.id})
        self.assertEqual(sheets.mapped('subject_id'), self.sub1 | self.sub2)
        self.assertEqual(sheets.filtered(lambda s: s.slot_no == s1.id)._api_extra()['room'], 'TT Room 1')
        Att._auto_generate(mon)   # idempotent
        self.assertEqual(Att.search_count([('batch_id', '=', self.batch.id), ('date', '=', mon)]), 2)
        # batch without timetable keeps the single full-day sheet
        self.assertEqual(Att.search_count([('batch_id', '=', self.batch2.id), ('date', '=', mon)]), 1)
        # a weekday with no slot for batch 1 falls back to the full-day sheet
        tue = date(2026, 10, 13)
        Att._auto_generate(tue)
        self.assertEqual(Att.search([('batch_id', '=', self.batch.id), ('date', '=', tue)]).slot_no, 0)
