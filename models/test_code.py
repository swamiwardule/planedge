from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
import pandas as pd
from collections import Counter
from datetime import datetime
from pathlib import Path
import xlsxwriter
import re

class TestCode(models.Model):
    _name = 'test.code'
    #_order = 'notification_dt desc, id desc'
    _description = "Test Code"

    name = fields.Char('Name')

    def extract_floor_number(self,floor_desc):
        # Extracts the first number from the string
        match = re.search(r'\d+', floor_desc)
        return int(match.group()) if match else -1
    
    def flat6_VJ_URBO_CENTRO(self):

        result = {
    '303': 'D2-303', '304': 'D2-304', '401': 'D2-401', '402': 'D2-402',
    '403': 'D2-403', '404': 'D2-404', '501': 'D2-501', '502': 'D2-502',
    '503': 'D2-503', '504': 'D2-504', '601': 'D2-601', '602': 'D2-602',
    '603': 'D2-603', '604': 'D2-604', '701': 'D2-701', '702': 'D2-702',
    '703': 'D2-703', '704': 'D2-704', '801': 'D2-801', '802': 'D2-802',
    '803': 'D2-803', '804': 'D2-804', '901': 'D2-901', '902': 'D2-902',
    '903': 'D2-903', '904': 'D2-904', '1001': 'D2-1001', '1002': 'D2-1002',
    '1003': 'D2-1003', '1004': 'D2-1004', '1101': 'D2-1101', '1102': 'D2-1102',
    '1103': 'D2-1103', '1104': 'D2-1104', '1201': 'D2-1201', '1202': 'D2-1202',
    '1203': 'D2-1203', '1204': 'D2-1204', '1301': 'D2-1301', '1302': 'D2-1302',
    '1303': 'D2-1303', '1304': 'D2-1304', '1401': 'D2-1401', '1402': 'D2-1402',
    '1403': 'D2-1403', '1404': 'D2-1404', '1501': 'D2-1501', '1502': 'D2-1502',
    '1503': 'D2-1503', '1504': 'D2-1504', '1601': 'D2-1601', '1602': 'D2-1602',
    '1603': 'D2-1603', '1604': 'D2-1604', '1701': 'D2-1701', '1702': 'D2-1702',
    '1703': 'D2-1703', '1704': 'D2-1704', '1801': 'D2-1801', '1802': 'D2-1802',
    '1803': 'D2-1803', '1804': 'D2-1804', '1901': 'D2-1901', '1902': 'D2-1902',
    '1903': 'D2-1903', '1904': 'D2-1904', '2001': 'D2-2001', '2002': 'D2-2002',
    '2003': 'D2-2003', '2004': 'D2-2004', '2101': 'D2-2101', '2102': 'D2-2102',
    '2103': 'D2-2103', '2104': 'D2-2104', '2201': 'D2-2201', '2202': 'D2-2202',
    '2203': 'D2-2203', '2204': 'D2-2204', '2301': 'D2-2301', '2302': 'D2-2302',
    '2303': 'D2-2303', '2304': 'D2-2304', '2401': 'D2-2401', '2402': 'D2-2402',
    '2403': 'D2-2403', '2404': 'D2-2404', '2501': 'D2-2501', '2502': 'D2-2502',
    '2503': 'D2-2503', '2504': 'D2-2504', '2601': 'D2-2601', '2602': 'D2-2602',
    '2603': 'D2-2603', '2604': 'D2-2604', '2701': 'D2-2701', '2702': 'D2-2702',
    '2703': 'D2-2703', '2704': 'D2-2704', '2801': 'D2-2801', '2802': 'D2-2802',
    '2803': 'D2-2803', '2804': 'D2-2804', '2901': 'D2-2901', '2902': 'D2-2902',
    '2903': 'D2-2903', '2904': 'D2-2904', '3001': 'D2-3001', '3002': 'D2-3002',
    '3003': 'D2-3003', '3004': 'D2-3004', '3101': 'D2-3101', '3102': 'D2-3102',
    '3103': 'D2-3103', '3104': 'D2-3104', '3201': 'D2-3201', '3202': 'D2-3202',
    '3203': 'D2-3203', '3204': 'D2-3204', '3301': 'D2-3301', '3302': 'D2-3302',
    '3303': 'D2-3303', '3304': 'D2-3304', '3401': 'D2-3401', '3402': 'D2-3402',
    '3403': 'D2-3403', '3404': 'D2-3404'
}

        print(result)
        #D2 BUILDING
        source_id = 294
        target_id = 347

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in result.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
    def flat5_VJ_URBO_CENTRO(self):

        result = {
    '303': 'D1-303',
    '304': 'D1-304',
    '401': 'D1-401',
    '402': 'D1-402',
    '403': 'D1-403',
    '404': 'D1-404',
    '501': 'D1-501',
    '502': 'D1-502',
    '503': 'D1-503',
    '504': 'D1-504',
    '601': 'D1-601',
    '602': 'D1-602',
    '603': 'D1-603',
    '604': 'D1-604',
    '701': 'D1-701',
    '702': 'D1-702',
    '703': 'D1-703',
    '704': 'D1-704',
    '801': 'D1-801',
    '802': 'D1-802',
    '803': 'D1-803',
    '804': 'D1-804',
    '901': 'D1-901',
    '902': 'D1-902',
    '903': 'D1-903',
    '904': 'D1-904',
    '1001': 'D1-1001',
    '1002': 'D1-1002',
    '1003': 'D1-1003',
    '1004': 'D1-1004',
    '1101': 'D1-1101',
    '1102': 'D1-1102',
    '1103': 'D1-1103',
    '1104': 'D1-1104',
    '1201': 'D1-1201',
    '1202': 'D1-1202',
    '1203': 'D1-1203',
    '1204': 'D1-1204',
    '1301': 'D1-1301',
    '1302': 'D1-1302',
    '1303': 'D1-1303',
    '1304': 'D1-1304',
    '1401': 'D1-1401',
    '1402': 'D1-1402',
    '1403': 'D1-1403',
    '1404': 'D1-1404',
    '1501': 'D1-1501',
    '1502': 'D1-1502',
    '1503': 'D1-1503',
    '1504': 'D1-1504',
    '1601': 'D1-1601',
    '1602': 'D1-1602',
    '1603': 'D1-1603',
    '1604': 'D1-1604',
    '1701': 'D1-1701',
    '1702': 'D1-1702',
    '1703': 'D1-1703',
    '1704': 'D1-1704',
    '1801': 'D1-1801',
    '1802': 'D1-1802',
    '1803': 'D1-1803',
    '1804': 'D1-1804',
    '1901': 'D1-1901',
    '1902': 'D1-1902',
    '1903': 'D1-1903',
    '1904': 'D1-1904',
    '2001': 'D1-2001',
    '2002': 'D1-2002',
    '2003': 'D1-2003',
    '2004': 'D1-2004',
    '2101': 'D1-2101',
    '2102': 'D1-2102',
    '2103': 'D1-2103',
    '2104': 'D1-2104',
    '2201': 'D1-2201',
    '2202': 'D1-2202',
    '2203': 'D1-2203',
    '2204': 'D1-2204',
    '2301': 'D1-2301',
    '2302': 'D1-2302',
    '2303': 'D1-2303',
    '2304': 'D1-2304',
    '2401': 'D1-2401',
    '2402': 'D1-2402',
    '2403': 'D1-2403',
    '2404': 'D1-2404',
    '2501': 'D1-2501',
    '2502': 'D1-2502',
    '2503': 'D1-2503',
    '2504': 'D1-2504',
    '2601': 'D1-2601',
    '2602': 'D1-2602',
    '2603': 'D1-2603',
    '2604': 'D1-2604',
    '2701': 'D1-2701',
    '2702': 'D1-2702',
    '2703': 'D1-2703',
    '2704': 'D1-2704',
    '2801': 'D1-2801',
    '2802': 'D1-2802',
    '2803': 'D1-2803',
    '2804': 'D1-2804',
    '2901': 'D1-2901',
    '2902': 'D1-2902',
    '2903': 'D1-2903',
    '2904': 'D1-2904',
    '3001': 'D1-3001',
    '3002': 'D1-3002',
    '3003': 'D1-3003',
    '3004': 'D1-3004',
    '3101': 'D1-3101',
    '3102': 'D1-3102',
    '3103': 'D1-3103',
    '3104': 'D1-3104',
    '3201': 'D1-3201',
    '3202': 'D1-3202',
    '3203': 'D1-3203',
    '3204': 'D1-3204',
    '3301': 'D1-3301',
    '3302': 'D1-3302',
    '3303': 'D1-3303',
    '3304': 'D1-3304',
    '3401': 'D1-3401',
    '3402': 'D1-3402',
    '3403': 'D1-3403',
    '3404': 'D1-3404'
}

        print(result)
        #C1C2 BUILDING
        source_id = 293
        target_id = 347

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in result.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
    def flat4_VJ_URBO_CENTRO(self):

        result = {
            '201': 'C2-201', '202': 'C2-202', '301': 'C2-301', '303': 'C2-303', '401': 'C2-401', '403': 'C2-403',
            '501': 'C2-501', '502': 'C2-502', '503': 'C2-503', '601': 'C2-601', '602': 'C2-602', '603': 'C2-603',
            '701': 'C2-701', '702': 'C2-702', '703': 'C2-703', '801': 'C2-801', '802': 'C2-802', '803': 'C2-803',
            '901': 'C2-901', '902': 'C2-902', '903': 'C2-903', '1001': 'C2-1001', '1002': 'C2-1002', '1003': 'C2-1003',
            '1101': 'C2-1101', '1102': 'C2-1102', '1103': 'C2-1103', '1201': 'C2-1201', '1202': 'C2-1202', '1203': 'C2-1203',
            '1301': 'C2-1301', '1302': 'C2-1302', '1303': 'C2-1303', '1401': 'C2-1401', '1402': 'C2-1402', '1403': 'C2-1403',
            '1501': 'C2-1501', '1502': 'C2-1502', '1503': 'C2-1503', '1601': 'C2-1601', '1602': 'C2-1602', '1603': 'C2-1603',
            '1701': 'C2-1701', '1702': 'C2-1702', '1703': 'C2-1703', '1801': 'C2-1801', '1802': 'C2-1802', '1803': 'C2-1803',
            '1901': 'C2-1901', '1902': 'C2-1902', '1903': 'C2-1903', '2001': 'C2-2001', '2002': 'C2-2002', '2003': 'C2-2003',
            '2101': 'C2-2101', '2102': 'C2-2102', '2103': 'C2-2103', '2201': 'C2-2201', '2202': 'C2-2202', '2203': 'C2-2203',
            '2301': 'C2-2301', '2302': 'C2-2302', '2303': 'C2-2303', '2401': 'C2-2401', '2402': 'C2-2402', '2403': 'C2-2403',
            '2501': 'C2-2501', '2502': 'C2-2502', '2503': 'C2-2503', '2601': 'C2-2601', '2602': 'C2-2602', '2603': 'C2-2603',
            '2701': 'C2-2701', '2702': 'C2-2702', '2703': 'C2-2703', '2801': 'C2-2801', '2802': 'C2-2802', '2803': 'C2-2803',
            '2901': 'C2-2901', '2902': 'C2-2902', '2903': 'C2-2903', '3001': 'C2-3001', '3002': 'C2-3002', '3003': 'C2-3003',
            '3101': 'C2-3101', '3102': 'C2-3102', '3103': 'C2-3103', '3201': 'C2-3201', '3202': 'C2-3202', '3203': 'C2-3203',
            '3301': 'C2-3301', '3302': 'C2-3302', '3303': 'C2-3303', '3401': 'C2-3401', '3402': 'C2-3402', '3403': 'C2-3403'
        }
        print(result)
        #C1C2 BUILDING
        source_id = 301
        target_id = 346

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in result.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    

    def flat3_VJ_URBO_CENTRO(self):
        result = {
    '202': 'C1-202', '203': 'C1-203', '302': 'C1-302', '303': 'C1-303', '402': 'C1-402', '403': 'C1-403', '404': 'C1-404',
    '502': 'C1-502', '503': 'C1-503', '504': 'C1-504', '601': 'C1-601', '602': 'C1-602', '603': 'C1-603', '604': 'C1-604',
    '701': 'C1-701', '702': 'C1-702', '703': 'C1-703', '704': 'C1-704', '801': 'C1-801', '802': 'C1-802', '803': 'C1-803',
    '804': 'C1-804', '901': 'C1-901', '902': 'C1-902', '903': 'C1-903', '904': 'C1-904', '1001': 'C1-1001', '1002': 'C1-1002',
    '1003': 'C1-1003', '1004': 'C1-1004', '1101': 'C1-1101', '1102': 'C1-1102', '1103': 'C1-1103', '1104': 'C1-1104',
    '1201': 'C1-1201', '1202': 'C1-1202', '1203': 'C1-1203', '1204': 'C1-1204', '1301': 'C1-1301', '1302': 'C1-1302',
    '1303': 'C1-1303', '1304': 'C1-1304', '1401': 'C1-1401', '1402': 'C1-1402', '1403': 'C1-1403', '1404': 'C1-1404',
    '1501': 'C1-1501', '1502': 'C1-1502', '1503': 'C1-1503', '1504': 'C1-1504', '1601': 'C1-1601', '1602': 'C1-1602',
    '1603': 'C1-1603', '1604': 'C1-1604', '1701': 'C1-1701', '1702': 'C1-1702', '1703': 'C1-1703', '1704': 'C1-1704',
    '1801': 'C1-1801', '1802': 'C1-1802', '1803': 'C1-1803', '1804': 'C1-1804', '1901': 'C1-1901', '1902': 'C1-1902',
    '1903': 'C1-1903', '1904': 'C1-1904', '2001': 'C1-2001', '2002': 'C1-2002', '2003': 'C1-2003', '2004': 'C1-2004',
    '2101': 'C1-2101', '2102': 'C1-2102', '2103': 'C1-2103', '2104': 'C1-2104', '2201': 'C1-2201', '2202': 'C1-2202',
    '2203': 'C1-2203', '2204': 'C1-2204', '2301': 'C1-2301', '2302': 'C1-2302', '2303': 'C1-2303', '2304': 'C1-2304',
    '2401': 'C1-2401', '2402': 'C1-2402', '2403': 'C1-2403', '2404': 'C1-2404', '2501': 'C1-2501', '2502': 'C1-2502',
    '2503': 'C1-2503', '2504': 'C1-2504', '2601': 'C1-2601', '2602': 'C1-2602', '2603': 'C1-2603', '2604': 'C1-2604',
    '2701': 'C1-2701', '2702': 'C1-2702', '2703': 'C1-2703', '2704': 'C1-2704', '2801': 'C1-2801', '2802': 'C1-2802',
    '2803': 'C1-2803', '2804': 'C1-2804', '2901': 'C1-2901', '2902': 'C1-2902', '2903': 'C1-2903', '2904': 'C1-2904',
    '3001': 'C1-3001', '3002': 'C1-3002', '3003': 'C1-3003', '3004': 'C1-3004', '3101': 'C1-3101', '3102': 'C1-3102',
    '3103': 'C1-3103', '3104': 'C1-3104', '3201': 'C1-3201', '3202': 'C1-3202', '3203': 'C1-3203', '3204': 'C1-3204',
    '3301': 'C1-3301', '3302': 'C1-3302', '3303': 'C1-3303', '3304': 'C1-3304', '3401': 'C1-3401', '3402': 'C1-3402',
    '3403': 'C1-3403','3404': 'C1-3404'
    }

        print(result)
        #C1C2 BUILDING
        source_id = 300
        target_id = 346

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in result.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
    def flat2_VJ_URBO_CENTRO(self):
            numbers = ['302', '303', '401', '402', '403', '501', '502', '503', '601', '602', '603', '604', '701', '702', '703', '704', '801', '802', '803', '804', '901', '902', '903', '904', '1001', '1002', '1003', '1004', '1101', '1102', '1103', '1104', '1201', '1202', '1203', '1204', '1301', '1302', '1303', '1304']
            result = {str(num): f'B2-{num}' for num in numbers}
            print(result)
            #B1B2 BUILDING
            source_id = 307
            target_id = 345

            source_tower = self.env['project.tower'].browse(source_id)
            target_tower = self.env['project.tower'].browse(target_id)

            source_map = {}

            # Step 1: Build flat → activity → checklist map from source
            for flat_line in source_tower.tower_flat_line_id:
                flat_key = flat_line.name.strip()
                source_map[flat_key] = {}

                for activity in flat_line.activity_ids:
                    act_key = activity.name.strip()
                    source_map[flat_key][act_key] = {
                        'act_rating': activity.act_rating,
                        'progress_percentage': activity.progress_percentage,
                        'checklists': {}
                    }

                    for checklist in activity.activity_type_ids:
                        ch_key = checklist.name.strip()
                        source_map[flat_key][act_key]['checklists'][ch_key] = {
                            'chcklist_status': checklist.status,
                            'act_type_rating': checklist.act_type_rating,
                            'progress_percentage': checklist.progress_percentage,
                            'user_maker': checklist.user_maker.id or False,
                            'user_checker': checklist.user_checker.id or False,
                            'user_approver': checklist.user_approver.id or False,

                        }

            # Step 2: Apply source values to matching mapped target flats
            counter = 0
            for target_flat in target_tower.tower_flat_line_id:
                # Reverse lookup: find source floor name from target using value
                source_flat_name = next((k for k, v in result.items() if v == target_flat.name), None)
                if not source_flat_name:
                    continue

                flat_data = source_map.get(source_flat_name.strip())
                if not flat_data:
                    continue

                for target_activity in target_flat.activity_ids:
                    act_data = flat_data.get(target_activity.name.strip())
                    if not act_data:
                        continue

                    target_activity.write({
                        'act_rating': act_data['act_rating'],
                        'progress_percentage': act_data['progress_percentage'],
                    })

                    for checklist in target_activity.activity_type_ids:
                        ch_data = act_data['checklists'].get(checklist.name.strip())
                        if ch_data:
                            checklist.write({
                                'status': ch_data['chcklist_status'],
                                'act_type_rating': ch_data['act_type_rating'],
                                'progress_percentage': ch_data['progress_percentage'],
                                'user_maker': ch_data['user_maker'],
                                'user_checker': ch_data['user_checker'],
                                'user_approver': ch_data['user_approver'],
                            })

                counter += 1
                # Optional commit to avoid timeout on large sets
                # if counter % 100 == 0:
                #     self.env.cr.commit()

            return True

