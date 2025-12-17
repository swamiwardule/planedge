# -*- coding: utf-8 -*-
# from distutils.command.check import check
# from setuptools import setup
# from setuptools.command.check import check

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class TrainingReport(models.Model):
    _name = 'training.report'
    _rec_name = 'project_info_id'
    _description = "Training Report"


    project_info_id = fields.Many2one('project.info','Project')
    user_id = fields.Many2one('res.users','User')
    training_report_line_ids = fields.One2many('training.report.line','training_report_id')
    image_ids = fields.One2many('training.report.image', 'training_report_id', string='Images')
    training_dated_on = fields.Date('Training Dated On')
    topic_of_training = fields.Char('Topic of Training')
    tower_id = fields.Many2one('project.tower','Tower')
    location = fields.Char('Location')
    trainer_name = fields.Char('Trainer Name')
    training_start_time = fields.Char(string='Training Start Time', help="Time in HH:MM AM/PM format")
    training_end_time = fields.Char(string='Training End Time', help="Time in HH:MM AM/PM format")
    total_duration = fields.Char('Total Duration')
    total_manhours = fields.Char('Total Manhours')
    description = fields.Text('Description')


    def get_training_report_details(self,data):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        traning_data = []
    
        user_id = data.get('user_id',False)
        if user_id:
            domain = [('user_id','=',user_id)]
        else:
            domain = []
      
        records = self.search(domain)
        for record in records:
            line_data = []
            image_data = []

            data = {
                'training_report_id': record.id,
                'project_info_id':str(record.project_info_id.id) or '',
                'project_name':str(record.project_info_id.name) or '',
                'user_id':str(record.user_id.id) or '',
                'training_dated_on':str(record.training_dated_on) or '',
                'topic_of_training':str(record.topic_of_training) or '',
                'tower_id':str(record.tower_id.id) or '',
                'tower_name':str(record.tower_id.name) or '',
                'trainer_name':str(record.trainer_name) or '',
                'training_start_time':str(record.training_start_time) or '',
                'training_end_time':str(record.training_end_time) or '',
                'total_duration':str(record.total_duration) or '',
                'total_manhours':str(record.total_manhours) or '',
                'description':str(record.description) or '',
                'location':str(record.location) or '',
            }

            for line in record.training_report_line_ids:
                line_data.append({'name':line.name or '','tag':line.tag or ''})
            data.update({'training_given_to':line_data})

            for im_data in record.image_ids:
                image=url+"/web/image?model=training.report.image&field=image&id="+str(im_data.id)
                image_data.append(image)
            data.update({'overall_images':image_data})
            traning_data.append(data)

        return traning_data

    def create_training_report(self,data):
        line_data = []
        image_data = []
        res = {
            
            'project_info_id':data.get('project_id'),
            'user_id':int(data.get('user_id','')),
            'training_dated_on':data.get('training_date'),
            'topic_of_training':data.get('training_topic'),
            'tower_id':data.get('tower_id'),
            'trainer_name':data.get('trainer_name'),
            'training_start_time':self.convert_time_to_24hr_format(data.get('start_time')),
            'training_end_time':self.convert_time_to_24hr_format(data.get('end_time')),
            'total_duration':data.get('total_duration'),
            'total_manhours':data.get('total_manhours'),
            'description':data.get('description',''),
            'location':data.get('location',''),
        }
  
        training_id = self.create(res)

        for value in data.get('training_given_to'):
            line_data.append({'name':value.get('name'),'tag':value.get('tag',''),'training_report_id':training_id.id})
        if line_data:
            self.env['training.report.line'].create(line_data)
        for image in data.get('overall_images'):
            image_data.append({'image':image,'training_report_id':training_id.id})
        if image_data:
            self.env['training.report.image'].create(image_data)

    def update_training_report(self,data):
        line_data = []
        image_data = []
        training_id = self.browse(int(data.get('training_report_id')))
        res = {
            'project_info_id':data.get('project_id'),
            'user_id':int(data.get('user_id','')),
            'training_dated_on':data.get('training_date'),
            'topic_of_training':data.get('training_topic'),
            'tower_id':data.get('tower_id'),
            'trainer_name':data.get('trainer_name'),
            'training_start_time':self.convert_time_to_24hr_format(data.get('start_time')),
            'training_end_time':self.convert_time_to_24hr_format(data.get('end_time')),
            'total_duration':data.get('total_duration'),
            'total_manhours':data.get('total_manhours'),
            'description':data.get('description',''),
            'location':data.get('location',''),
        }
        training_id.write(res)
        if training_id.training_report_line_ids:
            # Get the existing record IDs to delete them
            training_id.training_report_line_ids.unlink()
   
        for value in data.get('training_given_to'):
            line_data.append({'name':value.get('name'),'tag':value.get('tag',''),'training_report_id':training_id.id})
        if line_data:
            self.env['training.report.line'].create(line_data)

        # # Handle overall images
        # if training_id.image_ids:
        #     # Get the existing image record IDs to delete them
        #     training_id.image_ids.unlink()
            
        # for image in data.get('overall_images'):
        #     image_data.append({'image': image, 'training_report_id': training_id.id})
        # if image_data:
        #     self.env['training.report.image'].create(image_data)

        return True

  
      
    def convert_time_to_24hr_format(self, time_str):
        """
        Converts 12-hour format time (e.g., '10:10 AM') to 24-hour format (e.g., '10:10').
        """
        try:
            # Convert "10:10 AM" to "10:10" in 24-hour format
            time_obj = datetime.strptime(time_str, '%I:%M %p')
            return time_obj.strftime('%H:%M')
        except ValueError:
            raise ValueError("Invalid time format. Use 'HH:MM AM/PM' format.")



class TrainingReportLine(models.Model):
    _name = 'training.report.line'
    _description = "Training Report Line"

    name = fields.Char('Name')
    training_report_id = fields.Many2one('training.report','Training Report')
    # sr_no = fields.Integer(string="Sr. No", compute='_compute_sr_no', store=True)
    sr_no = fields.Integer(string="Sr. No")
    tag = fields.Selection(string='Tag',selection=[('contractor', 'Contractor'), ('vjd', 'Dreamwarez')])

    
class TrainingReportImages(models.Model):
    _name = 'training.report.image'
    _description = 'Training Report Images'

    training_report_id = fields.Many2one('training.report', string='Training Report', ondelete='cascade')
    image = fields.Binary('Image')
    image_name = fields.Char('Image Name')