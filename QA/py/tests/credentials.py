
# These correspond to the rights in schema_prod.sql

ADMIN_USER_ID = 1
ORDINARY_USER_USER_ID = 2
CREATOR_USER_ID = 3
ORDINARY_USER2_USER_ID = 4

ADMIN_AUTH = {"Authorization": "Bearer "+str(ADMIN_USER_ID)}
USER_AUTH = {"Authorization": "Bearer "+str(ORDINARY_USER_USER_ID)}
CREATOR_AUTH = {"Authorization": "Bearer "+str(CREATOR_USER_ID)}
USER2_AUTH = {"Authorization": "Bearer "+str(ORDINARY_USER2_USER_ID)}
