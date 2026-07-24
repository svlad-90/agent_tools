FROM ubuntu:24.04

ARG ACT_VERSION=0.2.89
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		ca-certificates \
		curl \
		docker.io \
		git \
		python3 \
		python3-venv \
		tar \
	&& rm -rf /var/lib/apt/lists/*

RUN set -eux; \
	case "${TARGETARCH:-amd64}" in \
		amd64) act_arch=x86_64 ;; \
		arm64) act_arch=arm64 ;; \
		*) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
	esac; \
	curl -fsSL "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_${act_arch}.tar.gz" \
		-o /tmp/act.tar.gz; \
	tar -C /usr/local/bin -xzf /tmp/act.tar.gz act; \
	rm -f /tmp/act.tar.gz; \
	act --version

WORKDIR /work
