# syntax=docker/dockerfile:experimental
#############
### build ###
#############
FROM python:3.7-alpine as base

FROM base as builder
RUN apk add --no-cache openssh-client git make gcc musl-dev libffi-dev libressl-dev

# Make ssh dir
RUN mkdir /root/.ssh/
RUN ssh-keyscan -t rsa git.dsg.tuwien.ac.at > ~/.ssh/known_hosts

# clone, install and build symmetry
RUN --mount=type=ssh git clone ssh://git@git.dsg.tuwien.ac.at/mc2/symmetry.git /symmetry
RUN pip install -r /symmetry/requirements.txt
RUN make -C /symmetry/ dist
RUN pip install -e /symmetry/

# install galileo dependencies
COPY requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

############
### prod ###
############
FROM base
COPY --from=builder  /usr/local /usr/local
COPY --from=builder  /symmetry /symmetry

RUN mkdir /app
WORKDIR /app

COPY galileo galileo

CMD ["python", "-u", "-m", "galileo.cli.worker"]
