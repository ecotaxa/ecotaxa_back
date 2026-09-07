FROM ubuntu:24.04 AS builder

MAINTAINER grololo06 <grololo06@users.noreply.github.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    gpg-agent \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update

RUN apt-get update && apt-get install \
    python3.14 python3-venv python3.14-dev python3.14-venv \
    --no-install-recommends --yes

# Get reqs from host
COPY py/requirements.txt ./reqs_orig.txt
# Remove typings
RUN grep -Ev "(-stubs|^types-)" reqs_orig.txt > reqs.txt

# Create venv, mandatory as we switched away from the python bundled with the OS
RUN python3.14 -m venv /venv
# Install wheel & upgrade pip which is pip-9.0.1 thus knows only manylinux1 repository
RUN PATH=/venv/bin pip3 install --upgrade pip wheel
RUN PATH=/venv/bin:$PATH pip3 install -r reqs.txt

# Strip a bit...
RUN find /venv -name "*.pyc" -delete && \
    rm -rf /venv/share/* && \
    find /venv -name tests -type d -exec rm -rf {} + && \
    find /venv/lib/python3.14/site-packages -name "*.exe" -delete

# Get source
WORKDIR /app/
COPY py ./

# Get starting script
COPY docker/prod_image/start.sh /app


##### Switch to target #####
FROM ubuntu:24.04 AS target

# Minimum install
RUN apt-get update && \
    apt-get install vim libpq5 dumb-init --no-install-recommends --yes && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/log/*

# Copy the venv and deps from builder
RUN mkdir -p /venv
COPY --from=builder --chown=root:root /venv /venv
COPY --from=builder /usr/bin/python3.14 /usr/bin/python3.14
COPY --from=builder /usr/lib/python3.14 /usr/lib/python3.14
COPY --from=builder /usr/lib/x86_64-linux-gnu/libpython3.14.so* /usr/lib/x86_64-linux-gnu/

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

EXPOSE 8000
# The number of gunicorn workers
ENV WEB_CONCURRENCY=8
# Of course the path below is seen from the container. Check your mounts.
# Needed directory contents can be found in config.ini.template
# ./appli
# ./temptask
# ./vault
WORKDIR /app/
ENV APP_CONFIG='/config.ini'

ENTRYPOINT ["/usr/bin/dumb-init", "--"]

CMD ["./start.sh"]