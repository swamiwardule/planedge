# -*- coding: utf-8 -*-
{
    'name': "API Data",
    'summary': "",
    'description': "",
    'author': "Chetan Jadhav",
    'category': 'API',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','custom_project_management'],

    # always loaded
    'data': [
        'security/api_data_view_access.xml',
        'security/ir.model.access.csv',
        'views/api_data_view.xml',
        'views/menu_api_data_view.xml',
        'views/project_tower_view.xml',
        'views/project_info_view.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'custom_project_management/static/src/css/kanban_view.css',
    #         'custom_project_management/static/src/js/set_title.js',
    #     ],
    # },
    'license': 'OPL-1',

}
