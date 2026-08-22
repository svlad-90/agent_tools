FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
	VIRTUAL_ENV=/opt/agent-workspace-tests-venv \
	PATH=/opt/agent-workspace-tests-venv/bin:${PATH}

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		ca-certificates \
		gir1.2-gtk-3.0 \
		gir1.2-vte-2.91 \
		git \
		python3 \
		python3-gi \
		python3-pip \
		python3-pytest \
		python3-tk \
		python3-venv \
	&& rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages "${VIRTUAL_ENV}" \
	&& pip3 install --upgrade \
		jsonschema \
		pytest \
		PyYAML \
		tiktoken \
		tree-sitter \
		tree-sitter-cpp

WORKDIR /workspace
