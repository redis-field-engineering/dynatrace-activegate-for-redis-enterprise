## Redis Enterprise Active Gate Plugin Troubleshooting Guide

The plugin collects data from the [Redis Enterprise API](https://storage.googleapis.com/rlecrestapi/rest-html/http_rest_api.html) and submits that data to Dynatrace via Active Gate

All commands below use the redis.cluster.fqdn as the Redis Enterprise cluster fully qualified domain name and all commands should be run on the Active Gate node.

### Check Cluster DNS Resolution

Redis Enterprise recommended configuration involves using [DNS for service discovery](https://docs.redis.com/latest/rs/installing-upgrading/configuring/cluster-dns/)

If you are having issues configuring DNS the [Zone Generator](http://dnszonegenerator.demo-azure.redislabs.com/) is available and includes step-by-step instructions and troubleshooting tips.


Example command to test resolution:

```
$ dig ns redis.cluster.fqdn

# should return 
;; ANSWER SECTION:
redis.cluster.fqdn.	3581 IN	NS	ns1.redis.cluster.fqdn.
redis.cluster.fqdn.	3581 IN	NS	ns2.redis.cluster.fqdn.
redis.cluster.fqdn.	3581 IN	NS	ns3.redis.cluster.fqdn.

```

### Check API Connectivity

From the active gate node you can check using telnet.  You should see "Connected" message

```
$ telnet redis.cluster.fqdn 9443
Trying 10.10.7.54...
Connected to redis.cluster.fqdn.
Escape character is '^]'.
^]
telnet> quit
Connection closed.
```

or you can test using openssl and should see a "CONNECTED"

```
$ openssl s_client -connect  redis.cluster.fqdn:9443
CONNECTED(00000003)
<snip>
```

### Check API Credentials

It is possible to check the credentials using curl

```
 curl  -vk -u login@example.com:MYPASSWORD  https://redis.cluster.fqdn:9443/v1/license


# Sucessful will return
< HTTP/1.1 200 OK

# Unsucessful will return
< HTTP/1.1 401 Unauthorized

```

### Check API Cluster Leadership

Redis Enterprise will resolve only to the cluster leader if DNS is properly configured.  If an API request goes to another node it will return a HTTP 307 code.


```
curl  -vk -u login@example.com:MYPASSWORD  https://redis.cluster.fqdn:9443/v1/cluster


# Sucessful will return
< HTTP/1.1 200 OK

# Unsucessful will return
< HTTP/1.1 307 Temporary Redirect
< location: https://10.0.77.68:9443/v1/cluster
```

If you are running behind a load balancer, it is possible to add every cluster node as a separate endpoint in Active Gate and only the cluster leader will respond.


### Check Redis Enterprse Plugin Logs

By default these are written to

```
/var/log/dynatrace/supportarchive/remotepluginmodule/log/remoteplugin/custom.remote.python.redisenterprise/RemoteRedisEnterprisePlugin.log
```

If you are connecting to an non-cluster leader node you should see :

```
2022-02-09 18:45:01.258 UTC INFO    [Python][9464087476285887869][notmaster][139765273847552][ThreadPoolExecutor-0_0] - [query] Data Collection Error: https://ns1.redis.cluster.fqdn:9443/ is not the cluster leader node. No metrics or event will be collected
```


### Check Active-Gate Logs

By default Dynatrace logs are written to:

```
/var/log/dynatrace
```

### Getting further help
