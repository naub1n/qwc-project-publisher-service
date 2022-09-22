import os
import urllib
import requests

from qwc_services_core.runtime_config import RuntimeConfig


class ProjectPublisherService:
    """ProjectPublisher class
    Add a QWC2 webservice to publish or delete a qgis project.
    """

    def __init__(self, tenant, logger):
        """Constructor
        :param str tenant: Tenant ID
        :param Logger logger: Application logger
        """
        self.tenant = tenant
        self.logger = logger

        self.config_handler = RuntimeConfig("projectPublisher", logger)
        self.config = self.config_handler.tenant_config(tenant)

    def error_result(self, message):
        result = {'error': message}
        return result

    def success_result(self, message):
        result = {'success': message}
        return result

    def file_output_path(self, filename):
        projects_scan_path = self.config.get("qgis_projects_scan_base_dir")
        if not projects_scan_path:
            projects_scan_path = "D:/SIG/QWC"
        if projects_scan_path:
            project_filename = filename
            project_file_output = os.path.join(projects_scan_path, project_filename)
            return project_file_output
        else:
            self.logger.warning("qgis_projects_scan_base_dir not defined")
            return ''

    def project_path(self, filename):
        return self.file_output_path(filename)

    def publish(self, filename, file):
        """Publish QGIS project
        :param obj filename: .qgs project file name
        :param object file: POST request file
        """

        project_file_out = self.file_output_path(filename)

        self.logger.debug("Tenant : %s" % self.tenant)
        self.logger.info("Try to write data to '%s'" % project_file_out)

        if project_file_out:
            try:
                file.seek(0)
                file.save(project_file_out)
                self.logger.info("Project '%s' successfully saved" % filename)

            except Exception as e:
                msg = "Unable to write in file %s" % project_file_out
                self.logger.error(msg)
                self.logger.debug('Error : "%s"' % str(e))
                return self.error_result(msg)

            try:
                if self.update_config():
                    return self.success_result("Project '%s' successfully published" % filename)
                else:
                    return self.error_result("Project saved but unable to generate service configurations")
            except Exception as e:
                msg = "Unable to generate service configurations"
                self.logger.error(msg)
                self.logger.debug('Error : "%s"' % str(e))
                return self.error_result(msg)

        else:
            return self.error_result("Project cant not be published. Contact GIS Administrator")

    def delete(self, filename):
        """Delete QGIS project file from QWC2 scan dir
        :param str filename: .qgs project file name
        """
        project_file = self.file_output_path(filename)

        if not os.path.exists(project_file):
            return self.error_result("Project file '%s' does not exist" % filename)

        try:
            os.remove(project_file)
        except Exception as e:
            msg = "Unable to delete file %s" % project_file
            self.logger.error(msg)
            self.logger.debug("Error : %s" % str(e))
            return self.error_result(msg)

        try:
            if self.update_config():
                return self.success_result("Delete completed")
            else:
                return self.error_result("Project deleted but unable to generate service configurations")
        except Exception as e:
            msg = "Unable to generate service configurations"
            self.logger.error(msg)
            self.logger.debug('Error : "%s"' % str(e))
            return self.error_result(msg)

    def update_config(self):
        """Send request to QWC Config Service to update configurations"""
        config_generator_url = self.config.get('config_generator_service_url', "http://qwc-config-service:9090")
        response = requests.post(
            urllib.parse.urljoin(
                config_generator_url,
                "generate_configs?tenant=" + self.tenant))

        if 'CRITICAL' in response.text:
            msg = "Unable to generate service configurations"
            self.logger.error(msg)
            return False
        else:
            msg = "Service configurations generated"
            self.logger.info(msg)
            return True

    def get_project(self, filename, content_only=False):
        """Send project file path or content to user request
        :param str filename: .qgs project file name
        :param bool content_only: request download file or only qgis project file content
        """
        project_path = self.project_path(filename)
        if content_only:
            if os.path.exists(project_path):
                with open(project_path, 'rb') as project:
                    project_content = project.read()
                    project.close()
                return project_content
            else:
                return
        else:
            return self.project_path(filename)

