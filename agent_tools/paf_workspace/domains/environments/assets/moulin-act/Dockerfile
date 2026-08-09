FROM catthehacker/ubuntu:act-22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		build-essential \
		ca-certificates \
		clang \
		cmake \
		git \
		libclang-dev \
		make \
		ninja-build \
		python3 \
		python3-clang \
		python3-pip \
		python3-pygit2 \
		python3-venv \
		ssh \
		sudo \
		xxd \
	&& rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip \
	&& pip3 install \
		flake8 \
		gitlint \
		mypy \
		pyaml \
		pytest \
		tree-sitter \
		tree-sitter-cpp \
		types-PyYAML \
		west
