FROM ubuntu:18.04 as builder

MAINTAINER grololo06 <grololo06@users.noreply.github.com>

RUN apt-get update

# postgresql-client # for psycopg2
# gcc make file cython3 # for uvloop for uvicorn needs cython needs make
RUN apt-get install python3 python3-dev python3-setuptools python3-pip python3-wheel \
    postgresql-client \
    gcc make file cython3 \
    --no-install-recommends --yes

# Get reqs from host
COPY py/requirements.txt ./reqs.txt

# Install
RUN pip3 install -r reqs.txt

# To know which places to copy in NEXT step
# RUN for i in `pip3 list`; do pip3 show $i; done | grep Location | sort | uniq
# Location: /usr/lib/python3/dist-packages
# Location: /usr/local/lib/python3.6/dist-packages

#RUN apt-get install -y iputils-ping iproute2

RUN find /usr/lib/python3 /usr/local/lib/python3* -name "*.pyc" -delete

##### Switch to target #####
FROM ubuntu:18.04 as target

# Cleanup to save on image size
RUN apt-get update && \
#apt-get install python3 python3-pip postgresql-client curl iputils-ping iproute2 --no-install-recommends --yes && \
apt-get install python3 python3-pip libpq5 --no-install-recommends --yes && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
rm -rf /var/log/*

# Copy the dist-packages directly from builder, as wheels stick
RUN mkdir -p /usr/lib/python3/dist-packages
COPY --from=builder --chown=root:root /usr/lib/python3/dist-packages/ /usr/lib/python3/dist-packages/
RUN mkdir -p /usr/local/lib/python3.6/dist-packages
COPY --from=builder --chown=root:root /usr/local/lib/python3.6/dist-packages/ /usr/local/lib/python3.6/dist-packages/
COPY --from=builder --chown=root:root /usr/local/bin/ /usr/local/bin/

# Back to host entry for resolving
#COPY docker/prod_image/docker-access-host.sh /
#RUN chmod +x /docker-access-host.sh
#ENTRYPOINT ["/docker-access-host.sh"]

# Below should say 'Requirement already satisfied' for each package and deps
COPY py/requirements.txt ./reqs.txt
RUN pip3 install -r reqs.txt

# Get source
WORKDIR /app/
COPY py link.ini ./
COPY link.ini /

# Get starting script
COPY prod_image/start.sh /app
RUN chmod +x start.sh
# Make all app world-writable as we run as non-root
RUN chmod -R a+rw /app

EXPOSE 8000
CMD ["./start.sh"]