# -*- coding: utf-8 -*-
# from distutils.command.check import check
# from setuptools import setup
# from setuptools.command.check import check

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
import base64
import re
import requests
import json
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

class FlatSiteVisit(models.Model):
    _name = 'flat.site.visit'
    _description = "Flat Site Visit"

    name = fields.Char("Name")
    sequence = fields.Integer("Sequence")
    flat_id = fields.Many2one("project.flats","Flat")
    tower_id = fields.Many2one("project.tower","Tower")
    project_id = fields.Many2one("project.info","Project")
    sv_location_ids = fields.One2many("site.visit.locations","flat_site_visit_id","Locations")
    color = fields.Selection([
        ('orange', 'Orange'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
    ],default='', string="Color")
    is_pdf_downloaded = fields.Boolean(string="PDF Downloaded", default=False)

    total_observation_count = fields.Integer(string="Raised",compute="_compute_total_observation_count",store=True)
    pending_observation_count = fields.Integer(string="Pending",compute="_compute_pending_observation_count",store=True)
    completed_observation_count = fields.Integer(string="Completed",compute="_compute_completed_observation_count",store=True)

    checker_completed_count = fields.Integer(
        string="Checker Completed",
        compute="_compute_flat_level_observation_counts",
        store=True
    )

    checker_pending_count = fields.Integer(
        string="Checker Pending",
        compute="_compute_flat_level_observation_counts",
        store=True
    )

    maker_completed_count = fields.Integer(
        string="Maker Completed",
        compute="_compute_flat_level_observation_counts",
        store=True
    )

    maker_pending_count = fields.Integer(
        string="Maker Pending",
        compute="_compute_flat_level_observation_counts",
        store=True
    )


    @api.depends(
    'sv_location_ids.checker_completed_count',
    'sv_location_ids.checker_pending_count',
    'sv_location_ids.maker_completed_count',
    'sv_location_ids.maker_pending_count',
    )
    def _compute_flat_level_observation_counts(self):
        for rec in self:
            rec.total_observation_count = sum(rec.sv_location_ids.mapped('observation_count'))
            rec.pending_observation_count = sum(rec.sv_location_ids.mapped('pending_observation_count'))
            rec.completed_observation_count = sum(rec.sv_location_ids.mapped('completed_observation_count'))

            rec.checker_completed_count = sum(rec.sv_location_ids.mapped('checker_completed_count'))
            rec.checker_pending_count = sum(rec.sv_location_ids.mapped('checker_pending_count'))
            rec.maker_completed_count = sum(rec.sv_location_ids.mapped('maker_completed_count'))
            rec.maker_pending_count = sum(rec.sv_location_ids.mapped('maker_pending_count'))


    @api.depends('sv_location_ids.observation_count')
    def _compute_total_observation_count(self):
        for visit in self:
            visit.total_observation_count = sum(loc.observation_count for loc in visit.sv_location_ids)

    @api.depends('sv_location_ids.pending_observation_count')
    def _compute_pending_observation_count(self):
        for visit in self:
            visit.pending_observation_count = sum(loc.pending_observation_count for loc in visit.sv_location_ids)
    
    @api.depends('sv_location_ids.completed_observation_count')
    def _compute_completed_observation_count(self):
        for visit in self:
            visit.completed_observation_count = sum(loc.completed_observation_count for loc in visit.sv_location_ids)

    @api.onchange('flat_id')
    def _onchange_flat_id(self):
        if self.flat_id:
            self.tower_id = self.flat_id.tower_id.id
            self.project_id = self.flat_id.project_id.id
    
    @api.model
    def create_first_site_visit(self,flat_id = False):
        #_logger.info(f"----------flat_id-----------: {flat_id}")
        if flat_id:
            flat_rec = self.env['project.flats'].browse(flat_id)
            #_logger.info(f"--------flat_rec-------------: {flat_rec}")
            if not flat_rec.flat_site_visit_ids:

                unit_locations_rec = self.env['unit.locations'].search([('unit_type', '=',flat_rec.unit_type)], order='sequence asc')
                _logger.info("--value------unit_locations_rec----------,%s",unit_locations_rec)
                
                if not unit_locations_rec:
                    return 300
                location_vals = [(0, 0, {'name': rec.name, 'unit_type': rec.unit_type,'unit_location_id':rec.id,'flat_id':flat_id}) for rec in unit_locations_rec]

                visit_rec = self.env['flat.site.visit'].create({
                    'name': 'Site Visit 1',
                    'sequence': 1,
                    'flat_id': flat_rec.id,
                    'tower_id': flat_rec.tower_id.id or False,
                    'project_id': flat_rec.project_id.id or False,
                })
                #_logger.info(f"---------visit_rec----------: {visit_rec}")
                # Write to the One2many field on the visit record
                visit_rec.write({
                    'sv_location_ids': location_vals
                })
                return True
            return 100
        
    def get_site_visit_pdf(self, visit_id):
        record = self.sudo().browse(visit_id)
        if not record.exists():
            return False

        try:
            report = self.env.ref('custom_project_management.action_report_hqi').sudo()
        except Exception:
            _logger.exception("Failed to load report via env.ref")
            return False

        try:
            pdf_content, _ = report.sudo()._render_qweb_pdf([record.id])
            pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")

            # Create HQI Email record and store PDF inside
            email_rec = self.env['hqi.email'].create({
                'email_to': record.partner_id.email,
                'project': record.project_id.name,
                'building': record.building_id.name,
                'flat': record.flat_id.name,
                'project_incharge_id': record.project_incharge_id.id,
                'state': 'draft',
                'pdf_report': pdf_base64,   # <-- store PDF here
            })

            _logger.info("PDF stored in hqi.email ID %s", email_rec.id)

        except Exception:
            _logger.exception("Failed to render QWeb PDF")
            return False

        return pdf_base64
        


    # Site Visit PDF Generation
    # def get_site_visit_pdf(self, visit_id):

    #     # Ensure correct user context
    #     record = self.sudo().browse(visit_id)
    #     if not record.exists():
    #         #_logger.error("Site visit record not found.")
    #         return False
    #     #_logger.info("---------visit_rec----------")
    #     try:
    #         # DO NOT pass list — pass a single XML ID string
    #         report = self.env.ref('custom_project_management.action_report_hqi').sudo()
    #         #_logger.info(f"--------report-------: {report.name} (ID: {report.id})")
    #     except Exception as e:
    #         _logger.exception("Failed to load report via env.ref")
    #         return False
    
    #     try:
    #         # Pass list of record IDs to render
    #         pdf_content, _ = report.sudo()._render_qweb_pdf(report,[record.id])
    #         color_map = {
    #         1: 'orange',
    #         2: 'yellow',
    #         3: 'green',
    #         }
    #         record.color = color_map.get(record.sequence)
    #         if not record.is_pdf_downloaded:
    #             record.is_pdf_downloaded = True
    #             self.env['hqi.email'].create({
    #                 'email_to': record.partner_id.email,
    #                 #'attachment_ids': [(6, 0, [pdf_content.id])],
    #                 'project': record.project_id.name,
    #                 'building': record.building_id.name,
    #                 'flat': record.flat_id.name,
    #                 'project_incharge_id': record.project_incharge_id.id,
    #                 'state':'draft',
    #             })
    #         #_logger.info("-------pdf_content rendered successfully---")
    #     except Exception as e:
    #         _logger.exception("Failed to render QWeb PDF")
    #         return False

    #     pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    #     #_logger.info(f"--------report-------:(ID: {pdf_base64})")
    #     return pdf_base64

    def action_generate_report_pdf(self):
        # # # Recompute for Site Visit Locations
        # self.env['site.visit.locations'].search([])._compute_checker_maker_counts()
        # self.env['site.visit.locations'].search([])._compute_observation_count()
        # self.env['site.visit.locations'].search([])._compute_pending_observation_count()
        # self.env['site.visit.locations'].search([])._compute_completed_observation_count()
        # # Recompute for Flat Site Visit
        # self.env['flat.site.visit'].search([])._compute_flat_level_observation_counts()
        # self.env['flat.site.visit'].search([])._compute_total_observation_count()
        # self.env['flat.site.visit'].search([])._compute_completed_observation_count()
        # self.env['flat.site.visit'].search([])._compute_pending_observation_count()

        return self.env.ref('custom_project_management.action_report_hqi').report_action(self)

class SiteVisitLocations(models.Model):
    _name = 'site.visit.locations'
    _description = "Site Visit Location(s)"

    flat_site_visit_id = fields.Many2one('flat.site.visit','Flat Site Visit ID')
    flat_id = fields.Many2one('project.flats','Flat ID')
    name = fields.Char('Name')
    observation_count = fields.Integer(string="Raised",compute="_compute_observation_count",store=True)
    pending_observation_count = fields.Integer(string="Pending",compute="_compute_pending_observation_count",store=True)
    completed_observation_count = fields.Integer(string="Completed",compute="_compute_completed_observation_count",store=True)
    checker_completed_count = fields.Integer(string="Checker Completed",compute="_compute_checker_maker_counts",store=True)

    checker_pending_count = fields.Integer(
        string="Checker Pending",
        compute="_compute_checker_maker_counts",
        store=True
    )

    maker_completed_count = fields.Integer(
        string="Maker Completed",
        compute="_compute_checker_maker_counts",
        store=True
    )

    maker_pending_count = fields.Integer(
        string="Maker Pending",
        compute="_compute_checker_maker_counts",
        store=True
    )

    color = fields.Selection([
        ('red', 'Red'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
    ],default='', string="Color")
    unit_location_id = fields.Many2one('unit.locations','Unit Location')
    unit_type = fields.Selection([('one_bhk', '1 BHK'),('two_bhk', '2 BHK'), ('three_bhk', '3 BHK'),('three_bhkxl', '3 BHK XL'),('duplex', 'Duplex'),('shop', 'Shop'),('simplex', 'Simplex')], string="Unit Type")
    svb_location_ids = fields.One2many("site.visit.location.observation","site_visit_location_id","Observation")
    
    
    @api.depends('svb_location_ids.is_original_observation')
    def _compute_observation_count(self):
        for rec in self:
            rec.observation_count = len(
                rec.svb_location_ids.filtered(lambda obs: obs.is_original_observation)
            )


    @api.depends('svb_location_ids.state')
    def _compute_checker_maker_counts(self):
        for rec in self:
            observations = rec.svb_location_ids.filtered(lambda obs: obs.is_original_observation)

            checker_completed = 0
            maker_completed = 0
            checker_pending = 0
            maker_pending = 0


            for obs in observations:
                # Checker Completed
                if obs.state in ('completed'):
                    checker_completed += 1
                    maker_completed += 1

                # Maker Completed
                if obs.state in ('re_review_by_checker'):
                    checker_pending += 1

                if obs.state in ('correction_by_maker'):
                    maker_pending += 1

            rec.checker_completed_count = checker_completed
            rec.checker_pending_count = checker_pending
            rec.maker_completed_count = maker_completed
            rec.maker_pending_count = maker_pending

    @api.depends('svb_location_ids.state')
    def _compute_pending_observation_count(self):
        for rec in self:
            rec.pending_observation_count = len(
                rec.svb_location_ids.filtered(
                    lambda obs: obs.is_original_observation and obs.state not in ('in_review_by_checker', 'completed')
                )
            )

    @api.depends('svb_location_ids.state')
    def _compute_completed_observation_count(self):
        for rec in self:
            rec.completed_observation_count = len(
                rec.svb_location_ids.filtered(lambda obs: obs.is_original_observation and obs.state == 'completed')
                )

    @api.model
    def get_flat_sv_location_observation(self, location_id):
        #_logger.info(f"---get_flat_sv_location_observation  sub---:")

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')

        rec = self.search([('id', '=', location_id)])
        #_logger.info(f"---rec----: {rec.id}")

        data = []
        color_list = []  # 🔶 Collect colors during the loop

        for observation in rec.svb_location_ids:
            color_list.append(observation.color)  # 🔶 Track colors on the fly

            img_list = []
            for line in observation.observation_image_ids:
                dl = {}

                if line.checker_uploaded_img:
                    dl['checker_img_url'] = (
                        f"{base_url}/web/image?model=observation.images"
                        f"&field=checker_uploaded_img&id={line.id}"
                    )

                if line.user_checker:
                    dl['user_checker'] = line.user_checker.id

                if line.maker_uploaded_img:
                    dl['maker_img_url'] = (
                        f"{base_url}/web/image?model=observation.images"
                        f"&field=maker_uploaded_img&id={line.id}"
                    )

                if line.user_maker:
                    dl['user_maker'] = line.user_maker.id

                img_list.append(dl)

            visit_dict = {}
            if observation.site_visit_location_id and observation.site_visit_location_id.flat_site_visit_id:
                visit_dict = {
                    'visit_name': observation.site_visit_location_id.flat_site_visit_id.name,
                    'sequence': observation.site_visit_location_id.flat_site_visit_id.sequence,
                    'visit_id': observation.site_visit_location_id.flat_site_visit_id.id
                }

            obs = {
                'visit_details': visit_dict,
                'img_data': img_list,
                'observation_id': observation.id,
                'name': observation.name,
                'state': observation.state,
                'date': observation.date.isoformat() if observation.date else '',
                'target_date': observation.target_date.isoformat() if observation.target_date else '',
                'issue_category_id': observation.issue_category_id.id if observation.issue_category_id else False,
                'issue_category_name': observation.issue_category_id.name if observation.issue_category_id else False,
                'issue_type_id': observation.issue_type_id.id if observation.issue_type_id else False,
                'issue_type_name': observation.issue_type_id.name if observation.issue_type_id else False,
                'description': observation.description or '',
                'remark': observation.remark or '',
                'impact': observation.impact or '',
                'location_id': location_id,
                'checker_submitted': observation.checker_submitted,
                'maker_submitted': observation.maker_submitted,
                'color': observation.color,
            }
            data.append(obs)

        # 🔶 Compute overall color after loop
        if color_list:
            if all(c == 'red' for c in color_list):
                location_color = 'red'
            elif all(c == 'green' for c in color_list):
                location_color = 'green'
            else:
                location_color = 'yellow'
        else:
            location_color = False

        # 🔶 Add overall color to every observation dict
        for obs in data:
            obs['location_overall_color'] = location_color
            rec.color = location_color
        return data

class SiteVisitLocationObservation(models.Model):
    _name = 'site.visit.location.observation'
    _description = "Site Visit Location Observation"

    observation_id = fields.Many2one('site.visit.location.observation','Observation',readonly=1)
    site_visit_location_id = fields.Many2one('site.visit.locations','Site Visit Location Id',readonly=1)
    name = fields.Char('Name',readonly=1)
    sequence = fields.Char('Sequence',readonly=1)

    date = fields.Date("Date",readonly=1)
    target_date = fields.Date("Target Date",readonly=1)
    issue_category_id = fields.Many2one('issue.category','Issue Category',readonly=1)
    issue_type_id = fields.Many2one('issue.type','Issue Type',readonly=1)
    description = fields.Char('Description',readonly=1)
    remark = fields.Char('Remark',readonly=1)
    state = fields.Selection([
    ('in_review_by_checker', 'In Review by Checker'),  # Checker reviewing first time
    ('correction_by_maker', 'Correction by Maker'),    # Maker correcting
    ('re_review_by_checker', 'Re-review by Checker'),  # Checker re-checking after correction
    ('completed', 'Completed'),                        # Finalized
    ], default='in_review_by_checker', tracking=True, string="State")

    impact = fields.Selection([('low', 'Low'), ('medium', 'Medium'),('high', 'High')], string="Impact",readonly=1)
    user_checker = fields.Many2one('res.users','Checker',readonly=1)
    user_maker = fields.Many2one('res.users','Maker',readonly=1)
    observation_image_ids = fields.One2many('observation.images','svl_observation_id','Observation Images')
    checker_submitted = fields.Boolean('Checker Submitted',readonly=1)
    maker_submitted = fields.Boolean('Maker Submitted',readonly=1)
    checker_count = fields.Integer('Checker Count',readonly=1)
    maker_count = fields.Integer('Maker Count',readonly=1)

    color = fields.Selection([
        ('red', 'Red'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
    ],default='yellow', string="Color")
    is_original_observation = fields.Boolean(
    string="Is Original Observation",
    default=False,
    help="Indicates whether this is the original observation created by the Checker in Site Visit 1."
    )
    

    @api.model
    def get_hqi_observation_history(self, observation_id):
        rec = self.browse(observation_id)

        issue_category_name = rec.issue_category_id.name or ''
        issue_type_name = rec.issue_type_id.name or ''

        checker_name = rec.user_checker.name if rec.user_checker else False
        maker_name = rec.user_maker.name if rec.user_maker else False
        #last_update_date = rec._last_update

        data = {
            'issue_category_name': issue_category_name,
            'issue_type_name': issue_type_name,
            'checker_name': checker_name,
            'maker_name': maker_name,
            'last_update': '',
        }

        return data
    
    @api.model
    def replicate_hqi_observation_history(self, observation_id,user_id):
        observation_rec = self.browse(observation_id)

        # Duplicate base observation (excluding One2manys)
        new_observation = self.sudo().create({
            'observation_id': observation_rec.id,
            'site_visit_location_id': observation_rec.site_visit_location_id.id,
            'name': observation_rec.name,
            'sequence': observation_rec.sequence,
            #'date': observation_rec.date,
            #'target_date': observation_rec.target_date,
            'issue_category_id': observation_rec.issue_category_id.id,
            'issue_type_id': observation_rec.issue_type_id.id,
            'description': observation_rec.description,
            'remark': observation_rec.remark or '',
            'state': 'correction_by_maker',  # Reset state
            'impact': observation_rec.impact or '',
            'user_checker': user_id,
            # 'user_maker': observation_rec.user_maker.id,
            'checker_submitted': True,
            'maker_submitted': False,
            'checker_count': 1,
            'maker_count': 0,
            'color': 'red',
            'is_original_observation': True,
        })
        return new_observation.id

    @api.model
    def flat_observation_return_to_maker_by_checker(self,params):
        #.info(f"----flat_site_visit--------: {flat_site_visit}")
        #_logger.info(f"----flat_observation_return_to_maker_by_checker---:(data: {params})")

        user_id = int(params.get('user_id'))

        first = False
        second = False

        if not params.get('observation_id'):
            first = True
            observation_id = self.create({
                'site_visit_location_id': int(params.get('location_id')),  # Replace with the actual ID
                'name': params.get('name'),
                'date': params.get('date'),
                'target_date': params.get('target_date'),
                'issue_category_id':int(params.get('issue_category_id')),
                'issue_type_id':int(params.get('issue_type_id')),
                'description':params.get('description'),
                'impact':params.get('impact'),
                'remark':params.get('remark'),
                'user_checker':user_id,
                'state':'correction_by_maker',# maker needs to correct this.
                'checker_submitted':True,
                'color':'red',
                'checker_count':1,
                'is_original_observation':True

                    })
            #observation_id.site_visit_location_id.color = 'red'
            observation_id.sequence = False
            location_id =  observation_id.site_visit_location_id
            if location_id:
                observation_id.sequence = f"{location_id.flat_id.project_id.name}/" \
                f"{location_id.flat_id.tower_id.name}/" \
                f"{location_id.flat_id.name}/" \
                f"{observation_id.site_visit_location_id.flat_site_visit_id.name}/" \
                
                f"{location_id.name}/" \
                f"{observation_id.issue_category_id.name}"
            
            if params.get('checker_uploaded_img'):
                images = params.get('checker_uploaded_img')
                data = []
                for img in images:
                    temp = {'svl_observation_id': observation_id.id,
                            'checker_uploaded_img': img, 'user_checker':user_id}
                    data.append(temp)
                if data:
                    self.env['observation.images'].create(data)
        else:
            second = True
            observation_id = params.get('observation_id')
            if observation_id:
                rec = self.browse(int(observation_id))
                observation_id = rec
                if rec.exists():
                    rec.write({
                        'state': 'correction_by_maker',
                        'color': 'red',
                        'description': str(params.get('description')),
                        'checker_count':1,
                        'checker_submitted':True,
                        'maker_submitted':False,
                        'impact': str(params.get('impact')),
                        'user_checker':user_id,
                        'checker_count':1,
                    })

                    def mark_correction_by_maker_recursively(observation):
                        if not observation:
                            return
                        # Update the current observation
                        observation.state = 'correction_by_maker'
                        observation.color = 'red'  # You had a typo: 'gren'
                        #observation.site_visit_location_id.color = 'red'

                        # Recursively update its child observation
                        if observation.observation_id:
                            mark_correction_by_maker_recursively(observation.observation_id)
                    mark_correction_by_maker_recursively(rec)

            if params.get('checker_uploaded_img'):
                images = params.get('checker_uploaded_img')
                data = []
                count = 1
                for img in images:
                    #_logger.info(f"----Checker Sending to Checker---1st-----: {count}")
                    count+=1

                    temp = {'svl_observation_id': rec.id,
                            'checker_uploaded_img': img, 'user_checker': user_id}
                    data.append(temp)
                if data:
                    self.env['observation.images'].create(data)
        if observation_id:
            user_value = 'maker'
            observation_id.send_hqi_notification(user_id,user_value,{'first':first,'second':second})

    @api.model
    def flat_observation_resubmit_to_checker(self, params):
        #_logger.info(f"---flat_observation_resubmit_to_checker----called-----:")

        fsv_obj = self.env['flat.site.visit']
        observation_id = params.get('observation_id')
        user_id = int(params.get('user_id'))
        obs_rec = self.browse(int(observation_id))
        obs_rec.maker_submitted = True
        # Get current visit details
        current_visit = obs_rec.site_visit_location_id.flat_site_visit_id
        next_sequence = current_visit.sequence + 1
        # Search for next site visit
        domain = [
            ('sequence', '=', next_sequence),
            ('project_id', '=', current_visit.project_id.id),
            ('tower_id', '=', current_visit.tower_id.id),
            ('flat_id', '=', current_visit.flat_id.id),
        ]
        flat_site_visit = fsv_obj.search(domain, limit=1)
        #.info(f"----flat_site_visit--------: {flat_site_visit}")
        if not flat_site_visit:
            flat_site_visit = fsv_obj.create({
                'name': f'Site Visit {next_sequence}',
                'sequence': next_sequence,
                'flat_id': current_visit.flat_id.id,
                'tower_id': current_visit.tower_id.id,
                'project_id': current_visit.project_id.id,
            })

        unit_location = obs_rec.site_visit_location_id.unit_location_id

        svl_record = self.env['site.visit.locations'].search([('flat_site_visit_id','=',flat_site_visit.id),('name','=',unit_location.name),('unit_type','=',unit_location.unit_type),('unit_location_id','=',unit_location.id),('flat_id','=',flat_site_visit.flat_id.id)])

        if not svl_record:
            ###  123
            # 1. Capture existing location IDs before write
            existing_ids = flat_site_visit.sv_location_ids.ids

            # 2. Prepare the new location values
            location_vals = [(0, 0, {
                'name': unit_location.name,
                'unit_type': unit_location.unit_type,
                'unit_location_id': unit_location.id,
                'flat_id': flat_site_visit.flat_id.id,
            })]

            # 3. Write the new location
            flat_site_visit.write({'sv_location_ids': location_vals})

            # 4. Find the new location by comparing IDs
            new_ids = flat_site_visit.sv_location_ids.ids
            created_ids = list(set(new_ids) - set(existing_ids))

            # 5. Get the new location record(s)
            new_locations = flat_site_visit.sv_location_ids.filtered(lambda l: l.id in created_ids)

            # If only one added, get its ID
            new_location_id = new_locations[0] if new_locations else None
            location_id = new_location_id
            # flat_site_visit.write({'sv_location_ids': location_vals})

        else:
            location_id = svl_record
        sequence = False
        # Create new observation under the next visit
        flat_rec = obs_rec.site_visit_location_id.flat_id
        if flat_rec:
            sequence = f"{flat_rec.project_id.name}/" \
                f"{flat_rec.tower_id.name}/" \
                f"{flat_rec.name}/" \
                f"{flat_site_visit.name}/" \
                f"{obs_rec.site_visit_location_id.name}/" \
                f"{obs_rec.issue_category_id.name}"

        observation_rec = self.create({
            'site_visit_location_id': location_id.id,
            'name': location_id.name,
            'date': datetime.today().strftime('%Y-%m-%d'),
            'target_date':obs_rec.target_date,
            'issue_category_id': obs_rec.issue_category_id.id,
            'issue_type_id': obs_rec.issue_type_id.id,
            'description': params.get('description'),
            'remark': params.get('remark'),
            'impact': obs_rec.impact,
            'user_maker': user_id,
            'state': 're_review_by_checker',
            'color':'yellow',
            'observation_id': obs_rec.id,
            'maker_submitted':True,
            'checker_submitted':False,
            'maker_count':1,
            'sequence':sequence ,
        })
        obs_rec.maker_count = 1
        obs_rec.maker_submitted = True

        data = []
        data2 = []
   
        for image_line in obs_rec.observation_image_ids:
            #_logger.info(f"---checker--IAMGE FOUND----------:{observation_rec.id}")
            #_logger.info(f"----Maker Sending to Checker---from old-----: {count}")
           
            if image_line.checker_uploaded_img:
                temp = {'svl_observation_id': observation_rec.id,
                        'checker_uploaded_img': image_line.checker_uploaded_img, 'user_checker': image_line.user_checker.id}
            if image_line.maker_uploaded_img:
                temp = {'svl_observation_id': observation_rec.id,
                        'maker_uploaded_img': image_line.maker_uploaded_img, 'user_maker': image_line.user_maker.id}

            data.append(temp)
        
        if params.get('maker_uploaded_img'):
            images = params.get('maker_uploaded_img')  # should be a list of base64 strings

            for img in images:
                if img.startswith('data:image'):
                    # Strip header if present (data:image/png;base64,...)
                    img_base64 = re.sub('^data:image/.+;base64,', '', img)
                else:
                    img_base64 = img

                try:
                    # Validate base64
                    base64.b64decode(img_base64)
                except Exception as e:
                    _logger.error(f"Invalid base64 image data: {e}")
                    continue

                temp = {
                    'svl_observation_id': observation_rec.id,
                    'maker_uploaded_img': img_base64,
                    'user_maker': user_id
                }

                temp2 = {
                    'svl_observation_id': obs_rec.id,
                    'maker_uploaded_img': img_base64,
                    'user_maker': user_id
                }
                data2.append(temp2)
                data.append(temp)
        #_logger.info(f"----length data---: {len(data)}")

        if data:
            self.env['observation.images'].create(data)
        if data2:
            self.env['observation.images'].create(data2)
        #_logger.info(f"---flat_observation_resubmit_to_checker----End-----:")

        def mark_re_review_by_checker_recursively(observation):
            if not observation:
                return
            # Update the current observation
            observation.state = 're_review_by_checker'
            observation.color = 'yellow'  # You had a typo: 'gren'
            #observation_rec.site_visit_location_id.color = 'yellow'

            # Recursively update its child observation
            if observation.observation_id:
                mark_re_review_by_checker_recursively(observation.observation_id)
        mark_re_review_by_checker_recursively(observation_rec)
        user_value = 'checker_approver'

        try:

            if self.site_visit_location_id:
                all_re_review = all(
                    obs.state == 're_review_by_checker' 
                    for obs in self.site_visit_location_id.svb_location_ids
                )
                if all_re_review:
                    flat_obj = self.site_visit_location_id.flat_id
                    self.env['hqi.whatsapp.log'].create({
                        'to_user': self.user_checker.id,
                        'from_user': self.user_maker.id,
                        'project': flat_obj.project_id.name or False,
                        'tower': flat_obj.tower_id.name or False,
                        'unit': self.site_visit_location_id.flat_id.name or False,
                        'state':'draft',
                    })
        except Exception as e:
            _logger.error(f"Error creating WhatsApp log: {e}")
            self.env['hqi.whatsapp.log'].create({
                        'error': str(e),
                        'state':'failed',
                    })

        obs_rec.send_hqi_notification(user_id,user_value,{'third':True})
        
    @api.model
    def flat_observation_completed(self, params):
        obs_id = int(params.get('observation_id'))
        user_id = int(params.get('user_id'))

        ####
        data = []
        if params.get('checker_uploaded_img'):
            count = 1
            images = params.get('checker_uploaded_img')  # should be a list of base64 strings

            for img in images:
                if img.startswith('data:image'):
                    # Strip header if present (data:image/png;base64,...)
                    img_base64 = re.sub('^data:image/.+;base64,', '', img)
                else:
                    img_base64 = img
                try:
                    # Validate base64
                    base64.b64decode(img_base64)
                except Exception as e:
                    _logger.error(f"Invalid base64 image data: {e}")
                    continue

                temp = {
                    'svl_observation_id': obs_id,
                    'checker_uploaded_img': img_base64,
                    'user_checker': user_id
                }
                data.append(temp)
        if data:
            self.env['observation.images'].create(data)
        ###
        def mark_completed_recursively(observation):
            if not observation:
                return

            # Update the current observation
            observation.state = 'completed'
            observation.color = 'green'
            observation.checker_submitted = True
            observation.maker_submitted = True
            observation.checker_count = 1
            observation.maker_count = 1

            # Recursively update its child observation
            if observation.observation_id:
                mark_completed_recursively(observation.observation_id)
        observation = self.browse(obs_id)
        observation.user_checker = user_id
        observation.checker_count = 1
        observation.maker_count = 1
        mark_completed_recursively(observation)

    def _log_error(self,NotificationLog, base_log, user, player_id, message, error):
        log_data = base_log.copy()
        log_data.update({
            'player_id': player_id,
            'message': message,
            'user': user.name,
            'error': error,
        })
        NotificationLog.create({'title': log_data, 'status': 'failed'})

    def send_hqi_notification(self, user_id, user_value,value):

        Notification = self.env['app.notification']
        NotificationLog = self.env['app.notification.log']

        failed_log = {
            'user_id': user_id,
            'method': '',
        }

        if not user_id:
            failed_log['error'] = 'No user_id provided'
            NotificationLog.create({'title': failed_log, 'status': 'failed'})
            return False

        user_record = self.env['res.users'].browse(user_id)
        hqi_user_ids = self.site_visit_location_id.flat_site_visit_id.tower_id.hqi_user_ids

        if not hqi_user_ids:
            failed_log['ids_not_found'] = 'HQI User Ids Not Found'
            NotificationLog.create({'title': failed_log, 'status': 'failed'})
            return False

        # Role-based group names
        target_groups = {
            'maker': ['maker hqi'],
            'checker_approver': ['checker hqi', 'approver hqi'],
        }.get(user_value, [])

        if not target_groups:
            failed_log['error'] = f'Invalid user_value: {user_value}'
            NotificationLog.create({'title': failed_log, 'status': 'failed'})
            return False

        sent = False
        if value.get('first'):
            message = f"{self.sequence or 'N/A'} Submitted by {user_record.name or 'Unknown User'}"
            title = f"{user_record.name} Created the Observation"
        elif value.get('second'):
            message = f"{self.sequence or 'N/A'} Submitted by {user_record.name or 'Unknown User'}"
            title = f"{user_record.name} ReSubmitted the Observation"
        elif value.get('third'):
            message = f"{self.sequence or 'N/A'} Submitted by {user_record.name or 'Unknown User'}"
            title = f"{user_record.name} Submitted the Observation"
        else:
            pass
       
        for user in hqi_user_ids:
            user_group_names = {g.name.lower() for g in user.groups_id}
            if any(role in user_group_names for role in target_groups):
                player_id, _ = self.env['res.users'].get_player_id(user.id)
                if player_id:
                    try:
                        Notification.hqi_send_push_notification(
                            title, [player_id], message, [user.id], 'hqi', self
                        )
                        sent = True
                    except Exception as e:
                        self._log_error(NotificationLog, failed_log, user, player_id, message, str(e))
                else:
                    self._log_error(NotificationLog, failed_log, user, player_id, message, "Missing player_id")

        if not sent:
            failed_log['group_name'] = 'Target group not found or no notifications sent'
            NotificationLog.create({'title': failed_log, 'status': 'failed'})

        return True

class ObservationImages(models.Model):
    _name = 'observation.images'
    _description = "Observation Images"

    svl_observation_id = fields.Many2one('site.visit.location.observation','Observation')
    user_checker = fields.Many2one('res.users','Checker')
    user_maker = fields.Many2one('res.users','Maker')
    checker_uploaded_img = fields.Binary('Checker Image',attachment=True)
    maker_uploaded_img = fields.Binary('Maker Image',attachment=True)

