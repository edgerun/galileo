#!/bin/bash

envfile="$(dirname $(realpath $0))/mysql.env"
source $envfile

exec gunicorn -w 4 --preload -b 0.0.0.0:5001 \
        -c galileo/webapp/gunicorn.conf.py \
        'galileo.webapp.app:start()' "$@"
