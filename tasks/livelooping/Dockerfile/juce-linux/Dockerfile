FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        clang \
        cmake \
        g++ \
        git \
        ladspa-sdk \
        libasound2-dev \
        libclang-dev \
        libfontconfig1-dev \
        libfreetype-dev \
        libjack-jackd2-dev \
        libx11-dev \
        libxcomposite-dev \
        libxcursor-dev \
        libxext-dev \
        libxi-dev \
        libxinerama-dev \
        libxrandr-dev \
        libxrender-dev \
        ninja-build \
        pkg-config \
        python3 \
        python3-clang \
        python3-dev \
        python3-pip \
        python3-venv \
    && python3 -m venv /opt/workspace-tools \
    && /opt/workspace-tools/bin/pip install --no-cache-dir \
        tree-sitter \
        tree-sitter-cpp \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/workspace-tools/bin:${PATH}"

WORKDIR /work
