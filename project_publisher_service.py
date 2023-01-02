import os
import urllib
import requests

from pathlib import Path
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

    def output_path(self, relpath):
        projects_scan_path = self.config.get("qgis_projects_scan_base_dir")
        self.logger.debug("projects_scan_path : %s" % projects_scan_path)
        self.logger.debug("relpath : %s" % relpath)
        if projects_scan_path:
            if relpath[0] == "/":
                relpath = relpath[1:]
            output_path = os.path.join(projects_scan_path, relpath)
            self.logger.debug("output_path : %s" % output_path)
            return output_path
        else:
            self.logger.warning("qgis_projects_scan_base_dir not defined")
            return ''

    def publish(self, filename, file):
        """Publish QGIS project
        :param obj filename: .qgs project file name
        :param object file: POST request file
        """

        project_file_out = self.output_path(filename)

        self.logger.debug("Tenant : %s" % self.tenant)
        self.logger.info("Try to write data to '%s'" % project_file_out)

        if project_file_out:
            try:
                os.makedirs(os.path.dirname(project_file_out), exist_ok=True)
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
        project_file = self.output_path(filename)

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
        project_path = self.output_path(filename)
        if content_only:
            if os.path.exists(project_path):
                with open(project_path, 'rb') as project:
                    project_content = project.read()
                    project.close()
                return project_content
            else:
                return
        else:
            return project_path

    def list_projects(self, allowed_extensions):
        """Get QGIS projects files in QWC2 scan directory
        :param dict allowed_extensions: list of allowed extensions
        """
        qgis_projects_scan_base_dir = self.config.get("qgis_projects_scan_base_dir")
        projects_filenames = []

        self.logger.debug("QWC2 scan dir path : %s" % qgis_projects_scan_base_dir)
        if qgis_projects_scan_base_dir:
            if os.path.exists(qgis_projects_scan_base_dir):
                for dirpath, dirs, files in os.walk(qgis_projects_scan_base_dir,
                                                    followlinks=True):
                    for filename in files:
                        if Path(filename).suffix[1:] in allowed_extensions:
                            relscanpath = os.path.relpath(dirpath,
                                                          qgis_projects_scan_base_dir)
                            if relscanpath == '.':
                                relscanpath = ''
                            relprojectpath = os.path.join(relscanpath, filename)
                            projects_filenames.append(relprojectpath)
            else:
                return self.error_result("qgis_projects_scan_base_dir is defined but not exists")
        else:
            return self.error_result("qgis_projects_scan_base_dir not defined")

        self.logger.debug('Projects in %s : %s ' % (qgis_projects_scan_base_dir, projects_filenames))

        return projects_filenames

    def clean_empty_dirs(self):
        qgis_projects_scan_base_dir = self.config.get("qgis_projects_scan_base_dir")
        deleted_dirs = []
        if qgis_projects_scan_base_dir:
            for dirpath, dirs, files in os.walk(qgis_projects_scan_base_dir, topdown=False):
                for dir in dirs:
                    fulldirpath = os.path.join(dirpath, dir)
                    reldirpath = os.path.relpath(fulldirpath, qgis_projects_scan_base_dir)
                    if len(os.listdir(fulldirpath)) == 0:
                        try:
                            os.rmdir(fulldirpath)
                            deleted_dirs.append(reldirpath)
                        except Exception as e:
                            if deleted_dirs:
                                msg_deleted_dirs = " but some directories are deleted : %s" % str(deleted_dirs)
                            else:
                                msg_deleted_dirs = ""
                            msg = "Unable to delete directory %s%s" % (fulldirpath, msg_deleted_dirs)
                            self.logger.error(msg)
                            self.logger.debug("Error : %s" % str(e))
                            return self.error_result(msg)

            return self.success_result("Directories deleted : %s" % str(deleted_dirs))
        else:
            return self.error_result("qgis_projects_scan_base_dir not defined")
