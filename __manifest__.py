{
    'name': 'Student Timetable',
    'version': '19.0.1.0.0',
    'category': 'Education',
    'summary': 'Class timetable: batch / subject / faculty / classroom, with per-period attendance sheets',
    'description': "Classrooms, weekly timetable (batch, subject, faculty, classroom), clash detection and per-period attendance sheets.",
    'author': 'Otomater',
    'company': 'Otomater',
    'website': 'https://otomater.com',
    'license': 'OPL-1',
    'depends': ['student_details_19', 'faculty_19'],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/timetable_views.xml',
    ],
    'installable': True,
    'application': False,
}
