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
libpq5 --no-install-recommends --yes && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
rm -rf /var/log/*

# Copy the venv from builder
RUN mkdir -p /venv
COPY --from=builder --chown=root:root /venv /venv

# Add venv to path
ENV PATH="/venv/bin:$PATH"

# Below should say 'Requirement already satisfied' for each package and their deps
COPY py/requirements.txt ./reqs.txt
RUN pip3 install -r reqs.txt

# Get source
WORKDIR /app/
COPY py ./
COPY link.ini /

# Get starting script
COPY prod_image/start.sh /app
RUN chmod +x start.sh
# Make all app world-writable (for .pyc) as we run as non-root
RUN chmod -R a+rw /app /venv

EXPOSE 8000
# The number of gunicorn workers
ENV WEB_CONCURRENCY=8
# Of course the path below is seen from the container. Check your mounts.
# Needed directory content:
# ./appli
# ./appli/config.cfg
# ./temptask
# ./vault
ENV LEGACY_APP='/ecotaxa_master'
CMD ["./start.sh"]