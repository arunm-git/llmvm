#!/bin/bash

if [[ -z "$OPENAI_API_KEY" && -z "$ANTHROPIC_API_KEY" ]]; then
    echo "Error: Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be set in your environment."
    exit 1
fi

if [[ -z "$SERPAPI_API_KEY" ]]; then
    echo "Warning: SERPAPI_API_KEY is not set in your environment. To search anything you need this API key. Its free!"
fi

set -o errexit -o pipefail -o noclobber -o nounset

CONTNAME=llmvm-container
IMGNAME=llmvm-image

# usually /home/llmvm/llmvm
BUILDDIR=$(cd $(dirname "$0"); pwd)

echo_usage() {
    echo "usage: docker.sh -- helper script to manage building and deploying llmvm into docker containers"
    echo
    echo "  -b (build image from Dockerfile)"
    echo "  -c (clean docker [remove all images named llmvm-image and containers named llmvm-container])"
    echo "  -f (force clean docker [remove all images and containers, and build cache])"
    echo "  -r (run container)"
    echo "  -s (sync code to running container)"
    echo "  -a (sync all files in llmvm to running container)"
    echo "  -r (run container and ssh into it)"
    echo "  -g (go: clean, build, run and ssh into container)"
    echo "  -n|--container_name <name> (default: llmvm-container)"
    echo "  -i|--image_name <name> (default: llmvm-image)"
    echo ""
}

b=n c=n f=n r=n s=n a=n g=n

while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--build)
      b=y
      shift # past argument
      ;;
    -c|--clean)
      c=y
      shift # past argument
      ;;
    -f|--force)
      f=y
      shift # past argument
      ;;
    -r|--run)
      r=y
      shift # past argument
      ;;
    -g|--go)
      g=y
      shift # past argument
      ;;
    -s|--sync)
      s=y
      shift
      ;;
    -a|--sync_all)
      a=y
      shift
      ;;
    -i|--image_name)
      IMGNAME="$2"
      shift
      shift
      ;;
    -n|--container_name)
      CONTNAME="$2"
      shift
      shift
      ;;
    -*|--*)
      echo "Unknown option $1"
      echo_usage
      exit 1
      ;;
    *)
      POSITIONAL_ARGS+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done

# handle non-option arguments
if [[ $# -ne 1 ]]; then
    echo_usage
fi

clean() {
    echo "Cleaning images and containers"
    if [ -n "$(docker ps -f name=$CONTNAME -q)" ]; then
        echo "Container $CONTNAME already running, removing anyway"
        docker rm -f $CONTNAME
    fi

    if [ -n "$(docker container ls -a | grep $CONTNAME)" ]; then
        echo "Container $CONTNAME exists, removing"
        docker rm -f $CONTNAME
    fi

    if [ -n "$(docker image ls -a | grep $IMGNAME)" ]; then
        echo "Image $IMGNAME exists, removing"
        docker image prune -f
        docker image rm -f $IMGNAME
    fi
}

force_clean() {
    echo "Cleaning all build cache"
    docker builder prune --force
}

run() {
    echo "running container $CONTNAME with this command:"
    echo ""
    echo " $ docker run --name $CONTNAME -ti -p 2222:22 -p starting -p  8888:8000 --tmpfs /run --tmpfs /run/lock -v /lib/modules:/lib/modules:ro -d $IMGNAME"
    echo ""

    if [ ! "$(docker image ls -a | grep $IMGNAME)" ]; then
      echo "cant find image named $IMGNAME to run"
      exit 1
    fi

    docker run \
        --name $CONTNAME \
        -ti \
        -p 2222:22 \
        -p 8888:8000 \
        --tmpfs /run \
        --tmpfs /run/lock \
        -v /lib/modules:/lib/modules:ro \
        -d $IMGNAME

    echo ""
    # echo ssh into container via ssh llmvm:llmvm@$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTNAME)
    echo "container: $CONTNAME"
    echo "ip address: $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTNAME)"
    echo "ssh'ing into container via ssh llmvm@localhost -p 2222, password is 'llmvm'"
    echo ""
    ssh llmvm@localhost -p 2222
}

build() {
    echo "building llmvm into image $IMGNAME and container $CONTNAME"
    echo ""
    echo "DOCKER_BUILDKIT=1 docker buildx build --build-arg OPENAI_API_KEY=$OPENAI_API_KEY --build-arg ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY --build-arg SEC_API_KEY=$SEC_API_KEY --build-arg SERPAPI_API_KEY=$SERPAPI_API_KEY -f $BUILDDIR/Dockerfile --platform linux/amd64 -t $IMGNAME --force-rm=true --rm=true $BUILDDIR"
    echo ""
    DOCKER_BUILDKIT=1 docker buildx build --build-arg OPENAI_API_KEY=$OPENAI_API_KEY --build-arg ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY --build-arg SEC_API_KEY=$SEC_API_KEY --build-arg SERPAPI_API_KEY=$SERPAPI_API_KEY -f $BUILDDIR/Dockerfile --platform linux/amd64 -t $IMGNAME --force-rm=true --rm=true $BUILDDIR
}

sync() {
    echo "syncing code directory to $CONTNAME"
    echo ""
    CONTID="$(docker ps -aqf name=$CONTNAME)"
    if [[ $CONTID == "" ]]; then
      echo "cant find running container that matches name $CONTNAME"
      exit 1
    fi
    echo "container id: $CONTID"
    echo " $ rsync -e 'docker exec -i' -av --delete $BUILDDIR/ $CONTID:/home/llmvm/llmvm/ --exclude='.git' --filter=\"dir-merge,- .gitignore\""
    echo ""
    rsync -e 'docker exec -i' -av --delete $BUILDDIR/ $CONTID:/home/llmvm/llmvm/ --exclude='.git' --filter="dir-merge,- .gitignore"
}

sync_all() {
    echo "syncing entire llmvm directory to $CONTNAME"
    echo ""
    CONTID="$(docker ps -aqf name=$CONTNAME)"
    if [[ $CONTID == "" ]]; then
      echo "cant find running container that matches name $CONTNAME"
      exit 1
    fi
    echo "container id: $CONTID"
    echo " $ rsync -e 'docker exec -i' -av $BUILDDIR/ $CONTID:/home/llmvm/llmvm/ --exclude='.git'"
    echo ""
    rsync -e 'docker exec -i' -av --delete $BUILDDIR/ $CONTID:/home/llmvm/llmvm/ --exclude='.git'
}

echo "build: $b, clean: $c, run: $r, force: $f, sync: $s, sync_all: $a, go: $g, image_name: $IMGNAME, container_name: $CONTNAME"

if [[ $b == "y" ]]; then
    build
fi
if [[ $c == "y" ]]; then
    clean
fi
if [[ $f == "y" ]]; then
    clean; force_clean
fi
if [[ $r == "y" ]]; then
    run
fi
if [[ $s == "y" ]]; then
    sync
fi
if [[ $a == "y" ]]; then
    sync_all
fi
if [[ $g == "y" ]]; then
    clean; build; run
fi
