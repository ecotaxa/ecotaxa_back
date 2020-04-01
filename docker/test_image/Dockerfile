FROM ubuntu:18.04 as builder

MAINTAINER grololo06 <grololo06@users.noreply.github.com>

RUN apt-get update

RUN apt-get install python3 python3-pip postgresql-client curl --no-install-recommends --yes
# All below is just for compiling psycopg2cffi, i.e. running the backend under pypy
RUN apt-get install python3-dev python3-setuptools g++ libpq-dev python3-wheel --yes

# Generate binary packages (wheels)
COPY py/requirements.txt ./reqs.txt
COPY QA/py/requirements.txt ./reqs_qa.txt

#RUN pip3 wheel -r reqs.txt -r reqs_qa.txt
RUN pip3 install -r reqs.txt -r reqs_qa.txt

# RUN for i in `pip3 list`; do pip3 show $i; done | grep Location | sort | uniq
# Location: /usr/lib/python3/dist-packages
# Location: /usr/local/lib/python3.6/dist-packages

# Get rid of compiling needs
# RUN apt-get purge python3-dev python3-setuptools g++ libpq-dev python3-wheel --yes
# RUN apt-get autoremove --yes

FROM ubuntu:18.04 as target

RUN apt-get update && \
apt-get install python3 python3-pip postgresql-client curl --no-install-recommends --yes && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

COPY py/requirements.txt ./reqs.txt
COPY QA/py/requirements.txt ./reqs_qa.txt

# Get wheels from builder, so install size is minimal
# OK but the .whl remain and take space
#COPY --from=builder /*.whl ./

RUN mkdir -p /usr/lib/python3/dist-packages
COPY --from=builder --chown=root:root /usr/lib/python3/dist-packages/ /usr/lib/python3/dist-packages/
RUN mkdir -p /usr/local/lib/python3.6/dist-packages
COPY --from=builder --chown=root:root /usr/local/lib/python3.6/dist-packages/ /usr/local/lib/python3.6/dist-packages/

#RUN pip3 install *.whl
# Below should say 'all installed already'
RUN pip3 install -r reqs.txt -r reqs_qa.txt

