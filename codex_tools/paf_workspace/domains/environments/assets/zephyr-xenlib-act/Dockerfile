FROM catthehacker/ubuntu:act-22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		ca-certificates \
		cmake \
		git \
		gperf \
		ninja-build \
		protobuf-compiler \
		sudo \
		wget \
		xz-utils \
	&& rm -rf /var/lib/apt/lists/*
