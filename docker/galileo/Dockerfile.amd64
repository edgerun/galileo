# syntax=docker/dockerfile:experimental
#############
### build ###
#############
FROM python:3.7-alpine as base

FROM base as builder
RUN apk add --no-cache openssh-client git make gcc musl-dev libffi-dev libressl-dev

# install galileo dependencies
COPY requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

############
### prod ###
############
FROM base
COPY --from=builder  /usr/local /usr/local

RUN mkdir /app
WORKDIR /app

COPY galileo galileo