######################################3
    def flat_VJ_URBO_CENTRO(self):
            numbers = [
                301, 302, 303, 401, 402, 403, 501, 502, 503, 601, 602, 603,
                701, 702, 703, 801, 802, 803, 901, 902, 903, 1001, 1002, 1003,
                1101, 1102, 1103, 1201, 1202, 1203, 1301, 1302, 1303, 1401, 1402, 1403,
                1501, 1502, 1503, 1601, 1602, 1603, 1701, 1702, 1703, 1801, 1802, 1803,
                1901, 1902, 1903, 2001, 2002, 2003, 2101, 2102, 2103, 2201, 2202, 2203,
                2301, 2302, 2303, 2401, 2402, 2403, 2501, 2502, 2503, 2601, 2602, 2603,
                2701, 2702, 2703, 2801, 2802, 2803, 2901, 2902, 2903, 3001, 3002, 3003,
                3101, 3102, 3103, 3201, 3202, 3203, 3301, 3302
            ]

            result = {str(num): f'B1-{num}' for num in numbers}

            print(result)
            #B1 BUILDING to B1B2
            source_id = 306
            target_id = 345
            source_tower = self.env['project.tower'].browse(source_id)
            target_tower = self.env['project.tower'].browse(target_id)

            source_map = {}

            # Step 1: Build flat → activity → checklist map from source
            for flat_line in source_tower.tower_flat_line_id:
                flat_key = flat_line.name.strip()
                source_map[flat_key] = {}

                for activity in flat_line.activity_ids:
                    act_key = activity.name.strip()
                    source_map[flat_key][act_key] = {
                        'act_rating': activity.act_rating,
                        'progress_percentage': activity.progress_percentage,
                        'checklists': {}
                    }

                    for checklist in activity.activity_type_ids:
                        ch_key = checklist.name.strip()
                        source_map[flat_key][act_key]['checklists'][ch_key] = {
                            'chcklist_status': checklist.status,
                            'act_type_rating': checklist.act_type_rating,
                            'progress_percentage': checklist.progress_percentage,
                            'user_maker': checklist.user_maker.id or False,
                            'user_checker': checklist.user_checker.id or False,
                            'user_approver': checklist.user_approver.id or False,

                        }

            # Step 2: Apply source values to matching mapped target flats
            counter = 0
            for target_flat in target_tower.tower_flat_line_id:
                # Reverse lookup: find source floor name from target using value
                source_flat_name = next((k for k, v in result.items() if v == target_flat.name), None)
                if not source_flat_name:
                    continue

                flat_data = source_map.get(source_flat_name.strip())
                if not flat_data:
                    continue

                for target_activity in target_flat.activity_ids:
                    act_data = flat_data.get(target_activity.name.strip())
                    if not act_data:
                        continue

                    target_activity.write({
                        'act_rating': act_data['act_rating'],
                        'progress_percentage': act_data['progress_percentage'],
                    })

                    for checklist in target_activity.activity_type_ids:
                        ch_data = act_data['checklists'].get(checklist.name.strip())
                        if ch_data:
                            checklist.write({
                                'status': ch_data['chcklist_status'],
                                'act_type_rating': ch_data['act_type_rating'],
                                'progress_percentage': ch_data['progress_percentage'],
                                'user_maker': ch_data['user_maker'],
                                'user_checker': ch_data['user_checker'],
                                'user_approver': ch_data['user_approver'],
                            })

                counter += 1
                # Optional commit to avoid timeout on large sets
                # if counter % 100 == 0:
                #     self.env.cr.commit()

            return True
    
