from ruxit.api.base_plugin import RemoteBasePlugin
from ruxit.api.data import PluginProperty
import logging
from datetime import datetime, timedelta
from enum import Enum
import requests
from requests.auth import HTTPBasicAuth


logger = logging.getLogger(__name__)

class RemoteRedisEnterprisePlugin(RemoteBasePlugin):

    class State(Enum):
        DOWNTIME = 0
        MAINTENANCE = 1
        WORKING = 2

    def initialize(self, **kwargs):
        self.url = self.config.get("url", "http://127.0.0.1:9443")
        self.user = self.config.get("auth_user", "admin")
        self.password = self.config.get("auth_password", "admin")
        self.alert_interval = self.config.get("alert_interval", 10)
        self.event_interval = self.config.get("event_interval", 3)
        self.relative_interval = self.config.get("relative_interval", 60)
        self.state_interval = self.config.get("state_interval", 60)

        self.alert_iterations = 0
        self.event_iterations = 0
        self.relative_iterations = 0
        self.absolute_iterations = 0
        self.state_iterations = 0

        self.current_entries = 1
        self.archived_entries = 0

    ###############################################################################################################
    def get_cluster_name(self):
        """ Pull cluster name from the API """
        info = self._api_fetch_json("cluster", False)
        return(info.get("name"))

    def get_license(self):
        """ Collect Enterprise License Information """
        stats = self._api_fetch_json("license", True)
        expire = datetime.strptime(stats['expiration_date'], "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.now()
        days = int((expire - now).days)
        shards = stats.get('shards_limit')
        return(days, shards)

    def _api_fetch_json(self, endpoint, allow_redirect):
        headers_sent = {'Content-Type': 'application/json'}
        url = '{}/v1/{}'.format(self.url, endpoint)
        auth=HTTPBasicAuth(self.user, self.password)
        r = requests.get(
            url,
            auth=auth,
            headers=headers_sent,
            allow_redirects=allow_redirect,
            verify=False,
        )
        if r.status_code != 200:
            logging.exception('HTTPS Fech Error: {} returns a {} status: {}'.format(url, r.status_code, r.content))

        return r.json()

    ###############################################################################################################
    # Query needs to go last!!

    def query(self, **kwargs):
        group = self.topology_builder.create_group(
            identifier="RedisEnterprise",
            group_name="ActiveGate RedisEnterprise Clusters"
            )
        cluster_name = self.get_cluster_name()
        device = group.create_device(cluster_name, cluster_name)
        re_license, re_shards = get_license()
        device.absolute("redis_enterprise.license_days", re_license)
        device.absolute("redis_enterprise.license_shards", re_shards)
