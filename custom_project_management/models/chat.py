    @restapi.method([(["/submit/hqi/flat"], "POST")], auth="user")
    def submit_hqi_flat(self):
        params = request.params
        flat_id = int(params.get('flat_id'))
        if not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        flat_rec = self.env['project.flats'].sudo().browse(flat_id)
        
        value = self.env['flat.site.visit'].create_first_site_visit(flat_id)
        if value == 100:
            return Response(json.dumps({'status': 'Failed', 'message': 'Visit Exists'}),
                        content_type='application/json;charset=utf-8', status=200)
        if value == 300:
            return Response(json.dumps({'status': 'Failed', 'message': 'Unit Locations does not exists'}),
                        content_type='application/json;charset=utf-8', status=200)
        flat_rec.hqi_state = 'progress'
        flat_rec.tower_id.hqi_state = 'progress'
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'HQI set to progress'}),
                        content_type='application/json;charset=utf-8', status=200)

    class FlatSiteVisit(models.Model):
        _name = 'flat.site.visit'
        _description = "Flat Site Visit"

    @api.model
    def create_first_site_visit(self,flat_id = False):
        #_logger.info(f"----------flat_id-----------: {flat_id}")
        if flat_id:
            flat_rec = self.env['project.flats'].browse(flat_id)
            #_logger.info(f"--------flat_rec-------------: {flat_rec}")
            if not flat_rec.flat_site_visit_ids:

                unit_locations_rec = self.env['unit.locations'].search([('unit_type', '=',flat_rec.unit_type)], order='sequence asc')
                if not unit_locations_rec:
                    return 300
                location_vals = [(0, 0, {'name': rec.name, 'unit_type': rec.unit_type}) for rec in unit_locations_rec]

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

    @restapi.method([(["/submit/flat/sv/location/obseration"], "POST")], auth="user")
    def submit_flat_sv_location_observation(self):
        params = request.params
        _logger.info("-submit_flat_sv_location_observationsubmit_flat_sv_location_observation---,%s",params)

        location_id = int(params.get('location_id'))
        
        if not location_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Locarion ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        data = self.env['site.visit.location.observation'].sudo().submit_flat_sv_location_observation(params)       
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flat Visits','data': data}),
                        content_type='application/json;charset=utf-8', status=200)


    class SiteVisitLocationObservation(models.Model):
        _name = 'site.visit.location.observation'
        _description = "Site Visit Location Observation"

    @api.model
    def submit_flat_sv_location_observation(self,params):
        _logger.info(f"-----submit_flat_sv_location_observation-----------: {params}")

        site_visit_location = self.create({
            'site_visit_location_id': int(params.get('location_id')),  # Replace with the actual ID
            'name': params.get('name'),
            'date': params.get('date'),
            'issue_category_id':params.get('issue_category_id'),
            'issue_type_id':params.get('issue_type_id'),
            'description':params.get('description'),
            'impact':params.get('impact'),
                })

functionality is
from the application /submit/hqi/flat is getting called.
then first site visit 1 is getting created then user from application is opening site visit 1 then location and then create observation and calling /submit/flat/sv/location/obseration
so observation is created from user(checker)
now on same observation form is opened by user(maker) doing something lets say change the date and calling submit_flat_sv_location_observation
now this time site visit 2 should be create and under that location observation is by  submitted user(maker) gets created.
then same form user(checker) will open and see some operation if it is ok then he will click on approved button and form will closed otehrwise again he will call /submit/flat/sv/location/obseration
now again user(maker) open this form did some chagnes and submit the form to checker in site visit 3 so after site visit 3 it gets stopped
