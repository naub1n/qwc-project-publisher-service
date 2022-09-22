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

        publisher_groups_name = self.config.get('publisher_groups_name', {'publishers'})
        self.logger.debug("publisher_group_name : %s" % publisher_groups_name)

        # Extract user infos from identity
        if isinstance(identity, dict):
            username = identity.get('username')
        else:
            username = identity

        session = self.config_models.session()
        publisher_group = self.publisher_group_query(username, session, publisher_groups_name)
        session.close()

        return publisher_group

    def publisher_group_query(self, username, session, publisher_groups_name):
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
        user_groups_query = query.join(Group.users_collection) \
            .filter(User.name == username)

        user_is_publisher = True
        if publisher_groups_name:
            for group in publisher_groups_name:
                group_query = user_groups_query.filter(Group.name == group)
                (user_in_group, ), = session.query(group_query.exists())
                self.logger.debug('User %s in group %s : %s' % (username, group, user_in_group))
                if not user_in_group:
                    user_is_publisher = False
                    break

        self.logger.debug("publisher_role : %s" % str(user_is_publisher))

        return user_is_publisher
