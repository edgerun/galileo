Galileo: MC2 Experimentation Environment
========================================

This project allows users to define operational experiments for the MC2 (Mini Compute Cluster),
and interact with the experimentation environment during runtime.
The experimentation environment consists of two major components a user can interact with:
the experiment controller and the routing table.
The experiment controller can spawn clients that generate load on client hosts, and controll the amount of load they generate.
The routing table defines to which cluster node a service request is sent to.

Build
-----

Create and activate a new virtual environment

    virtualenv .venv
    source .venv/bin/activate

Install requirements

    pip install -r requirements.txt

If you have symmetry locally in the parent folder, link it via

    pip install -e ../symmetry


Preparing the Example Application
---------------------------------

We prepare the cluster with an example application. Specifically a image classification service.

Run the mxnet-model-server as a Docker container named 'mms', exposed on port 8080.
For example, to start mxnet-model-server with models squeezenet and alexnet, run the following command on a cluster node:

    docker run -itd --name mms -p 8080:8080 -p 8081:8081 awsdeeplearningteam/mxnet-model-server:1.0.0-mxnet-cpu mxnet-model-server --start \
    --models squeezenet=https://s3.amazonaws.com/model-server/models/squeezenet_v1.1/squeezenet_v1.1.model,alexnet=https://s3.amazonaws.com/model-server/model_archive_1.0/alexnet.mar


Prepare the Experiment Client Hosts
-----------------------------------

The devices hosting the clients that generate load need to run the experiment controller host application.

    python -m galileo.cli.host --redis redis://graviton --trace-logging 'redis'

The `--redis` option takes as argument the URL to the Redis instance used for communication and data storage.


Run the Routing Table CLI
-------------------------

The symmetry routing table CLI allows the user to set load balancing policies.

```
(.venv) pi@graviton:~/mc2/symmetry $ python -m symmetry.cli.rtable
rtbl> help

Documented commands (type help <topic>):
========================================
clear  date  help  set  sleep  source  unset

Undocumented commands:
======================
echo  exit  flush  info  list  updates

rtbl> 
rtbl> help set

Usage: set service hosts weights
  
  Set a routing record. For example
  
  set squeezenet heisenberg:8080,einstein:8080 1,2
  
  will set two hosts for the service squeezenet that are balanced at a ratio of 1 to 2
  
parameters:
  service: the service name
  hosts: a comma separated list of hosts
  weights: a comma separated list of weights

rtbl> 
```


Run the Experiment Controller
-----------------------------

```
exp> hel(.venv) pi@graviton:~/mc2/galileo $ python -m galileo.cli.controller
Welcome to the interactive experiment controller Shell.
exp> help

Documented commands (type help <topic>):
========================================
close  date  help  hosts  info  ping  rps  sleep  source  spawn

Undocumented commands:
======================
clients  echo  exit

exp> help spawn

Usage: spawn host_pattern service [num]
  
  Spawn a new client for the given service on the given host.
  
parameters:
  host_pattern: the host name or pattern (e.g., 'pico1' or 'pico[0-9]')
  service: the service name
  num: the number of clients

exp> help rps

Usage: rps host_pattern service rps
```
