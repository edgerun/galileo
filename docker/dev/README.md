Galileo dev deployment
======================

Build the image locally by running in the root directory:

    docker build -f docker/galileo/Dockerfile.amd64 -t galileo/galileo .

Then run

    cd docker/dev
    docker-compose up -d

You should see four containers

     % docker-compose ps
              Name                         Command               State           Ports         
    -------------------------------------------------------------------------------------------
    dev_galileo-api_1           gunicorn -w 2 --preload -b ...   Up      0.0.0.0:7701->5001/tcp
    dev_galileo-experimentd_1   python -u -m galileo.cli.e ...   Up                            
    dev_redis_1                 docker-entrypoint.sh redis ...   Up      0.0.0.0:6379->6379/tcp
    dev_worker_1                python -u -m galileo.cli.w ...   Up       

Usage
-----

You can start a galileo shell by running in the root directory

    python -m galileo.cli.shell

Check out the root `README.md` for infos on how to use galileo.
