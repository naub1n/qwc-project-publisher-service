import logging
import os

from flask import Flask, Response, jsonify, request, send_file
from flask_restx import Api, Resource, reqparse
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from qwc_services_core.auth import auth_manager, optional_auth, get_identity
from qwc_services_core.api import CaseInsensitiveArgument
from qwc_services_core.tenant_handler import TenantHandler
from project_publisher_service import ProjectPublisherService
from access_control import AccessControl

AUTH_REQUIRED = os.environ.get('AUTH_REQUIRED', '0').lower() not in [0, "0", "false"]
ALLOWED_EXTENSIONS = ['qgs']

# Flask application
app = Flask(__name__)
api = Api(app, version='1.0', title='Publisher API',
          description='API for QWC Project Publisher service',
          default_label='Publisher operations', doc='/api/')
# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

# Setup the Flask-JWT-Extended extension
jwt = auth_manager(app)
# app.secret_key = app.config['JWT_SECRET_KEY']


# create tenant handler
tenant_handler = TenantHandler(app.logger)


def project_publisher_service_handler():
    """Get or create a Project Publisher Service instance for a tenant."""
    tenant = tenant_handler.tenant()
    handler = tenant_handler.handler('projectPublisher', 'publisher', tenant)
    if handler is None:
        handler = tenant_handler.register_handler(
            'publisher', tenant, ProjectPublisherService(tenant, app.logger))
    return handler


def get_username():
    # Extract user infos from identity
    identity = get_identity()
    if isinstance(identity, dict):
        username = identity.get('username')
    else:
        username = identity
    return username

def check_filename(api, params):
    if 'filename' in params and params['filename']:
        pass
    else:
        api.abort(404, "filename parameter is required")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# request parser
publish_parser = reqparse.RequestParser(argument_class=CaseInsensitiveArgument)
publish_parser.add_argument('filename', type=str)
publish_parser.add_argument('file', location='files', type=FileStorage, required=True)

get_parser = reqparse.RequestParser(argument_class=CaseInsensitiveArgument)
get_parser.add_argument('filename', required=True, type=str)
get_parser.add_argument('content_only', default="true", type=str)

delete_parser = reqparse.RequestParser(argument_class=CaseInsensitiveArgument)
delete_parser.add_argument('filename', required=True, type=str)


@app.before_request
@optional_auth
def assert_user_is_logged():
    app.logger.debug("AUTH_REQUIRED : %s" % AUTH_REQUIRED)
    identity = get_identity()
    username = get_username()

    if AUTH_REQUIRED:
        app.logger.debug("Access with identity %s" % username)
        if identity is None:
            msg = "Access denied, authentication required"
            app.logger.info(msg)
            api.abort(401, msg)

        access_control = AccessControl(tenant_handler.tenant(), app.logger)
        if not access_control.is_publisher(identity):
            msg = "Access denied for user %s. The user us not a member of publisher group." % username
            app.logger.info(msg)
            api.abort(401, msg)

# routes
@api.route('/publish')
class PublishProject(Resource):
    @api.doc('publishproject')
    @api.param('filename', 'Name used to save project in qgs-resources folder')
    @api.param('file', 'QGIS Project with .qgs extension')
    @api.expect(publish_parser)
    @optional_auth
    def post(self):

        # check if the post request has the file part
        if 'file' not in request.files:
            api.abort(404, "No file part")
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            api.abort(404, "No selected file")
        if not file or not allowed_file(file.filename):
            api.abort(404, "File not allowed")

        params = publish_parser.parse_args()

        publish_service = project_publisher_service_handler()
        tenant = publish_service.tenant

        if 'filename' in params and params['filename']:
            filename = secure_filename(params['filename'])
        else:
            filename = secure_filename(file.filename)

        username = get_username()
        result = publish_service.publish(filename, file)

        app.logger.debug('Publish result : "%s' % result)
        app.logger.info('User %s publish project %s in tenant %s' % (username, filename, tenant))

        return jsonify(result)

@api.route('/deleteproject')
class DeleteProject(Resource):
    @api.doc('deleteproject')
    @api.param('filename', 'Name used to save project in qgs-resources folder')
    @api.expect(delete_parser)
    @optional_auth
    def delete(self):
        params = delete_parser.parse_args()

        #Check 'filename' parameter
        check_filename(api, params)

        publish_service = project_publisher_service_handler()
        tenant = publish_service.tenant
        filename = params['filename']

        username = get_username()

        result = publish_service.delete(filename)
        app.logger.debug('Delete result : "%s' % result)
        if 'success' in result:
            app.logger.info('User %s delete project %s in tenant %s' % (username, filename, tenant))
        return jsonify(result)

@api.route('/getproject')
class GetProject(Resource):
    @api.doc('getproject')
    @api.param('filename', 'Name used to save project in qgs-resources folder')
    @api.expect(get_parser)
    @optional_auth
    def get(self):

        params = get_parser.parse_args()

        # Check 'filename' parameter
        check_filename(api, params)

        publish_service = project_publisher_service_handler()
        tenant = publish_service.tenant
        filename = params['filename']
        content_only = params.get('content_only', "true").lower() in ["true", "1"]
        username = get_username()

        result = publish_service.get_project(filename, content_only)

        app.logger.debug('Download result : "%s' % result)
        if result:
            if content_only:
                app.logger.info('User %s download content of project %s in tenant %s' % (username, filename, tenant))
                return Response(result, mimetype='text/xml')
            else:
                app.logger.info('User %s download project file %s in tenant %s' % (username, filename, tenant))
                return send_file(result, as_attachment=True)
        else:
            msg = "Project file %s empty or does not exist" % filename
            app.logger.debug(msg)
            api.abort(404, msg)

@api.route('/listprojects')
class ListProjects(Resource):
    @api.doc('listprojects')
    @optional_auth
    def get(self):
        publish_service = project_publisher_service_handler()
        tenant = publish_service.tenant
        username = get_username()

        result = publish_service.list_projects(ALLOWED_EXTENSIONS)

        app.logger.info('User %s list projects in tenant %s' % (username, tenant))
        app.logger.debug(result)
        return jsonify(result)

""" readyness probe endpoint """


@app.route("/ready", methods=['GET'])
def ready():
    return jsonify({"status": "OK"})


""" liveness probe endpoint """


@app.route("/healthz", methods=['GET'])
def healthz():
    return jsonify({"status": "OK"})


# local webserver
if __name__ == '__main__':
    print("Starting Project publisher...")
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=5100, debug=True)