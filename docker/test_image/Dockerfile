FROM ubuntu:18.04 as builder

MAINTAINER grololo06 <grololo06@users.noreply.github.com>

RUN apt-get update

# postgresql-client # for psycopg2
# gcc make file cython3 # for uvloop for uvicorn needs cython needs make
RUN apt-get install \
    python3.8 python3-venv python3.8-dev python3.8-venv \
    postgresql-client \
    gcc make file cython3 \
    --no-install-recommends --yes

# Get reqs from host
COPY py/requirements.txt ./reqs.txt

# Create venv, mandatory as we switched away from the python bundled with the OS
RUN python3.8 -m venv /venv
# Install
RUN PATH=/venv/bin pip3 install wheel
RUN PATH=/venv/bin:$PATH pip3 install -r reqs.txt

# Strip a bit...
RUN find /venv -name "*.pyc" -delete

##### Switch to target #####
FROM ubuntu:18.04 as target

# Cleanup to save on image size
RUN apt-get update && \
apt-get install python3.8 python3.8-venv python3.8-distutils \
postgresql-client curl \
libpq5 --no-install-recommends --yes && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
rm -rf /var/log/*

# Copy the venv from builder
RUN mkdir -p /venv
COPY --from=builder --chown=root:root /venv /venv

# Add venv to path
ENV PATH="/venv/bin:$PATH"

COPY py/requirements.txt ./reqs.txt
# But we add QA ones
COPY QA/py/requirements.txt ./reqs_qa.txt

# Below should say 'Requirement already satisfied' for prod package and their deps
RUN pip3 install -r reqs.txt -r reqs_qa.txt

