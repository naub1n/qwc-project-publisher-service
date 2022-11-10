from sqlalchemy import distinct
from sqlalchemy.sql import text as sql_text, exists

from qwc_services_core.config_models import ConfigModels
from qwc_services_core.runtime_config import RuntimeConfig
from qwc_services_core.database import DatabaseEngine
from qwc_services_core.auth import get_username, get_groups


class AccessControl:

    def __init__(self, tenant, logger):
        """Constructor

        :param str tenant: Tenant ID
        :param Logger logger: Application logger
        """
        self.tenant = tenant
        self.logger = logger

        self.config_handler = RuntimeConfig("projectPublisher", logger)
        self.config = self.config_handler.tenant_config(tenant)

    def is_publisher(self, identity):
        """Check if user is in publishers group

        :param str identity: User identity
        """
        db_engine = DatabaseEngine()
        conn_str = self.config.get('config_db_url', 'postgresql:///?service=qwc_configdb')
        self.config_models = ConfigModels(db_engine, conn_str)

        publisher_role_name = self.config.get('publisher_role_name', 'publishers')
        self.logger.debug("publisher_role_name : %s" % publisher_role_name)

        username = get_username(identity)
        groups = get_groups(identity)

        session = self.config_models.session()
        publisher_role = self.publisher_role_query(username, groups, session, publisher_role_name)
        session.close()

        return publisher_role

    def publisher_role_query(self, username, groups, session, publisher_role_name):
        """Create base query for all permissions of a user and group.
        Combine permissions from roles of user and user groups, groups roles and
        public role.

        :param str username: User name
        :param list or str groups: Groups names
        :param Session session: DB session
        :param str publisher_role_name: Publishers role name
        """
        Role = self.config_models.model('roles')
        Group = self.config_models.model('groups')
        User = self.config_models.model('users')

        # check groups list
        flat_groups_list = []
        if isinstance(groups, list):
            for item in groups:
                if isinstance(item, list):
                    for subitem in item:
                        flat_groups_list.append(subitem)
                else:
                    flat_groups_list.append(item)
        else:
            flat_groups_list.append(groups)

        # create query
        query = session.query(Role)

        # query permissions from roles in user groups
        user_groups_roles_query = query.join(Role.groups_collection) \
            .join(Group.users_collection) \
            .filter(User.name == username)

        # query permissions from direct user roles
        user_roles_query = query.join(Role.users_collection) \
            .filter(User.name == username)

        # query permissions from group roles
        group_roles_query = query.join(Role.groups_collection) \
            .filter(Group.name.in_(flat_groups_list))

        # combine queries
        query = user_groups_roles_query.union(user_roles_query) \
            .union(group_roles_query) \
            .filter(Role.name == publisher_role_name)

        (publisher_role, ), = session.query(query.exists())

        return publisher_role
