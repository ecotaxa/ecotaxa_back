
# Get SQLAlchemy URL from same config. as the app
from API_operations.helpers.Service import Service
from helpers.AppConfig import Config
app_config = Config()
try:
    # TODO: Dirty
    conn = Service.build_connection(app_config)
except:
    conn = None