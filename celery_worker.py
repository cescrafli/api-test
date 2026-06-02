from app import create_app
from extensions import celery

app = create_app()

# This allows celery worker to pick up the app context
app.app_context().push()