#########################################
    def floor_VJ_URBO_CENTRO(self):
            #A BUILDING
            # source_id = 292
            # target_id = 344
            #B BUILDING
            # source_id = 146
            # target_id = 345
            #C BUILDING
            # source_id = 147
            # target_id = 346
            #D BUILDING
            # source_id = 148
            # target_id = 347
            # no floors for E,F and G
            floor_mapping = {
                "Ground floor": "GROUND FLOOR",
                "1st floor": "FLOOR 1",
                "2nd floor": "FLOOR 2",
                "3rd floor": "FLOOR 3",
                "4th floor": "FLOOR 4",
                "5th floor": "FLOOR 5",
                "6th floor": "FLOOR 6",
                "7th floor": "FLOOR 7",
                "8th floor": "FLOOR 8",
                "9th floor": "FLOOR 9",
                "10th floor": "FLOOR 10",
                "11th floor": "FLOOR 11",
                "12th floor": "FLOOR 12",
                "13th floor": "FLOOR 13",
                "14th floor": "FLOOR 14",
                "15th floor": "FLOOR 15",
                "16th floor": "FLOOR 16",
                "17th floor": "FLOOR 17",
                "18th floor": "FLOOR 18",
                "19th floor": "FLOOR 19",
                "20th floor": "FLOOR 20",
                "21st floor": "FLOOR 21",
                "22nd floor": "FLOOR 22",
                "23rd floor": "FLOOR 23",
                "24th floor": "FLOOR 24",
                "25th floor": "FLOOR 25",
                "26th floor": "FLOOR 26",
                "27th floor": "FLOOR 27",
                "28th floor": "FLOOR 28",
                "29th floor": "FLOOR 29",
                "30th floor": "FLOOR 30",
                "31st floor": "FLOOR 31",
                "32nd floor": "FLOOR 32",
                "33st floor": "FLOOR 33",
                "34nd floor": "FLOOR 34"
            }

            source_tower = self.env['project.tower'].browse(source_id)
            target_tower = self.env['project.tower'].browse(target_id)

            source_map = {}

            # Step 1: Build flat → activity → checklist map from source
            for flat_line in source_tower.tower_floor_line_id:
                flat_key = flat_line.name.strip()
                source_map[flat_key] = {}

                for activity in flat_line.activity_ids:
                    act_key = activity.name.strip()
                    source_map[flat_key][act_key] = {
                        'act_rating': activity.act_rating,
                        'progress_percentage': activity.progress_percentage,
                        'checklists': {}
                    }

                    for checklist in activity.activity_type_ids:
                        ch_key = checklist.name.strip()
                        source_map[flat_key][act_key]['checklists'][ch_key] = {
                            'chcklist_status': checklist.status,
                            'act_type_rating': checklist.act_type_rating,
                            'progress_percentage': checklist.progress_percentage,
                            'user_maker': checklist.user_maker.id or False,
                            'user_checker': checklist.user_checker.id or False,
                            'user_approver': checklist.user_approver.id or False,

                        }

            # Step 2: Apply source values to matching mapped target flats
            counter = 0
            for target_flat in target_tower.tower_floor_line_id:
                # Reverse lookup: find source floor name from target using value
                source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
                if not source_flat_name:
                    continue

                flat_data = source_map.get(source_flat_name.strip())
                if not flat_data:
                    continue

                for target_activity in target_flat.activity_ids:
                    act_data = flat_data.get(target_activity.name.strip())
                    if not act_data:
                        continue

                    target_activity.write({
                        'act_rating': act_data['act_rating'],
                        'progress_percentage': act_data['progress_percentage'],
                    })

                    for checklist in target_activity.activity_type_ids:
                        ch_data = act_data['checklists'].get(checklist.name.strip())
                        if ch_data:
                            checklist.write({
                                'status': ch_data['chcklist_status'],
                                'act_type_rating': ch_data['act_type_rating'],
                                'progress_percentage': ch_data['progress_percentage'],
                                'user_maker': ch_data['user_maker'],
                                'user_checker': ch_data['user_checker'],
                                'user_approver': ch_data['user_approver'],
                            })

                counter += 1
                # Optional commit to avoid timeout on large sets
                # if counter % 100 == 0:
                #     self.env.cr.commit()

            return True
        
        
