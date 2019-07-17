#!/bin/sh

docker run -d -p 3307:3306 --rm --name mariadb -e MYSQL_ROOT_PASSWORD=password -e MYSQL_USER=galileo -e MYSQL_PASSWORD=galileo -e MYSQL_DATABASE=galileo mariadb

