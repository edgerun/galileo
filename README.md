Galileo: MC2 Experimentation Environment
========================================

This project allows users to define operational experiments for the MC2 (Mini Compute Cluster),
and interact with the experimentation environment during runtime.
Galileo consists of two major components a user can interact with:
the experiment controller shell and the galileo dashboard.
The experiment controller can spawn emulated clients on workers, and control the amount of load they generate.
Furthermore, a user can interact with Symmetry's routing table shell to control to which cluster node a service request
is sent to.

Build
-----

Create and activate a new virtual environment

    virtualenv .venv
    source .venv/bin/activate

Install requirements

    pip install -r requirements.txt

If you have symmetry locally in the parent folder, link it via

    pip install -e ../symmetry

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

    python -m galileo.cli.worker

All runtime parameters are controlled via `galileo_*` environment variables. Check `docker/galileo-worker/worker.env` for some examples.

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


Run the Experiment Controller Shell
-----------------------------------

```
(.venv) pi@graviton:~/mc2/galileo $ python -m galileo.cli.shell

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
  
  Spawn a new client for the given service on the given worker host.
  
parameters:
  host_pattern: the host name or pattern (e.g., 'pico1' or 'pico[0-9]')
  service: the service name
  num: the number of clients

exp> help rps

Usage: rps host_pattern service rps
```

Run the Experiment Daemon
-------------------------

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


Run the Galileo Dashboard
-------------------------
#### Run Dashboard with npm and ng
Take a look at the README in `galileo-dashboard`. 


#### Run Dashboard with Docker 
Run in `galileo-dashboard`:

    docker build -t galileo/galileo-dashboard-dev .
        
After building run the container with:

    docker run -v ${PWD}:/app -v /app/node_modules -p 4201:4200 --name galileo-dashboard galileo/galileo-dashboard-dev
        
Making changes in the app will hot-reload the app.

If you are done developing, stop the container with
    
    docker stop galileo-dashboard-dev
    
You can restart the container later with

    docker start galileo-dashboard-dev
    
and attach your terminal to see the build output with

    docker attach galileo-dashboard-dev
    
 

To make a production build and serve the app with nginx execute:

    docker build -f Dockerfile-prod -t galileo/galileo-dashboard  .
  