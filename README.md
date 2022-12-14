QWC Project publisher service
=================

API documentation:

    http://localhost:5100/api/

This service can be used with [Project Publisher QGIS Plugin](https://github.com/naub1n/QGIS_Project_Publisher) to easily publish project.


Configuration
-------------

The static config files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

### JSON config

* [JSON schema](schemas/qwc-project-publisher-service.json)
* File location: `$CONFIG_PATH/<tenant>/projectPublisherConfig.json`

Example:
```json
{
  "$schema": "https://raw.githubusercontent.com/naub1n/qwc-project-publisher-service/master/schemas/qwc-project-publisher-service.json",
  "service": "publisher",
  "config": {
    "qgis_projects_scan_base_dir": "/data/scan", 
    "publisher_role_name": "publishers",
    "config_generator_service_url": "http://qwc-config-service:9090",
    "update_config_enable": true
  }
}
```

`publisher_role_name` is role required to publish a project.

`update_config_enable` allow qwc_project_publisher_service to run config_generator_service after a user publish or delete project.

### Environment variables

| Variable                   | Description                                   |  Default        |
|----------------------------|-----------------------------------------------|-----------------|
| `AUTH_REQUIRED`            | Enable authentication. If `False`, all users can use api.</br>If `True`, only users in `publisher_groups_name` can use api.| `False`         |



Usage
-----

Publish a project :

`curl -v -X POST "http://127.0.0.1:5100/publish?filename=myproject.qgs"`

-optional : You can add `filename` parameter to specify output file name in QWC2 scan base dir

Get a project (get .qgs project content (xml)) :

`curl -v -X GET "http://127.0.0.1:5100/getproject?filename=myproject.qgs"`

Get a project (download .qgs project) :

`curl -v -X GET "http://127.0.0.1:5100/getproject?filename=myproject.qgs&content_only=false"`

Delete a project :

`curl -v -X DELETE "http://127.0.0.1:5100/deleteproject?filename=myproject.qgs"`

Get projects list :

`curl -v -X GET "http://127.0.0.1:5100/listprojects?"`

N.B. : If `AUTH_REQUIRED` = `True`, X-CSRF-TOKEN header and cookies are required.</br>
Add `-H "X-CSRF-TOKEN: xxxxxxxx" -b cookiefilepath` to cURL command.<br>
Use cURL POST command to login in.<br>
Look at `POST_PARAM_LOGIN` in https://github.com/qwc-services/qwc-db-auth

Development
-----------

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements.txt

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

    export CONFIG_PATH=../qwc-docker/volumes/config

Configure environment:

    echo FLASK_ENV=development >.flaskenv

Start local service:

    python server.py 
