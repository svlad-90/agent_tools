FROM catthehacker/ubuntu:act-22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		ca-certificates \
		clang \
		cmake \
		git \
		gperf \
		libclang-dev \
		ninja-build \
		protobuf-compiler \
		python3 \
		python3-clang \
		python3-pip \
		python3-venv \
		sudo \
		wget \
		xz-utils \
	&& rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade \
		tree-sitter \
		tree-sitter-cpp
