#!/usr/bin/env bash

image=git.dsg.tuwien.ac.at:5005/mc2/galileo/recorder
# registry/group/repository/image
builddir="docker/recorder"

# change into project root
BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT=$(realpath "${BASE}/../..")
cd $PROJECT_ROOT

if [[ $1 ]]; then
    version="$1"
else
    version=$(grep "version" setup.py | cut -d'=' -f 2 | sed 's/[",]//g')
fi

basetag="${image}:${version}"

docker run --rm --privileged multiarch/qemu-user-static:register --reset

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
