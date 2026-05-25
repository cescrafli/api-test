from flask_restx import Namespace, Resource, fields
from sqlalchemy import text
from db import get_session

api = Namespace('Inventory', description='Warehouse inventory and operational metrics operations')

# Define Swagger Data Models
# Using String for large numbers to prevent truncation/out of range errors in Swagger/JSON
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
    'AreaCategory': fields.String(description='Mapped Area Category', example='BigBag'),
    'RackingAvailable': fields.Integer(description='Distinct count of storage units', example=150)
})

def map_area_category(bin_code):
    """Maps the first two letters of the storage bin to a category."""
    if not bin_code or len(bin_code) < 2:
        return 'Unknown'
    
    prefix = bin_code[:2].upper()
    # Dynamic mapping logic
    category_map = {
        'BB': 'BigBag',
        'PM': 'PM',
        'RM': 'RM'
    }
    
    return category_map.get(prefix, 'Other')


@api.route('/status')
class InventoryStatus(Resource):
    @api.doc('get_inventory_status')
    @api.marshal_list_with(inventory_model)
    def get(self):
        """Fetch daily inventory status with dynamically mapped area categories."""
        session = get_session()
        
        # In a real scenario, this would query the specific master table.
        # Example query using text()
        query = text(\"""
            SELECT 
                CAST(STORAGEUNIT AS CHAR) as STORAGEUNIT,
                CAST(GR_Number AS CHAR) as GR_Number,
                StorageBin,
                MaterialCode,
                Quantity
            FROM inventory_master
            LIMIT 100
        \""")
        
        try:
            result = session.execute(query).fetchall()
            
            response_data = []
            for row in result:
                # Map the row to dictionary
                row_dict = dict(row._mapping)
                # Apply dynamic filter for area
                row_dict['AreaCategory'] = map_area_category(row_dict.get('StorageBin', ''))
                response_data.append(row_dict)
                
            return response_data, 200
        except Exception as e:
            api.abort(500, f"Database error: {str(e)}")


@api.route('/metrics')
class OperationalMetrics(Resource):
    @api.doc('get_operational_metrics')
    @api.marshal_list_with(metrics_model)
    def get(self):
        """Fetch warehouse operational metrics (e.g. Racking Available using DISTINCT COUNT)."""
        session = get_session()
        
        # Raw SQL to calculate distinct count of storage units, grouped by the first two characters of StorageBin
        query = text(\"""
            SELECT 
                CURRENT_DATE() as Date,
                UPPER(SUBSTRING(StorageBin, 1, 2)) as AreaPrefix,
                COUNT(DISTINCT STORAGEUNIT) as RackingAvailable
            FROM inventory_master
            WHERE StorageBin IS NOT NULL
            GROUP BY UPPER(SUBSTRING(StorageBin, 1, 2))
        \""")
        
        try:
            result = session.execute(query).fetchall()
            
            response_data = []
            for row in result:
                row_dict = dict(row._mapping)
                prefix = row_dict.get('AreaPrefix', '')
                
                # Apply business logic mapping
                if prefix == 'BB':
                    area_category = 'BigBag'
                elif prefix == 'PM':
                    area_category = 'PM'
                elif prefix == 'RM':
                    area_category = 'RM'
                else:
                    area_category = 'Other'
                    
                response_data.append({
                    'Date': str(row_dict.get('Date')),
                    'AreaCategory': area_category,
                    'RackingAvailable': row_dict.get('RackingAvailable', 0)
                })
                
            return response_data, 200
        except Exception as e:
            api.abort(500, f"Database error: {str(e)}")
