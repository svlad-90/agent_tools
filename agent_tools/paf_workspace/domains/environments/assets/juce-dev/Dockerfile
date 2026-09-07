FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        clang \
        cmake \
        g++ \
        git \
        ladspa-sdk \
        libasound2-dev \
        libclang-dev \
        libcurl4-openssl-dev \
        libegl1-mesa-dev \
        libfontconfig1-dev \
        libfreetype-dev \
        libgl1-mesa-dev \
        libgtk-3-dev \
        libjack-jackd2-dev \
        libwebkit2gtk-4.1-dev \
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
        xvfb \
    && python3 -m venv /opt/workspace-tools \
    && /opt/workspace-tools/bin/pip install --no-cache-dir \
        PyYAML \
        clang==18.1.8 \
        tree-sitter \
        tree-sitter-cpp \
        tree-sitter-java \
    && rm -rf /var/lib/apt/lists/*

ENV LD_LIBRARY_PATH="/usr/lib/llvm-18/lib:${LD_LIBRARY_PATH}"
ENV PATH="/opt/workspace-tools/bin:${PATH}"

WORKDIR /workspace
