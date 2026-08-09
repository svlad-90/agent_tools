# syntax=docker/dockerfile:1.7
#
# Yocto/Poky build environment for Xen product images.

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG NINJA_VERSION=1.11.1
ARG USER_NAME=builder
ARG USER_ID=1000
ARG USER_GID=1000

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    HOME=/home/${USER_NAME}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       bash-completion \
       build-essential \
       ca-certificates \
       chrpath \
       clang \
       cmake \
       cpio \
       curl \
       diffstat \
       file \
       gawk \
       gcc-multilib \
       git \
       git-lfs \
       gperf \
       iputils-ping \
       libegl1-mesa \
       libclang-dev \
       liblz4-tool \
       locales \
       locales-all \
       ninja-build \
       python3 \
       python3-clang \
       python3-pip \
       python3-pexpect \
       python3-venv \
       socat \
       texinfo \
       unzip \
       wget \
       xz-utils \
       zstd \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8

RUN curl -fsSL "https://github.com/ninja-build/ninja/releases/download/v${NINJA_VERSION}/ninja-linux.zip" \
        -o /tmp/ninja-linux.zip \
    && unzip -o /tmp/ninja-linux.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/ninja \
    && test "$(ninja --version)" = "${NINJA_VERSION}" \
    && rm -f /tmp/ninja-linux.zip

RUN pip3 install --upgrade \
        tree-sitter \
        tree-sitter-cpp \
        "git+https://github.com/svlad-90/moulin@main"

RUN mkdir -p /workspace "/home/${USER_NAME}" \
    && chown -R "${USER_ID}:${USER_GID}" /workspace "/home/${USER_NAME}"

WORKDIR /workspace
USER ${USER_ID}:${USER_GID}

RUN git config --global user.name "Isolated Builder" \
    && git config --global user.email "builder@example.com"

CMD ["/bin/bash"]
