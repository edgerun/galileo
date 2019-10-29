#!/bin/bash

if [[ $1 ]]; then
        VERSION="$1"
else
        VERSION=$(grep "version" setup.py | cut -d'=' -f 2 | sed 's/[",]//g')
fi

# registry/group/repository/image
IMAGE=git.dsg.tuwien.ac.at:5005/mc2/galileo/galileo

make clean

docker run --rm --privileged multiarch/qemu-user-static:register --reset

docker build -t ${IMAGE}:${VERSION}-amd64 -f Dockerfile.amd64 .
docker build -t ${IMAGE}:${VERSION}-arm32v7 -f Dockerfile.arm32v7 .

docker push ${IMAGE}:${VERSION}-amd64
docker push ${IMAGE}:${VERSION}-arm32v7

docker manifest create --amend ${IMAGE}:${VERSION} \
	${IMAGE}:${VERSION}-amd64 \
	${IMAGE}:${VERSION}-arm32v7

docker manifest push ${IMAGE}:${VERSION}
