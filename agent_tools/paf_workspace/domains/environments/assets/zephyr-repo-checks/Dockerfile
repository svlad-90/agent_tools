# syntax=docker/dockerfile:1.7
#
# Zephyr repository validation environment for PR-style checks.
#
# This image extends the Zephyr/Xen build environment with dependencies used by
# Zephyr repository checks such as compliance, Doxygen coverage diffs, and
# coding guideline scripts. Keep target build/runtime validation in zephyr-xen.

ARG BASE_IMAGE=codex/zephyr-xen:24.04
FROM ${BASE_IMAGE}

ARG USER_ID=1000
ARG USER_GID=1000

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       clang-tidy \
       coccinelle \
       cppcheck \
       libpq-dev \
       lcov \
       nodejs \
       npm \
       python3-dev \
       python3-setuptools \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --upgrade codechecker

USER ${USER_ID}:${USER_GID}
