# These correspond to the rights in schema_prod.sql

ADMIN_USER_ID = 1  # From default build
ORDINARY_USER_USER_ID = 2
CREATOR_USER_ID = 3
ORDINARY_USER2_USER_ID = 4
REAL_USER_ID = 6
ORDINARY_USER3_USER_ID = 8
USERS_ADMIN_USER_ID = 7

ADMIN_AUTH = {"Authorization": "Bearer " + str(ADMIN_USER_ID)}
USER_AUTH = {"Authorization": "Bearer " + str(ORDINARY_USER_USER_ID)}
CREATOR_AUTH = {"Authorization": "Bearer " + str(CREATOR_USER_ID)}
USER2_AUTH = {"Authorization": "Bearer " + str(ORDINARY_USER2_USER_ID)}
REAL_USER_AUTH = {"Authorization": "Bearer " + str(REAL_USER_ID)}
USER3_AUTH = {"Authorization": "Bearer " + str(ORDINARY_USER3_USER_ID)}
USERS_ADMIN_AUTH = {"Authorization": "Bearer " + str(USERS_ADMIN_USER_ID)}
