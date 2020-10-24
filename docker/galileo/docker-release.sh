#!/usr/bin/env bash

image=edgerun/galileo
# registry/group/repository/image
builddir="docker/galileo"

# change into project root
BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT=$(realpath "${BASE}/../..")
cd $PROJECT_ROOT

# get version and create basetag
if [[ $1 ]]; then
    version="$1"
else
    version=$(grep "version" setup.py | cut -d'=' -f 2 | sed 's/[",]//g')
fi
basetag="${image}:${version}"

# remove any qemu builder container
docker run --rm --privileged multiarch/qemu-user-static:register --reset

# remove build pollution
make clean-dist

# build all the images
docker build -t ${basetag}-amd64 -f ${builddir}/Dockerfile.amd64 .
docker build -t ${basetag}-arm32v7 -f ${builddir}/Dockerfile.arm32v7 .

# push em all
docker push ${basetag}-amd64 &
docker push ${basetag}-arm32v7 &

wait

export DOCKER_CLI_EXPERIMENTAL=enabled

# create the manifest
docker manifest create ${basetag} \
	${basetag}-amd64 \
	${basetag}-arm32v7

# explicit annotations
docker manifest annotate ${basetag} ${basetag}-arm32v7 --os "linux" --arch "arm" --variant "v7"

# ship it
docker manifest push --purge ${basetag}
