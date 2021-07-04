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
COPY py/requirements.txt ./reqs_orig.txt
# Remove typings
RUN grep -v stubs reqs_orig.txt > reqs.txt

# Create venv, mandatory as we switched away from the python bundled with the OS
RUN python3.8 -m venv /venv
# Install
RUN PATH=/venv/bin pip3 install wheel
RUN PATH=/venv/bin:$PATH pip3 install -r reqs.txt

# Strip a bit...
RUN find /venv -name "*.pyc" -delete && \
rm -rf /venv/share/* && \
rm /venv/lib/python3.8/site-packages/uvloop/loop.c && \
find /venv -name tests -type d -exec rm -rf {} + && \
find /venv/lib/python3.8/site-packages -name "*.exe" -delete

# Get source
WORKDIR /app/
COPY py ./

# Get starting script
COPY prod_image/start.sh /app


##### Switch to target #####
FROM ubuntu:18.04 as target

# Minimum install
RUN apt-get update && \
apt-get install python3.8 libpq5 --no-install-recommends --yes && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
rm -rf /var/log/*

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

# Add venv to path
ENV PATH="/venv/bin:$PATH"

# _the_ ini file
COPY link.ini /

EXPOSE 8000
# The number of gunicorn workers
ENV WEB_CONCURRENCY=8
# Of course the path below is seen from the container. Check your mounts.
# Needed directory content:
# ./appli
# ./appli/config.cfg
# ./temptask
# ./vault
WORKDIR /app/
ENV LEGACY_APP='/ecotaxa_master'
CMD ["./start.sh"]