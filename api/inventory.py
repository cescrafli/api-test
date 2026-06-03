from flask_restx import Namespace, Resource, fields
from flask import request, current_app
from sqlalchemy import text
from db import get_session
from extensions import cache, celery

api = Namespace('Inventory', description='Warehouse inventory and operational metrics operations')

# Define Swagger Data Models
inventory_model = api.model('InventoryStatus', {
    'STORAGEUNIT': fields.String(description='Large digit Storage Unit ID', example='998877665544332211'),
    'GR_Number': fields.String(description='Large digit Goods Receipt Number', example='112233445566778899'),
    'StorageBin': fields.String(description='Storage Bin Code', example='RM-01A'),
    'AreaCategory': fields.String(description='Mapped Area Category', example='RM'),
    'MaterialCode': fields.String(description='Material Code', example='MAT123'),
    'Quantity': fields.Float(description='Quantity of material', example=100.5)
})

metrics_model = api.model('OperationalMetrics', {
    'Date': fields.String(description='Date of metrics', example='2026-05-25'),
    'AreaCategory': fields.String(description='Mapped Area Category', example='PM'),
    'RackingAvailable': fields.Integer(description='Distinct count of storage units', example=150),
    '% Occupancy PM Ambient': fields.Float(description='Occupancy percentage', example=75.5)
})

bulk_upload_response = api.model('BulkUploadResponse', {
    'message': fields.String(description='Status message'),
    'task_id': fields.String(description='Celery Task ID')
})

# Celery Task for background insertion
@celery.task
def process_bulk_upload(payload):
    session = get_session()
    try:
        # executemany style execution for extreme speed
        query = text("""
            INSERT INTO inventory_master (STORAGEUNIT, GR_Number, StorageBin, MaterialCode, Quantity)
            VALUES (:STORAGEUNIT, :GR_Number, :StorageBin, :MaterialCode, :Quantity)
        """)
        # We assume payload is a list of dicts matching the fields
        session.execute(query, payload)
        session.commit()
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

@api.route('/status')
class InventoryStatus(Resource):
    @api.doc('get_inventory_status', params={'category': 'Filter by Area Category (e.g. PM, RM, BigBag)'})
    @api.marshal_list_with(inventory_model)
    @cache.cached(timeout=60, query_string=True)
    def get(self):
        """Fetch daily inventory status with SQL-level area category mapping."""
        session = get_session()
        category_filter = request.args.get('category')
        
        base_query = """
            SELECT 
                CAST(STORAGEUNIT AS CHAR) as STORAGEUNIT,
                CAST(GR_Number AS CHAR) as GR_Number,
                StorageBin,
                MaterialCode,
                Quantity,
                CASE UPPER(SUBSTRING(StorageBin, 1, 2))
                    WHEN 'BB' THEN 'BigBag'
                    WHEN 'PM' THEN 'PM'
                    WHEN 'RM' THEN 'RM'
                    ELSE 'Other'
                END AS AreaCategory
            FROM inventory_master
        """
        
        params = {}
        if category_filter:
            base_query += """
            WHERE CASE UPPER(SUBSTRING(StorageBin, 1, 2))
                    WHEN 'BB' THEN 'BigBag'
                    WHEN 'PM' THEN 'PM'
                    WHEN 'RM' THEN 'RM'
                    ELSE 'Other'
                  END = :category
            """
            params['category'] = category_filter
            
        base_query += " LIMIT 1000" # arbitrary limit to prevent mega payload
        
        try:
            result = session.execute(text(base_query), params).fetchall()
            
            response_data = [dict(row._mapping) for row in result]
            return response_data, 200
        except Exception as e:
            api.abort(500, f"Database error: {str(e)}")


@api.route('/metrics')
class OperationalMetrics(Resource):
    @api.doc('get_operational_metrics', params={'category': 'Filter by Area Category (e.g. PM, RM, BigBag)'})
    @api.marshal_list_with(metrics_model)
    @cache.cached(timeout=60, query_string=True)
    def get(self):
        """Fetch warehouse operational metrics with SQL-level mapping and occupancy calculations."""
        session = get_session()
        category_filter = request.args.get('category')
        
        base_query = """
            SELECT 
                CURRENT_DATE() as Date,
                CASE UPPER(SUBSTRING(StorageBin, 1, 2))
                    WHEN 'BB' THEN 'BigBag'
                    WHEN 'PM' THEN 'PM'
                    WHEN 'RM' THEN 'RM'
                    ELSE 'Other'
                END AS AreaCategory,
                COUNT(DISTINCT STORAGEUNIT) as RackingAvailable
            FROM inventory_master
            WHERE StorageBin IS NOT NULL
        """
        
        params = {}
        if category_filter:
            base_query += """
                AND CASE UPPER(SUBSTRING(StorageBin, 1, 2))
                    WHEN 'BB' THEN 'BigBag'
                    WHEN 'PM' THEN 'PM'
                    WHEN 'RM' THEN 'RM'
                    ELSE 'Other'
                END = :category
            """
            params['category'] = category_filter
            
        base_query += """
            GROUP BY 
                CASE UPPER(SUBSTRING(StorageBin, 1, 2))
                    WHEN 'BB' THEN 'BigBag'
                    WHEN 'PM' THEN 'PM'
                    WHEN 'RM' THEN 'RM'
                    ELSE 'Other'
                END
        """
        
        try:
            result = session.execute(text(base_query), params).fetchall()
            
            response_data = []
            # Dynamic MAX_CAPACITY from config
            MAX_CAPACITY = current_app.config['MAX_CAPACITY'] 

            for row in result:
                row_dict = dict(row._mapping)
                racking_available = row_dict.get('RackingAvailable', 0)
                
                # Add Occupancy calculation
                occupancy = (racking_available / MAX_CAPACITY) * 100.0 if racking_available else 0.0
                
                response_data.append({
                    'Date': str(row_dict.get('Date')),
                    'AreaCategory': row_dict.get('AreaCategory'),
                    'RackingAvailable': racking_available,
                    '% Occupancy PM Ambient': round(occupancy, 2)
                })
                
            return response_data, 200
        except Exception as e:
            api.abort(500, f"Database error: {str(e)}")

@api.route('/bulk-upload')
class BulkUpload(Resource):
    @api.doc('bulk_upload_inventory')
    @api.expect([inventory_model])
    @api.marshal_with(bulk_upload_response, code=202)
    def post(self):
        """Asynchronously process thousands of inventory records."""
        payload = request.json
        if not payload:
            api.abort(400, "Payload is empty")
            
        # Send task to Celery
        task = process_bulk_upload.delay(payload)
        
        return {'message': 'Data accepted and is being processed', 'task_id': task.id}, 202
