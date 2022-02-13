
# Get SQLAlchemy URL from same config. as the app
from API_operations.helpers.Service import Service
from helpers.link_to_legacy import read_config
app_config = read_config()
try:
    # TODO: Dirty
    conn = Service.build_connection(app_config)
except:
    conn = None