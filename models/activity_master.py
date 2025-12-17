from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta , time , date
import re
import requests
import json
import ast
import os
import configparser


# Define the path to your config file
module_dir = os.path.dirname(os.path.abspath(__file__))
# Path to the config file
config_path = os.path.join(module_dir, '..', 'config_file.conf')
# Initialize configparser and read the file
config = configparser.ConfigParser()
config.read(config_path)
# Read values from the configuration file
activityMaster = config.get('settings', 'Activitymaster', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)


class ActivityMaster(models.Model):
    _name = 'activity.master'
    _rec_name = "activityId"
    #_order = 'notification_dt desc, id desc'
    _description = "ActivityMaster"

    activityId = fields.Integer("ActivityId")
    code = fields.Char("Code")
    uom = fields.Char("Uom")
    description = fields.Char("Description")
    constructionActivityGroup = fields.Char("Construction Activity Group")
    constructionActivityGroupID = fields.Integer("Activity Group ID")

    @api.model
    def action_activity_master(self, timestamp):
        api_log_obj = self.env['api.log']
        log_vals = {
            'name': f'ActivityMaster Sync - {timestamp}',
            'api_name': 'activity_master',
            'create_datetime': datetime.now(),
        }

        try:
            _logger.info("---action_activity_master-------. (service name: %s)", timestamp)
            
            headers = {
                "Authorization": Authorization,  # Replace with your actual variable or value
                "Content-Type": ContentType,
            }

            response = requests.get(activityMaster, headers=headers)

            if response.status_code == 200:
                data = response.json()
                existing_ids = set(self.search([]).mapped('activityId'))
                records_to_create = []

                for line in data:
                    try:
                        if isinstance(line, str):
                            line = ast.literal_eval(line)
                        if isinstance(line, dict):
                            vals = {
                                'activityId': line.get('ActivityId', 0),
                                'code': line.get('Code', ''),
                                'description': line.get('Description', ''),
                                'uom': line.get('Uom', ''),
                                'constructionActivityGroup': line.get('ConstructionActivityGroup', ''),
                                'constructionActivityGroupID': line.get('ConstructionActivityGroupID', 0),
                            }
                            if int(line['ActivityId']) not in existing_ids:
                                records_to_create.append(vals)
                            else:
                                self.search([('activityId', '=', line['ActivityId'])]).write(vals)
                        else:
                            _logger.warning("Skipping non-dictionary line: %s", line)
                    except Exception as e:
                        _logger.error("Error processing line: %s. Error: %s", line, e)

                if records_to_create:
                    self.create(records_to_create)
                    message = 'Activity Master Data Created Successfully'
                else:
                    message = 'Activity Master - No Records Found to Create'

                log_vals.update({
                    'state': 'done',
                    'message': message,
                })
                api_log_obj.sudo().create(log_vals)
                return {'status': 'success', 'message': message}
            else:
                error_msg = f"Failed to retrieve data. Status code: {response.status_code}, Response: {response.text}"
                log_vals.update({
                    'state': 'failed',
                    'error': error_msg,
                    'message': 'Failed to fetch data from API.'
                })
                api_log_obj.sudo().create(log_vals)
                return {'status': 'failed', 'message': 'API response error'}

        except Exception as e:
            error_text = f"Unexpected error: {str(e)}"
            log_vals.update({
                'state': 'failed',
                'error': error_text,
                'message': 'Exception occurred during API sync.'
            })
            api_log_obj.sudo().create(log_vals)
            _logger.error(error_text)
            return {'status': 'failed', 'message': 'Exception during API call'}


    # @api.model
    # def action_activity_master(self, timestamp):
    #     _logger.info("---action_activity_master-------. ""(service name: %s)", timestamp)
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     # Make the GET request
    #     response = requests.get(activityMaster, headers=headers)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         data = response.json()
    #         # Fetch existing IDs in the model
    #         existing_ids = set(self.search([]).mapped('activityId'))
    #         #_logger.info("-existing_ids--. ""(service name: %s)", existing_ids)
    #         # Prepare records to create
    #         records_to_create = []
    #         for line in data:
    #             try:
    #                 # Convert line to dictionary if it is a string
    #                 if isinstance(line, str):
    #                     line = ast.literal_eval(line)  # Convert to dictionary

    #                 # Proceed if the line is now a dictionary
    #                 if isinstance(line, dict):
    #                     if int(line['ActivityId']) not in existing_ids:
    #                         records_to_create.append({
    #                             'activityId': line.get('ActivityId',0),
    #                             'code': line.get('Code',''),
    #                             'description':line.get('Description',''),
    #                             'uom': line.get('Uom',0),  # Adjust key names as per actual structure
    #                             'constructionActivityGroup': line.get('ConstructionActivityGroup',''), 
    #                             'constructionActivityGroupID': line.get('ConstructionActivityGroupID',0), 


    #                         })
    #                     else:
    #                         self.search([('activityId', '=', line['ActivityId'])]).write({
    #                             'activityId': line.get('ActivityId',0),
    #                             'code': line.get('Code',''),
    #                             'description':line.get('Description',''),
    #                             'uom': line.get('Uom',0),  # Adjust key names as per actual structure
    #                             'constructionActivityGroup': line.get('ConstructionActivityGroup',''), 
    #                             'constructionActivityGroupID': line.get('ConstructionActivityGroupID',0), 

    #                         })

    #                 else:
    #                     _logger.warning(" action_activity_master Skipping non-dictionary line: %s", line)
    #             except Exception as e:
    #                 _logger.error("Error processing line: %s. Error: %s", line, e)
                  
    #         # Create all new records in one batch
    #         if records_to_create:
    #             self.create(records_to_create)
    #             _logger.info("--Activity Master Data Created Sucessfully---")
    #             return {'status': 'sucess', 'message': 'Activity Master Data Created Sucessfully'}
    #         return {'status': 'sucess', 'message': 'Activity Master - No Records Found to Create '}
            
    #     else:
    #         _logger.info("-action_activity_master-Failed to retrieve data. Status code:-. ""(%s)", response.status_code)
    #         _logger.info("-action_activity_master-Error message--. ""(%s)", response.text)
    #         return {'status': 'failed', 'message': 'data not reeived'}


class ConstttructionActivityGroup(models.Model):
    _name = 'construction.activity.group'
    _rec_name = "name"
    #_order = 'notification_dt desc, id desc'
    _description = "ConstttructionActivityGroup"

    name = fields.Char("Construction Activity Group")
    activity_id = fields.Integer("Activity ID")
    activity_group_id = fields.Integer("Activity Group Id")

    name = fields.Char("Construction Activity Group")

    type_1 = fields.Selection([('floor', 'Floor'), ('flat', 'Flat')], string="Type 1")
    type_2 = fields.Selection([('common_area', 'Common Area'), ('development', 'Development')], string="Type 2")


    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The Constttruction Activity Group name must be unique!')
    ]
