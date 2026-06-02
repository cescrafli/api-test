from flask import Flask
from flask_restx import Api
from config import Config
from db import close_session
from extensions import cache, celery
from api.inventory import api as inventory_ns

def create_app():
    """Factory function to create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Extensions
    cache.init_app(app)
    
    # Configure Celery
    celery.conf.update(app.config)
    
    # TaskBase for context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Initialize Flask-RESTX
    api = Api(
        app, 
        version='1.0', 
        title='Logistics Operational Data API',
        description='A read-only RESTful API for real-time warehouse metrics and inventory status.',
        doc='/docs'  # Swagger UI endpoint
    )

    # Register Namespaces
    api.add_namespace(inventory_ns, path='/api/v1/inventory')

    # Register teardown function to clean up database connections
    @app.teardown_appcontext
    def teardown_db(exception=None):
        close_session(exception)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=(app.config['FLASK_ENV'] == 'development'))
