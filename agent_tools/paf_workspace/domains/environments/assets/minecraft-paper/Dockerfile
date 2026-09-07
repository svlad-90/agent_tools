FROM ubuntu:24.04

ARG GRADLE_VERSION=9.7.1

ENV DEBIAN_FRONTEND=noninteractive \
	VIRTUAL_ENV=/opt/minecraft-paper-venv \
	GRADLE_HOME=/opt/gradle \
	PATH=/opt/minecraft-paper-venv/bin:/opt/gradle/bin:${PATH}

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bash \
		ca-certificates \
		curl \
		git \
		netcat-openbsd \
		openjdk-21-jdk \
		procps \
		python3 \
		python3-pip \
		python3-venv \
		sqlite3 \
		unzip \
		zip \
	&& rm -rf /var/lib/apt/lists/*

RUN python3 -m venv "${VIRTUAL_ENV}" \
	&& pip3 install --upgrade \
		PyYAML \
		tree-sitter \
		tree-sitter-cpp

RUN curl -fsSL "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" \
		-o /tmp/gradle.zip \
	&& unzip -q /tmp/gradle.zip -d /opt \
	&& mv "/opt/gradle-${GRADLE_VERSION}" "${GRADLE_HOME}" \
	&& rm /tmp/gradle.zip

WORKDIR /workspace
