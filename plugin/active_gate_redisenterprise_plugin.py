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

    def get_bdb_dict(self):
        """ Return a dictionary for mapping the BDBs to names with usage information """
        bdb_dict = {}
        bdbs = self._api_fetch_json("bdbs", True)
        for i in bdbs:
            # collect the number of shards and multiply by 2 if replicated
            shards_used = i['shards_count']
            if i['replication']:
                shards_used = shards_used * 2
            bdb_dict[i['uid']] = {
                'name': i['name'],
                'limit': i['memory_size'],
                'shards_used': shards_used,
                'endpoints': len(i['endpoints'][-1]['addr']),
            }
        return bdb_dict

    def get_bdb_stats(self, cluster_device, bdb_dict, bdb_devices): 
        """ Collect Enterprise database related stats """
        gauges = [
            'avg_latency', 'avg_latency_max', 'avg_other_latency', 'avg_read_latency', 'avg_write_latency', 'conns'
            'conns', 'egress_bytes', 'evicted_objects', 'expired_objects', 'fork_cpu_system',
            'ingress_bytes', 'listener_acc_latency', 'main_thread_cpu_system', 'main_thread_cpu_system_max', 'memory_limit',
            'no_of_keys', 'other_req', 'read_hits', 'read_misses', 'read_req', 'shard_cpu_system',
            'shard_cpu_system_max', 'total_req', 'total_req_max', 'used_memory', 'write_hits', 'write_misses',
            'write_req', 'bigstore_objs_ram', 'bigstore_objs_flash', 'bigstore_io_reads', 'bigstore_io_writes',
            'bigstore_throughput', 'big_write_ram', 'big_write_flash', 'big_del_ram', 'big_del_flash',
        ]
        # If there are no databases created the following link will 404, so we need to handle this

        try:
            stats = self._api_fetch_json("bdbs/stats/last", True)
            cluster_device.absolute("redis_enterprise.database_count", len(stats))
        except Exception as e:
            cluster_device.absolute("redis_enterprise.database_count", 0)
            self.logger.exception('BDB Fech Error: {}'.format(e))

        for i in stats:
            db_name = bdb_dict[int(i)].get("name")
            for j in stats[i].keys():
                if j in gauges:
                    dev = bdb_devices.get(db_name)
                    dev.absolute('redis_enterprise.{}'.format(j), float(stats[i][j]))

    def get_events(self, device):
        evnts = self._api_fetch_json(
            "logs", True,
            params = {
                "stime": (datetime.now() - timedelta(seconds=int(self.config.get('relative_interval')))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "order": "desc",
                "limit": 100,
            }
        )
        for evnt in evnts:
            msg = {k: v for k, v in evnt.items() if k not in ['time', 'severity']}
            device.report_custom_info_event(
                title = msg.get('type'),
                description = msg.get('description'),
                properties=msg,
            )


    def _api_fetch_json(self, endpoint, allow_redirect, params=None):
        headers_sent = {'Content-Type': 'application/json'}
        url = '{}/v1/{}'.format(self.url, endpoint)
        auth=HTTPBasicAuth(self.user, self.password)
        r = requests.get(
            url,
            auth=auth,
            headers=headers_sent,
            allow_redirects=allow_redirect,
            verify=False,
            params=params,
        )
        if r.status_code != 200:
            self.logger.exception('HTTPS Fech Error: {} returns a {} status: {}'.format(url, r.status_code, r.content))

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
        re_license, re_shards = self.get_license()
        device.absolute("redis_enterprise.license_days", re_license)
        device.absolute("redis_enterprise.license_shards", re_shards)
        bdbs = self.get_bdb_dict()
        bdb_devices = {}
        for i in bdbs:
            bdb_devices[bdbs[i]['name']] = group.create_device(
                '{}:{}'.format(cluster_name, bdbs[i]['name']),
                '{}:{}'.format(cluster_name, bdbs[i]['name']))
        self.get_bdb_stats(device, bdbs, bdb_devices)
        self.get_events(device)