#!/bin/bash

envfile="$(dirname $(realpath $0))/mysql.env"
source $envfile

exec python -m galileo.cli.experimentd "$@"
