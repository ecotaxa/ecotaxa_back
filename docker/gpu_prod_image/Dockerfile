FROM ubuntu:18.04 as builder

#
# @see https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#install-guide
#
MAINTAINER grololo06 <grololo06@users.noreply.github.com>

RUN apt-get update

# postgresql-client # for psycopg2
RUN apt-get install \
    python3.8 python3-venv python3.8-dev python3.8-venv \
    postgresql-client-10 libpq-dev \
    --no-install-recommends --yes

# Get GPU reqs from host
COPY py/gpu_jobs_reqs.txt ./reqs_orig.txt
# Remove typings
RUN grep -Ev "(-stubs|^types-)" reqs_orig.txt >> reqs.txt

# Create venv, mandatory as we switched away from the python bundled with the OS
RUN python3.8 -m venv /venv
# Install wheel & upgrade pip which is pip-9.0.1 thus knows only manylinux1 repository
RUN PATH=/venv/bin pip3 install --upgrade pip wheel setuptools
RUN PATH=/venv/bin:$PATH pip3 install -r reqs.txt

# Strip a bit...
RUN find /venv -name "*.pyc" -delete && \
rm -rf /venv/share/* && \
find /venv -name tests -type d -exec rm -rf {} + && \
find /venv/lib/python3.8/site-packages -name "*.exe" -delete

# Get source
WORKDIR /app/
COPY py ./

# Get starting script
COPY docker/gpu_prod_image/start.sh /app


##### Switch to target #####
# Image is for drivers v470
FROM nvidia/cuda:11.4.3-cudnn8-runtime-ubuntu18.04 as target

RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub

# Minimum install
RUN apt-get update && \
apt-get install python3.8 libpq5 --no-install-recommends --yes && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
rm -rf /var/log/*

# Copy distutils from builder, hidden dep of TF
COPY --from=builder --chown=root:root /usr/lib/python3.8/distutils /usr/lib/python3.8/distutils

# Copy the venv from builder
RUN mkdir -p /venv
COPY --from=builder --chown=root:root /venv /venv

# Copy the app from builder
RUN mkdir -p /app
COPY --from=builder --chown=root:root /app /app

# For /app/ecotaxa_back_0.log and **/__pycache__, allow non-root user to create inside dirs
# and fix startup script rights
RUN find /venv /app -type d -exec chmod a+w {} \; && \
chmod +x /app/start.sh

# Create an empty config file which can be mounted
RUN touch /config.ini

# Add venv to path
ENV PATH="/venv/bin:$PATH"

# NO WEB
# EXPOSE 8000
# The number of gunicorn workers
#ENV WEB_CONCURRENCY=8
# Of course the path below is seen from the container. Check your mounts.
# Needed directory content:
# ./appli
# ./appli/config.cfg
# ./temptask
# ./vault
WORKDIR /app/
ENV APP_CONFIG='/config.ini'
CMD ["./start.sh"]
#CMD["sleep 600"]
