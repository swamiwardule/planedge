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
import pytz

# Define the path to your config file
module_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the config file
config_path = os.path.join(module_dir, '..', 'config_file.conf')

# Initialize configparser and read the file
config = configparser.ConfigParser()
config.read(config_path)

# Read values from the configuration file
businessUnit = config.get('settings', 'businessUnit', fallback=None)
Authorization = config.get('settings', 'Authorization', fallback=None)
ContentType = config.get('settings', 'ContentType', fallback=None)

class BuUnit(models.Model):
    _name = 'business.unit'
    _rec_name = "description"
    #_order = 'notification_dt desc, id desc'
    _description = "BuUnit"

    buId = fields.Integer("Bu Id")
    description = fields.Text("Description")
    type = fields.Char("type")
    email = fields.Char("Email")
    #{'Id': 35, 'Description': 'MAHALUNGE 15', 'Type': 'B', 'Email1': 'abc@gmail.com'}



    def fields_get(self, allfields=None, attributes=None):
        res = super(BuUnit, self).fields_get(allfields, attributes=attributes or [])
        
        # List of fields that should NOT be readonly
        #editable_fields = ['vjd_bu_hie_id', 'vjd_pro_hie_id']  # Add the field names you want to keep editable
        
        for field in res:
            res[field]['readonly'] = True  # Make all other fields readonly
        return res
    
    @api.model
    def action_business_unit(self, timestamp):
        _logger.info("----- action_business_unit ----- (timestamp: %s)", timestamp)
        api_log_obj = self.env['api.log']
        ist = pytz.timezone('Asia/Kolkata')
        aware_dt = datetime.now(ist)                      # Aware datetime in IST
        utc_naive_dt = aware_dt.astimezone(pytz.utc).replace(tzinfo=None)
        log_vals = {
            'name': f'BusinessUnit Sync - {timestamp}',
            'api_name': 'bu',
            'create_datetime': utc_naive_dt,
        }

        headers = {
            "Authorization": Authorization,  # Replace with your token
            "Content-Type": ContentType,
        }

        try:
            response = requests.get(businessUnit, headers=headers)

            if response.status_code == 200:
                data = response.json()
                existing_ids = set(self.search([]).mapped('buId'))

                records_to_create = []

                for line in data:
                    try:
                        if isinstance(line, str):
                            line = ast.literal_eval(line)

                        if isinstance(line, dict):
                            if int(line['Id']) not in existing_ids:
                                records_to_create.append({
                                    'buId': line.get('Id', 0),
                                    'description': line.get('Description', ''),
                                    'type': line.get('Type', ''),
                                    'email': line.get('Email1', ''),
                                })
                        else:
                            _logger.warning("Skipping non-dictionary line: %s", line)
                    except Exception as e:
                        _logger.error("action_business_unit - Error processing line: %s. Error: %s", line, e)

                if records_to_create:
                    self.create(records_to_create)
                    message = f"action_business_unit ---success--- records created: {len(records_to_create)}"
                    log_vals.update({'state': 'done', 'message': message})
                    api_log_obj.sudo().create(log_vals)
                    return {'status': 'success', 'message': message}

                message = "action_business_unit ---success--- no new records to create"
                log_vals.update({'state': 'done', 'message': message})
                api_log_obj.sudo().create(log_vals)
                return {'status': 'success', 'message': message}

            else:
                error_msg = f"API response error. Status code: {response.status_code}, Response: {response.text}"
                _logger.error(error_msg)
                log_vals.update({'state': 'failed', 'error': error_msg, 'message': 'Failed to fetch data from businessUnit API'})
                api_log_obj.sudo().create(log_vals)
                return {'status': 'failed', 'message': 'Data not received'}

        except Exception as e:
            error_msg = f"Exception during business unit sync: {str(e)}"
            _logger.exception(error_msg)
            log_vals.update({'state': 'failed', 'error': error_msg, 'message': 'Exception during businessUnit API call'})
            api_log_obj.sudo().create(log_vals)
            return {'status': 'failed', 'message': 'Exception occurred during sync'}
    
    # @api.model
    # def action_business_unit(self, timestamp):
    #     _logger.info("-----action_business_unit-------. ""(service name: %s)", timestamp)
    #     # Optional: Add headers if required (e.g., for authentication)
    #     headers = {
    #         "Authorization": Authorization,  # Replace with your token if needed
    #         "Content-Type": ContentType,
    #     }
    #     # Make the GET request
    #     response = requests.get(businessUnit, headers=headers)
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         data = response.json()
    #         # Fetch existing IDs in the model
    #         existing_ids = set(self.search([]).mapped('buId'))
            
    #         # Prepare records to create
    #         records_to_create = []
    #         for line in data:
    #             try:
    #                 # Convert line to dictionary if it is a string
    #                 if isinstance(line, str):
    #                     line = ast.literal_eval(line)  # Convert to dictionary

    #                 # Proceed if the line is now a dictionary
    #                 if isinstance(line, dict):
    #                     if int(line['Id']) not in existing_ids:
    #                         records_to_create.append({
    #                             'buId': line.get('Id',0),
    #                             'description': line.get('Description',''),
    #                             'type': line.get('Type',''),
    #                             'email': line.get('Email1','')  # Adjust key names as per actual structure
    #                         })
    #                 else:
    #                     _logger.warning("Skipping non-dictionary line: %s", line)
    #             except Exception as e:
    #                 _logger.error(" action_business_unit Error processing line: %s. Error: %s", line, e)
                  
    #         # Create all new records in one batch
    #         if records_to_create:
    #             self.create(records_to_create)
    #             _logger.info("-action_business_unit -Data retrieved from API---. ""(%s)", data)
    #             return {'status': 'sucess', 'message': 'Data Created Sucessfully'}
    #         return {'status': 'sucess', 'message': 'No Records Found to Create '}
            
    #     else:
    #         _logger.info("-action_business_unit-Failed to retrieve data. Status code:-. ""(service name: %s)", response.status_code)
    #         _logger.info("-action_business_unit -Error message--. ""(: %s)", response.text)
    #         return {'status': 'failed', 'message': 'data not reeived'}
