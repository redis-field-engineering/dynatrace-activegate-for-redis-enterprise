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
            'avg_latency', 'avg_latency_max', 'avg_other_latency', 'avg_read_latency', 'avg_write_latency',
            'conns', 'egress_bytes', 'evicted_objects', 'expired_objects', 'fork_cpu_system',
            'ingress_bytes', 'listener_acc_latency', 'main_thread_cpu_system', 'main_thread_cpu_system_max',
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

        cluster_total_req = 0

        for i in stats:
            db_name = bdb_dict[int(i)].get("name")
            dev = bdb_devices.get(db_name)
            dev.absolute('redis_enterprise.endpoints', float(bdb_dict[int(i)].get("endpoints")))
            dev.absolute('redis_enterprise.shard_count', float(bdb_dict[int(i)].get("shards_used")))
            dev.absolute('redis_enterprise.memory_limit', float(bdb_dict[int(i)].get("limit")))

            # Dynatrace does not support derived stats so we need to calculate two here ourselves
            # ensure we don't divide by zero here
            if stats[i]['read_hits'] + stats[i]['read_misses'] + stats[i]['write_hits'] + stats[i]['write_misses'] < 1.0:
                cache_hit_rate = 0.0
            else:
                cache_hit_rate = (
                    stats[i]['read_hits'] + stats[i]['write_hits']
                    ) / (
                        stats[i]['read_hits']+stats[i]['read_misses']+stats[i]['write_hits']+stats[i]['write_misses'])

            dev.absolute("redis_enterprise.cache_hit_rate", cache_hit_rate)
            dev.absolute("redis_enterprise.memory_usage_percent", float(stats[i]['used_memory'] / bdb_dict[int(i)]['limit']))

            total_req = stats[i].get('total_req')
            if total_req is not None:
                cluster_total_req += float(total_req)
            for j in stats[i].keys():
                if j in gauges:
                    dev.absolute('redis_enterprise.{}'.format(j), float(stats[i][j]))


        # send the total as well
        cluster_device.absolute("redis_enterprise.cluster_total_req", cluster_total_req)

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

    def  get_nodes(self, device):
        stats = self._api_fetch_json(
            "nodes",
            True,
        )
        res = {'total_node_cores': 0, 'total_node_memory': 0, 'total_node_count': 0, 'total_active_nodes': 0}
        for i in stats:
            res['total_node_cores'] += i['cores']
            res['total_node_memory'] += i['total_memory']
            res['total_node_count'] += 1
            if i['status'] == "active":
                res['total_active_nodes'] += 1
        for x in res.keys():
            device.absolute('redis_enterprise.{}'.format(x), float(res[x]))


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
        bdbs = self.get_bdb_dict()
        bdb_devices = {}
        used_shards_total = 0
        for i in bdbs:
            used_shards_total += int(bdbs[i]['shards_used'])
            bdb_devices[bdbs[i]['name']] = group.create_device(
                '{}:{}'.format(cluster_name, bdbs[i]['name']),
                '{}:{}'.format(cluster_name, bdbs[i]['name']))

        device.absolute("redis_enterprise.license_days", max(re_license, 0))
        device.absolute("redis_enterprise.license_shards", re_shards)
        device.absolute("redis_enterprise.shards_used", used_shards_total)

        self.get_bdb_stats(device, bdbs, bdb_devices)
        self.get_events(device)
        self.get_nodes(device)