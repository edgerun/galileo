Galileo: A framework for distributed load testing experiments
=============================================================

[![PyPI Version](https://badge.fury.io/py/edgerun-galileo.svg)](https://badge.fury.io/py/edgerun-galileo)
[![Build Status](https://travis-ci.org/edgerun/galileo.svg?branch=master)](https://travis-ci.org/edgerun/galileo)
[![Coverage Status](https://coveralls.io/repos/github/edgerun/galileo/badge.svg?branch=master)](https://coveralls.io/github/edgerun/galileo?branch=master)

This project allows users to define, run, and interact with distributed load testing experiments for distributed
web-service-oriented systems.
Galileo consists of two major components a user can interact with:
the experiment controller shell and the galileo dashboard.
The experiment controller can spawn emulated clients on workers, and control the amount of load they generate.
Furthermore, a user can interact with the service routing table shell to control to which cluster node a service request
is sent to.

Build
-----

Create a new virtual environment and install all dependencies

    make venv

#### Docker

To create a Docker image that can run galileo components, run 

    make docker
    
To create a arm32v7 Docker image that can run galileo components, run
    
    make docker-arm

Start a worker with

    cd docker/galileo-worker
    docker-compose up

Compose files for arm32v7 are located in 
    
    docker/arm
    
Start a local dev environment, including: API, ExperimentDaemon, 1 worker, redis and database:

    cd docker/dev
    docker-compose up
 
Preparing the Example Application
---------------------------------

We prepare the cluster with an example application. Specifically a image classification service.

Run the mxnet-model-server as a Docker container named 'mms', exposed on port 8080.
For example, to start mxnet-model-server with models squeezenet and alexnet, run the following command on a cluster node:

    docker run -itd --name mms -p 8080:8080 -p 8081:8081 awsdeeplearningteam/mxnet-model-server:1.0.0-mxnet-cpu mxnet-model-server --start \
    --models squeezenet=https://s3.amazonaws.com/model-server/models/squeezenet_v1.1/squeezenet_v1.1.model,alexnet=https://s3.amazonaws.com/model-server/model_archive_1.0/alexnet.mar


Prepare the Experiment Worker Hosts
-----------------------------------

The devices hosting the workers that generate load need to run the experiment controller host application.

    bin/run worker --logging=INFO

All runtime parameters are controlled via `galileo_*` environment variables. Check `docker/galileo-worker/worker.env` for some examples.

All environment variables, that start with `galileo_`, can be used as worker label when creating a client group.

I.e., if you start a worker process with the env variable `galileo_zone=A`, you can spawn a client group that contains only 
workers with this labels as follows:

    g.spawn('service',worker_labels={'galileo_zone': 'A'})


Run the Experiment Controller Shell
-----------------------------------

```
(.venv) pi@graviton:~/edgerun/galileo $ bin/run shell
                                   __  __
 .-.,="``"=.          ____ _____ _/ (_) /__  ____
 '=/_       \        / __ `/ __ `/ / / / _ \/ __ \
  |  '=._    |      / /_/ / /_/ / / / /  __/ /_/ /
   \     `=./`.     \__, /\__,_/_/_/_/\___/\____/
    '=.__.=' `='   /____/


Welcome to the galileo shell!

Type `usage` to list available functions

galileo> usage
the galileo shell is an interactive python shell that provides the following commands

Commands:
  usage         show this message
  env           show environment variables
  pwd           show the current working directory

Functions:
  sleep         time.sleep wrapper

Objects:
  g             Galileo object that allows you to interact with the system
  show          Prints runtime information about the system to system out
  exp           Galileo experiment
  rtbl          Service routing table

Type help(<function>) or help(<object>) to learn how to use the functions.

```



Configure the routing table
---------------------------

The `rtbl` object in the shell allows you to set load balancing policies. Run `help(rtbl)` in the galileo shell.
Here is an example of how to set a record for the service `myservice`.
```
galileo> rtbl.set('myservice', ['host1:8080', 'host2:8080'], [1,2])
RoutingRecord(service='myservice', hosts=['host1:8080', 'host2:8080'], weights=[1, 2])
galileo> rtbl
+---------------------------+----------------------+-----------+
| Service                   |                Hosts |   Weights |
+---------------------------+----------------------+-----------+
| myservice                 |           host1:8080 |       1.0 |
|                           |           host2:8080 |       2.0 |
+---------------------------+----------------------+-----------+

```

Run the Experiment Daemon
-------------------------

---

**FIXME: THIS IS OUTDATED**  

---

The experiment daemon continuously reads from the blocking redis queue `galileo:experiments:instructions`.
After receiving instructions, the controller will execute the commands and record the telemetry data
published via Redis. At the end the status of the experiment will be set to 'FINISHED' and the traces,
that were saved in the db by the clients, will be updated to reference the experiment.

Example Redis command to inject a new experiment (where `exphost` is the hostname of the experiment host):

    LPUSH galileo:experiments:instructions '{"instructions": "spawn exphost squeezenet 1\nsleep 2\nrps exphost squeezenet 1\nsleep 5\nrps exphost squeezenet 0\nsleep 2\nclose exphost squeezenet"}'

you can also specify `exp_id`, `creator`, and `name`, otherwise some generated/standard values will be used.

You can change the database used to store the experiment data via the env `galileo_expdb_driver` (`sqlite` or `mysql`).
To write the changes into MySQL (or MariaDB), set the following environment variables:
`galileo_expdb_mysql_host`,
`galileo_expdb_mysql_port`,
`galileo_expdb_mysql_db`,
`galileo_expdb_mysql_user`,
`galileo_expdb_mysql_password`

You can create a mariadb docker instance with:

    ./bin/run-db.sh

Then execute the daemon with:

    python -m galileo.cli.experimentd

Or run the script, which exports the mariadb setup from the docker container (add `--logging DEBUG` for output)

    ./bin/experimentd-mysql.sh


Run the Galileo REST API
------------------------

Serve the app with gunicorn

    gunicorn -w 4 --preload -b 0.0.0.0:5001 \
        -c galileo/webapp/gunicorn.conf.py \
        galileo.webapp.wsgi:api
