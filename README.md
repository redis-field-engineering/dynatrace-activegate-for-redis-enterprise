## Redis Enterprise ActiveGate Extension

### Prerequisites

1. Working [Dynatrace Install](https://www.dynatrace.com/support/help/setup-and-configuration/)
2. Working [ActiveGate Instance](https://www.dynatrace.com/support/help/setup-and-configuration/dynatrace-activegate/)
3. Login to a Redis Enterprise Cluster


### Architecture

![architecture  diagram](docs/architecture.png)


### Setup Account

#### Setup a read only user Account

Login to your Redis Entprise Instance and click on Access Control

![create account](docs/account_1.png)


#### Add a new user account with Cluster View Permissions

![create account](docs/account_2.png)



### SSH into your ActiveGate node

#### Install the Zip file

```
cd /tmp/ 
wget https://redislabs-field-engineering.s3.us-west-1.amazonaws.com/private-preview/active_gate_redisenterprise_plugin/custom.remote.python.redisenterprise.zip
sudo mv /tmp/custom.remote.python.redisenterprise.zip /opt/dynatrace/remotepluginmodule/plugin_deployment/custom.remote.python.redisenterprise.zip
```

#### Restart the service

```
sudo service dynatracegateway restart
```

### Install and setup custom extension

#### On Dynatrace go into Settings/Monitoring/Monitored Technologies/Custom Extensions Tab

![setup mon](docs/extension_1.png)

#### Click on Upload Extensions

![upload_1](docs/upload_1.png)

#### Upload Extension and click on the extension to configure the endpoint

![endpoint config](docs/config_endpoint.png)

#### Check to ensure the Status is OK

![endpoint running](docs/running_endpoint.png)

#### Under Infrastructuer Click on Technology and Proceses

![Tech Groups](docs/technology_group.png)

#### Select REDIS_ENTERPRISE

![Device list](docs/devices.png)

#### Select Active Gate RedisEnterprise Clusters

![Cluster Stats](docs/cluster_stats.png)

The cluster level information is the FQDN of the cluster and the database level information is on the FQDN:DB_NAME devices

#### Events

![Events](docs/events.png)

#### Cluster Stats
![Cluster Events](docs/cluster_stats.png)

#### DB Stats
![DB Stats](docs/bdb_stats.png)