######################################
    def flat_VJ_INDILIFE_KHARADI(self):
        #Wing A
        # source_id = 295
        # target_id = 382
        #Wing B
        source_id = 296
        target_id = 383
            
        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            flat_data = source_map.get(target_flat.name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                # Batch update activity
                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

            return True
    
#################################33
    def floor_VJ_INDILIFE_KHARADI(self):
        #Wing A
        # source_id = 295
        # target_id = 382
        #Wing B
        source_id = 296
        target_id = 383
        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
######################################
    def flat_VJ_ENCHANTE(self):
            
        #A Building
        # source_id = 125
        # target_id = 327
        #B Building
        # source_id = 126
        # target_id = 328
        #C Building
        # source_id = 127
        # target_id = 329
        #D Building
        # source_id = 128
        # target_id = 330
        #E Building
        # source_id = 129
        # target_id = 331
         #E Building
        source_id = 130
        target_id = 332
            
        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            flat_data = source_map.get(target_flat.name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                # Batch update activity
                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

            return True
    
#################################33
    def floor_VJ_ENCHANTE(self):
        #A Building
        # source_id = 125
        # target_id = 327
        #B Building
        # source_id = 126
        # target_id = 328
        #C Building
        # source_id = 127
        # target_id = 329
        #D Building
        # source_id = 128
        # target_id = 330
        #E Building
        # source_id = 129
        # target_id = 331
        #E Building
        source_id = 130
        target_id = 332
        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
######################################
    def flat_VJ_ETERNITEE(self):
            
        #A Building
        # source_id = 137
        # target_id = 318
        #B Building
        # source_id = 138
        # target_id = 319
        #C Building
        # source_id = 139
        # target_id = 320
        #D Building
        # source_id = 140
        # target_id = 321
        #E Building
        source_id = 184
        target_id = 322
            
        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            flat_data = source_map.get(target_flat.name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                # Batch update activity
                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

            return True
    
#################################33
    def floor_VJ_ETERNITEE(self):
        #A Building
        # source_id = 137
        # target_id = 318
        #B Building
        # source_id = 138
        # target_id = 319
        #C Building
        # source_id = 139
        # target_id = 320
        #D Building
        # source_id = 140
        # target_id = 321
        #E Building
        source_id = 184
        target_id = 322
        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
##################################################
    def flat_VJ_PORTIA_GRANDE(self):
            
        #Tower 1
        # source_id = 141
        # target_id = 333
        #Tower 2
        source_id = 142
        target_id = 342
            
        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            flat_data = source_map.get(target_flat.name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                # Batch update activity
                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

            return True
    
#################################33
    def floor_VJ_PORTIA_GRANDE(self):
        #Tower 1
        # source_id = 141
        # target_id = 333
        #Tower 2
        source_id = 142
        target_id = 342
        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    

##################################################
    def flat_VJ_PBC(self):
            
        #T1
        # source_id = 171
        # target_id = 354
        #T2
        # source_id = 172
        # target_id = 355
        #T3
        # source_id = 143
        # target_id = 356
        #T4
        # source_id = 144
        # target_id = 357
        #T5
        source_id = 303
        target_id = 358
            

        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            #if flat_key == '702':
            if 1:
                source_map[flat_key] = {}

                for activity in flat_line.activity_ids:
                    act_key = activity.name.strip()
                    source_map[flat_key][act_key] = {
                        'act_rating': activity.act_rating,
                        'progress_percentage': activity.progress_percentage,
                        'checklists': {}
                    }

                    for checklist in activity.activity_type_ids:
                        ch_key = checklist.name.strip()
                        source_map[flat_key][act_key]['checklists'][ch_key] = {
                            'chcklist_status': checklist.status,
                            'act_type_rating': checklist.act_type_rating,
                            'progress_percentage': checklist.progress_percentage,
                            'user_maker': checklist.user_maker.id or False,
                            'user_checker': checklist.user_checker.id or False,
                            'user_approver': checklist.user_approver.id or False,
                        }
        #_logger.info("--source_map-: %s",(source_map))
        
        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            #_logger.info("--target_datatarget_datatarget_data--: %s",(target_flat.name.strip()))

            #if target_flat.name.strip() == '702':
            if 1:
                #_logger.info("--target_datatarget_datatarget_data--: %s",(target_flat.name.strip()))

                flat_data = source_map.get(target_flat.name.strip())
                if not flat_data:
                    continue

                for target_activity in target_flat.activity_ids:
                    act_data = flat_data.get(target_activity.name.strip())
                    if not act_data:
                        continue
                    #_logger.info("--act_dataact_data--: %s",(act_data))


                    # Batch update activity
                    target_activity.write({
                        'act_rating': act_data['act_rating'],
                        'progress_percentage': act_data['progress_percentage'],
                    })

                    for checklist in target_activity.activity_type_ids:
                        ch_data = act_data['checklists'].get(checklist.name.strip())
                        if ch_data:
                            checklist.write({
                                'status': ch_data['chcklist_status'],
                                'act_type_rating': ch_data['act_type_rating'],
                                'progress_percentage': ch_data['progress_percentage'],
                                'user_maker': ch_data['user_maker'],
                                'user_checker': ch_data['user_checker'],
                                'user_approver': ch_data['user_approver'],
                            })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
#################################33
    def floor_VJ_PBC(self):
        #T1
        # source_id = 171
        # target_id = 354
        #T2
        # source_id = 172
        # target_id = 355
        #T3
        # source_id = 143
        # target_id = 356
        #T4
        source_id = 144
        target_id = 357
        #T5
        # source_id = 303
        # target_id = 358
        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
#################################################3
    def flat_VJ_NUOVOCENTRO(self):
            
        #A
        # source_id = 133
        # target_id = 324
        #B
        # source_id = 134
        # target_id = 325
        # C
        source_id = 135
        target_id = 338
            
        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            flat_data = source_map.get(target_flat.name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                # Batch update activity
                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

            return True
    
#################################33
    def floor_VJ_NUOVOCENTRO(self):
        #A
        # source_id = 133
        # target_id = 324
        #B
        # source_id = 134
        # target_id = 325
        # C
        source_id = 135
        target_id = 338
        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True
    
#################################################3
    def flat_vj_pkc_and_ca(self):
            #T1
            source_id = 285
            target_id = 375
            #T2
            # source_id = 286
            # target_id = 376
            # #T3
            # source_id = 287
            # target_id = 377
            # # #T4
            # source_id = 288
            # target_id = 378
            # # #T5
            # source_id = 289
            # target_id = 336
            # # #T6
            # source_id = 290
            # target_id = 337

            # Fetch source and target towers
            source_tower = self.env['project.tower'].browse(source_id)
            target_tower = self.env['project.tower'].browse(target_id)

            source_map = {}

            # Step 1: Build flat → activity → checklist map from source
            for flat_line in source_tower.tower_flat_line_id:
                flat_key = flat_line.name.strip()
                source_map[flat_key] = {}

                for activity in flat_line.activity_ids:
                    act_key = activity.name.strip()
                    source_map[flat_key][act_key] = {
                        'act_rating': activity.act_rating,
                        'progress_percentage': activity.progress_percentage,
                        'checklists': {}
                    }

                    for checklist in activity.activity_type_ids:
                        ch_key = checklist.name.strip()
                        source_map[flat_key][act_key]['checklists'][ch_key] = {
                            'chcklist_status': checklist.status,
                            'act_type_rating': checklist.act_type_rating,
                            'progress_percentage': checklist.progress_percentage,
                            'user_maker': checklist.user_maker.id or False,
                            'user_checker': checklist.user_checker.id or False,
                            'user_approver': checklist.user_approver.id or False,
                        }

            # Step 2: Apply source values to matching target flats
            counter = 0
            for target_flat in target_tower.tower_flat_line_id:
                flat_data = source_map.get(target_flat.name.strip())
                if not flat_data:
                    continue

                for target_activity in target_flat.activity_ids:
                    act_data = flat_data.get(target_activity.name.strip())
                    if not act_data:
                        continue

                    # Batch update activity
                    target_activity.write({
                        'act_rating': act_data['act_rating'],
                        'progress_percentage': act_data['progress_percentage'],
                    })

                    for checklist in target_activity.activity_type_ids:
                        ch_data = act_data['checklists'].get(checklist.name.strip())
                        if ch_data:
                            checklist.write({
                                'status': ch_data['chcklist_status'],
                                'act_type_rating': ch_data['act_type_rating'],
                                'progress_percentage': ch_data['progress_percentage'],
                                'user_maker': ch_data['user_maker'],
                                'user_checker': ch_data['user_checker'],
                                'user_approver': ch_data['user_approver'],
                            })

                counter += 1

                # Optional: Commit every 100 flats to avoid timeout
                # if counter % 100 == 0:
                #     self.env.cr.commit()

            return True
    
#################################33
    def floor_vj_pkc_and_ca(self):
        #T1
        source_id = 285
        target_id = 375
        #T2
        # source_id = 286
        # target_id = 376
        # # #T3
        # source_id = 287
        # target_id = 377
        # # #T4
        # source_id = 288
        # target_id = 378
        # # #T5
        # source_id = 289
        # target_id = 336
        # # #T6
        # source_id = 290
        # target_id = 337

        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,

                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True

    
###########################################################################


    def floor_vj_indlife_wakad(self):
        source_id = 169
        target_id = 352

        floor_mapping = {
            "Ground floor": "GROUND FLOOR",
            "1st floor": "FLOOR 1",
            "2nd floor": "FLOOR 2",
            "3rd floor": "FLOOR 3",
            "4th floor": "FLOOR 4",
            "5th floor": "FLOOR 5",
            "6th floor": "FLOOR 6",
            "7th floor": "FLOOR 7",
            "8th floor": "FLOOR 8",
            "9th floor": "FLOOR 9",
            "10th floor": "FLOOR 10",
            "11th floor": "FLOOR 11",
            "12th floor": "FLOOR 12",
            "13th floor": "FLOOR 13",
            "14th floor": "FLOOR 14",
            "15th floor": "FLOOR 15",
            "16th floor": "FLOOR 16",
            "17th floor": "FLOOR 17",
            "18th floor": "FLOOR 18",
            "19th floor": "FLOOR 19",
            "20th floor": "FLOOR 20",
            "21st floor": "FLOOR 21",
            "22nd floor": "FLOOR 22",
            "23rd floor": "FLOOR 23",
            "24th floor": "FLOOR 24",
            "25th floor": "FLOOR 25",
            "26th floor": "FLOOR 26",
            "27th floor": "FLOOR 27",
            "28th floor": "FLOOR 28",
            "29th floor": "FLOOR 29",
            "30th floor": "FLOOR 30",
            "31st floor": "FLOOR 31",
            "32nd floor": "FLOOR 32"
        }

        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_floor_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching mapped target flats
        counter = 0
        for target_flat in target_tower.tower_floor_line_id:
            # Reverse lookup: find source floor name from target using value
            source_flat_name = next((k for k, v in floor_mapping.items() if v == target_flat.name), None)
            if not source_flat_name:
                continue

            flat_data = source_map.get(source_flat_name)
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1
            # Optional commit to avoid timeout on large sets
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True


############################################################################

    def flat_vj_indlife_wakad(self):
        source_id = 169
        target_id = 352

        # Fetch source and target towers
        source_tower = self.env['project.tower'].browse(source_id)
        target_tower = self.env['project.tower'].browse(target_id)

        source_map = {}

        # Step 1: Build flat → activity → checklist map from source
        for flat_line in source_tower.tower_flat_line_id:
            flat_key = flat_line.name.strip()
            source_map[flat_key] = {}

            for activity in flat_line.activity_ids:
                act_key = activity.name.strip()
                source_map[flat_key][act_key] = {
                    'act_rating': activity.act_rating,
                    'progress_percentage': activity.progress_percentage,
                    'checklists': {}
                }

                for checklist in activity.activity_type_ids:
                    ch_key = checklist.name.strip()
                    source_map[flat_key][act_key]['checklists'][ch_key] = {
                        'chcklist_status': checklist.status,
                        'act_type_rating': checklist.act_type_rating,
                        'progress_percentage': checklist.progress_percentage,
                        'user_maker': checklist.user_maker.id or False,
                        'user_checker': checklist.user_checker.id or False,
                        'user_approver': checklist.user_approver.id or False,
                    }

        # Step 2: Apply source values to matching target flats
        counter = 0
        for target_flat in target_tower.tower_flat_line_id:
            flat_data = source_map.get(target_flat.name.strip())
            if not flat_data:
                continue

            for target_activity in target_flat.activity_ids:
                act_data = flat_data.get(target_activity.name.strip())
                if not act_data:
                    continue

                # Batch update activity
                target_activity.write({
                    'act_rating': act_data['act_rating'],
                    'progress_percentage': act_data['progress_percentage'],
                })

                for checklist in target_activity.activity_type_ids:
                    ch_data = act_data['checklists'].get(checklist.name.strip())
                    if ch_data:
                        checklist.write({
                            'status': ch_data['chcklist_status'],
                            'act_type_rating': ch_data['act_type_rating'],
                            'progress_percentage': ch_data['progress_percentage'],
                            'user_maker': ch_data['user_maker'],
                            'user_checker': ch_data['user_checker'],
                            'user_approver': ch_data['user_approver'],
                        })

            counter += 1

            # Optional: Commit every 100 flats to avoid timeout
            # if counter % 100 == 0:
            #     self.env.cr.commit()

        return True

    
    # def activity_submit_for_source_target_towers(self):
    #     source = 169
    #     target = 352
    #     source_data = []
    #     target_data = []

    #     source_tower = self.env['project.tower'].browse(source)
    #     source_data = []

    #     # Build nested source structure for flat 101
    #     for flat_line in source_tower.tower_flat_line_id:
          
    #         flat_dict = {
    #             'flat_name': flat_line.name,
    #             'activities': []
    #         }
    #         for activity in flat_line.activity_ids:
    #             activity_dict = {
    #                 'act_name': activity.name,
    #                 'act_rating': activity.act_rating,
    #                 'progress_percentage': activity.progress_percentage,
    #                 'checklists': []
    #             }
    #             for checklist in activity.activity_type_ids:
    #                 checklist_dict = {
    #                     'chcklist_name': checklist.name,
    #                     'chcklist_status': checklist.status,
    #                     'act_type_rating': checklist.act_type_rating,
    #                     'progress_percentage': checklist.progress_percentage,
    #                 }
    #                 activity_dict['checklists'].append(checklist_dict)
    #             flat_dict['activities'].append(activity_dict)
    #         source_data.append(flat_dict)

    #         # Apply values to target tower
    #     target_tower = self.env['project.tower'].browse(target)

    #     for target_flat in target_tower.tower_flat_line_id:
    #         matching_flat = next((f for f in source_data if f['flat_name'] == target_flat.name), None)
    #         if matching_flat:
    #             for target_activity in target_flat.activity_ids:
    #                 matching_activity = next((a for a in matching_flat['activities'] if a['act_name'] == target_activity.name), None)
    #                 if matching_activity:
    #                     # Update activity-level fields
    #                     target_activity.act_rating = matching_activity['act_rating']
    #                     target_activity.progress_percentage = matching_activity['progress_percentage']
                        
    #                     for target_checklist in target_activity.activity_type_ids:
    #                         matching_checklist = next(
    #                             (c for c in matching_activity['checklists'] if c['chcklist_name'] == target_checklist.name), None
    #                         )
    #                         if matching_checklist:
    #                             target_checklist.status = matching_checklist['chcklist_status']
    #                             target_checklist.act_type_rating = matching_checklist['act_type_rating']
    #                             target_checklist.progress_percentage = matching_checklist['progress_percentage']

    #     # _logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++=")
        # _logger.info("--target_datatarget_datatarget_data--: %s",(target_data))

    def delete_ff(self):
        self.env['project.activity.type'].search([('tower_id','=',352)])

        # vjd_inventory_obj = self.env['vjd.inventory']
        # flats_recs = vjd_inventory_obj.search([
        #     ('hirerchyParent', '=', 479),
        #     ('buid', '=', 55),
        #     #('unitSubType', '=', 'Flat'),
        #     ('unitTypeId', '!=', False),
        #     #('state', '=', 'draft'),
        # ],order='unitNo asc')

        # sorted_flats_recs = sorted(flats_recs, key=lambda rec: int(rec.floorId), reverse=False)
        # #sorted_flats_recs = sorted(flats_recs, key=lambda rec: self.extract_floor_number(rec.floorDesc))

        # for rec in sorted_flats_recs:
        #     _logger.info("---rec.unitNorec.unitNo---: %s",(rec.unitNo))

        # # Step 1: Search records
        # floors_recs = vjd_inventory_obj.search([
        #     ('hirerchyParent', '=', 479),
        #     ('buid', '=', 55),
        #     ('floorDesc', '!=', False), 
        #     ('floorId', '!=', False),
        # ], order='id asc')
        # _logger.info("-----------floors_recs count---: %s", len(floors_recs))
        # # Step 2: Sort by extracted floor number
        # sorted_floors_recs = sorted(floors_recs, key=lambda rec: self.extract_floor_number(rec.floorDesc))

        # # Step 3: Track and log unique floorDesc values
        # seen_floor_descs = set()
        # for rec in sorted_floors_recs:
        #     if rec.floorDesc not in seen_floor_descs:
        #         _logger.info("----Unique FloorDesc---: %s", rec.floorDesc)
        #         seen_floor_descs.add(rec.floorDesc)
        return

        """Export project 21 activities, marking State = approved only when *all*
        related activity_type_ids are approved."""
        export_dir = Path('/opt/odoo16/odoo-custom-addons/vjd')
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_path = export_dir / f'project_data_{timestamp}.xlsx'

        workbook = xlsxwriter.Workbook(str(file_path))
        project = self.env['project.info'].browse(21)
        used_names = {}

        for tower_line in project.project_info_tower_line_temp:
            sheet_base = (tower_line.tower_id.name or "Unnamed Tower")[:31]
            idx = used_names.get(sheet_base.lower(), 0) + 1
            used_names[sheet_base.lower()] = idx
            sheet_name = f"{sheet_base[:28]}_{idx}" if idx > 1 else sheet_base

            ws = workbook.add_worksheet(sheet_name)
            ws.write_row(0, 0, ['Name (Flat/Floor)', 'Activity Name', 'State'])
            row = 1

            # For tower floor line activities
            for loc in tower_line.tower_id.tower_floor_line_id:
                for act in loc.activity_ids:
                    is_fully_approved = (
                        act.activity_type_ids
                        and all(t.status == "approve" for t in act.activity_type_ids)
                    )
                    state = "approve" if is_fully_approved else "draft"
                    ws.write_row(row, 0, [loc.name, act.name, state])
                    row += 1

            # For tower flat line activities
            for loc in tower_line.tower_id.tower_flat_line_id:
                for act in loc.activity_ids:
                    # for t in act.activity_type_ids:
                    #     _logger.info("---t.status-. (%s)", t.status)

                    is_fully_approved = (
                        act.activity_type_ids
                        and all(t.status == "approve" for t in act.activity_type_ids)
                    )
                    state = "approve" if is_fully_approved else "draft"
                    _logger.info("---t.status-. (%s)(%s)(%s)",loc.name,act.name,state)

                    ws.write_row(row, 0, [loc.name, act.name, state])
                    row += 1

        workbook.close()
        return file_path


    # def delete_ff(self):
    #     """Export activities for project 14 to a timestamped Excel file."""
    #     export_dir = Path('/opt/odoo16/odoo-custom-addons/vjd')
    #     export_dir.mkdir(parents=True, exist_ok=True)

    #     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    #     file_path = export_dir / f'project_data_{timestamp}.xlsx'

    #     workbook = xlsxwriter.Workbook(str(file_path))
    #     project = self.env['project.info'].browse(21)
    #     used_names = {}

    #     for tower_line in project.project_info_tower_line_temp:
    #         sheet_base = (tower_line.tower_id.name or "Unnamed Tower")[:31]
    #         index = used_names.get(sheet_base.lower(), 0) + 1
    #         used_names[sheet_base.lower()] = index
    #         sheet_name = f"{sheet_base[:28]}_{index}" if index > 1 else sheet_base

    #         ws = workbook.add_worksheet(sheet_name)
    #         ws.write_row(0, 0, ['Name (Flat/Floor)', 'Activity Name', 'State'])
    #         row = 1
    #         for loc in tower_line.tower_id.tower_floor_line_id:
    #             for act in loc.activity_ids:
    #                 ws.write_row(row, 0, [loc.name, act.name, act.state])
    #                 row += 1

    #         for loc in tower_line.tower_id.tower_flat_line_id:
    #             for act in loc.activity_ids:
    #                 ws.write_row(row, 0, [loc.name, act.name, act.state])
    #                 row += 1


    #     workbook.close()
    #     return file_path

        #self.env['project.floors'].search([('vj_floor_id','>',0)],limit=150).unlink()
        #self.env['project.flats'].search([('vj_floor_id','>',0)],limit=150).unlink()
        # records = self.env['vjd.inventory'].search([('floorId','>',0),('unitSubType','=','Flat')])
        # _logger.info("---records--. (%s)", records)
        
        # for record in records:
        #     existing_ids = record.flat_activity_group_ids.ids  # Get current IDs
        #     new_ids = list(set(existing_ids + [24]))  # Avoid duplicates
        #     record.write({'flat_activity_group_ids': [(6, 0, new_ids)]})

    #0  Code to create construction activity group records
    def set_inv_records_To_draft(self):
        records = self.env['vjd.inventory'].search([])
        records.state = 'draft'
        # a = vj_inv_obj = self.env['vjd.inventory'].search([])
        # a.write({
        #     'flat_activity_group_ids': [(5, 0, 0)],  # Clears all records from the many2many field
        #     'floor_activity_group_ids': [(5, 0, 0)]  # Clears all records from the many2many field
        # })
        
        # return
        return

    #1  Code to create construction activity group records
    def create_construction_activity_group(self): 
        activity_master_obj = self.env['activity.master']
        construction_act_grp_obj = self.env['construction.activity.group']
        records = activity_master_obj.search([])  # Fetch all records
        names = records.mapped('constructionActivityGroup')  # Extract names
        name_counts = Counter(names)  # Count occurrences
        duplicate_names = [name for name, count in name_counts.items() if count >= 1]  # Extract only duplicate names
        
        for key in duplicate_names:
            try:
                rec = activity_master_obj.search([('constructionActivityGroup','=',key)],limit=1)
                const_act_grp_rec = construction_act_grp_obj.search([('name','=',key)])
                if not const_act_grp_rec:
                    construction_act_grp_obj.create({'name':key,'activity_group_id':rec.constructionActivityGroupID})
                else:
                    const_act_grp_rec.write({'activity_group_id':rec.constructionActivityGroupID})

            except Exception as e:
                pass

    # #2 code to map construction activity group to construction activity group id from activity.master
    # def map_activity_group_to_id(self):
    #     activity_records = self.env['activity.master'].search([])
    #     for activity in activity_records:
    #         if activity.constructionActivityGroup:
    #             # Find the corresponding construction.activity.group record by name
    #             group = self.env['construction.activity.group'].search([
    #                 ('name', '=', activity.constructionActivityGroup)
    #             ], limit=1)
    #             if group:
    #                 # Update the construction_activity_group_id field
    #                 group.write({'activity_group_id': activity.constructionActivityGroupID})

    #3 Project Activity Name
    def map_activity_with_activity_group(self):
        #path = "/home/chetan/work/VJ/vj-test-env/vjd/api_data/activity_mapping.xlsx"
        prod_path = "/opt/odoo16/odoo-custom-addons/vjd/api_data/activity_mapping.xlsx"

        df = pd.read_excel(prod_path, engine='openpyxl', sheet_name='Quality App activity')
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        # Drop rows where all values are NaN
        df = df.dropna(how='all')
        # Select the 4th, 5th, and 7th columns (index starts from 0)
        selected_columns = df.iloc[:, [0,1]]  
        # Drop rows where any of the selected columns have NaN
        selected_columns = selected_columns.dropna(how='any')
        project_act_name_obj = self.env['project.activity.name']
        con_act_group = self.env['construction.activity.group']
        # Print the selected rows
        count = 0
        for index, row in selected_columns.iterrows():
            # if row[0] == 'FLOOR 10' and int(row[1]) == 252:
            #     count+=1
            #print(row[0], row[1], row[2])  # Access column values
            act_records = project_act_name_obj.search([('realname', '=', row[0])]) 
            groups = con_act_group.search([('name', '=', row[1])])  # Search for activity groups by name

            if groups:
                # Assuming 'groups' can have multiple records and you want to add them all
                for group in groups:
                    # Add each group.id to the many2many field of inventory records
                    act_records.write({'construction_activity_group_ids': [(4, group.id)]})  # Add group to Many2many field
                    
        #_logger.info("---selected_columns--count---. (%s)", count)
        return
    #4 Inventory mapping
    def map_floor_id_with_activity_group(self):
        #path = "/home/chetan/work/VJ/vj-test-env/vjd/api_data/activity_mapping.xlsx"
        path = "/opt/odoo16/odoo-custom-addons/vjd/api_data/activity_mapping.xlsx"
        # Load the Excel file
        df = pd.read_excel(path, engine='openpyxl', sheet_name='Mapped')
        # Strip any leading/trailing spaces for all string columns
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        # Drop rows where all values are NaN
        df = df.dropna(how='all')
        # Select the 4th, 5th, and 7th columns (index starts from 0)
        selected_columns = df.iloc[:, [3,4,5,6]]  
        # Drop rows where any of the selected columns have NaN
        selected_columns = selected_columns.dropna(how='any')
        vj_inv_obj = self.env['vjd.inventory']
        con_act_group = self.env['construction.activity.group']
        # Print the selected rows
        count = 0
        for index, row in selected_columns.iterrows():
            if row[2] == 'FLOOR WISE':
                #     count+=1
                #print(row[0], row[1], row[2])  # Access column values
                inv_records = vj_inv_obj.search([('floorDesc', '=', row[0]), ('floorId', '=', int(row[1]))]) 
                groups = con_act_group.search([('name', '=', row[3])])  # Search for activity groups by name

                if groups:
                    # Assuming 'groups' can have multiple records and you want to add them all
                    for group in groups:
                        # Add each group.id to the many2many field of inventory records
                        inv_records.write({'floor_activity_group_ids': [(4, group.id)]})  # Add group to Many2many field
                        #inv_records.write({'type':'floor_wise'})
            if row[2] == 'FLAT WISE':
                inv_records = vj_inv_obj.search([('floorDesc', '=', row[0]), ('floorId', '=', int(row[1]))]) 
                groups = con_act_group.search([('name', '=', row[3])])  # Search for activity groups by name

                if groups:
                    # Assuming 'groups' can have multiple records and you want to add them all
                    for group in groups:
                        # Add each group.id to the many2many field of inventory records
                        inv_records.write({'flat_activity_group_ids': [(4, group.id)]})  # Add group to Many2many field
                        #inv_records.write({'type':'flat_wise'})
        #_logger.info("---selected_columns--count---. (%s)", count)
        return

    #5 Set Manual group in the inventory
    def set_manual_group_in_the_inventory(self):
        
        group_ids = [48]
        vj_inv_obj = self.env['vjd.inventory']
        inv_records = vj_inv_obj.search([('unitSubType', '=', 'Flat')])
            
        inv_records.write({'flat_activity_group_ids': [(4, 48)]})

    #_-------------------------------------------------------------#######3
    # def map_floor_id_with_activity_group(self):
    #     path = "/home/chetan/Downloads/activity_mapping.xlsx"
    #     # Load the Excel file
    #     df = pd.read_excel(path, engine='openpyxl', sheet_name='Mapped')
    #     # Strip any leading/trailing spaces for all string columns
    #     df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    #     # Drop rows where all values are NaN
    #     df = df.dropna(how='all')
    #     # Select the 4th, 5th, and 7th columns (index starts from 0)
    #     selected_columns = df.iloc[:, [3, 4, 6]]  
    #     # Drop rows where any of the selected columns have NaN
    #     selected_columns = selected_columns.dropna(how='any')
    #     vj_inv_obj = self.env['vjd.inventory']
    #     con_act_group = self.env['construction.activity.group']
    #     # Print the selected rows
    #     for index, row in selected_columns.iterrows():
    #         print(row[0], row[1], row[2])  # Access column values
    #         inv_records = vj_inv_obj.search([('floorDesc', '=', row[0]), ('floorId', '=', int(row[1]))]) 
    #         group = con_act_group.search([('name', '=', row[2])])
    #         if group:
    #             inv_records.write({'activity_group_id': group.id})
    #         _logger.info("---selected_columns-----. (%s,%s,%s)", row[0], int(row[1]), row[2])

    #     return

