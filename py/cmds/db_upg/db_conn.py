
# Get SQLAlchemy URL from same config. as the app
from API_operations.helpers.Service import Service
from helpers.link_to_legacy import read_config
_app_config = read_config()
conn = Service.build_connection(_app_config)