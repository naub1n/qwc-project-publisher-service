from sqlalchemy import distinct
from sqlalchemy.sql import text as sql_text, exists

from qwc_services_core.config_models import ConfigModels
from qwc_services_core.runtime_config import RuntimeConfig
from qwc_services_core.database import DatabaseEngine


class AccessControl:

    # name of admin iam.role
    PUBLISHER_GROUP_OR_ROLE_NAME = 'publisher'

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

        publisher_group_name = self.config.get('publisher_group_name', 'publishers')
        self.logger.debug("publisher_group_name : %s" % publisher_group_name)

        # Extract user infos from identity
        if isinstance(identity, dict):
            username = identity.get('username')
        else:
            username = identity

        session = self.config_models.session()
        publisher_group = self.publisher_group_query(username, session, publisher_group_name)
        session.close()

        return publisher_group

    def publisher_group_query(self, username, session, publisher_group_name):
        """Create query filtered by username and publishers group name
        :param str username: User name
        :param Session session: DB session
        :param str publisher_group_name: Publishers group name
        """
        Group = self.config_models.model('groups')
        User = self.config_models.model('users')

        # create query
        query = session.query(Group)

        # Get user groups
        groups_query = query.join(Group.users_collection) \
            .filter(Group.name == publisher_group_name) \
            .filter(User.name == username)

        self.logger.debug('User groups query : %s' % str(groups_query))

        (publisher_role, ), = session.query(groups_query.exists())

        self.logger.debug("publisher_role : %s" % str(publisher_role))

        return publisher_role