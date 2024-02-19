# ecotaxa-back

![CI](https://github.com/ecotaxa/ecotaxa_back/workflows/CI/badge.svg)
[![codecov](https://codecov.io/gh/grololo06/ecotaxa_back/branch/master/graph/badge.svg)](https://codecov.io/gh/grololo06/ecotaxa_back)

#### Backend (decoupled from UI) for EcoTaxa

In this directory:

- `py` is for Python back-end
- `QA` contains all tests & measurements on the code.

In `docker` one can find build scripts, as well as a simple docker-compose configuration for setting up a DB server quickly, without impacting your whole
  system. It also embeds a PgAdmin4 docker image.

The UI itself is a server-side Flask app, in `../ecotaxa` repository.

Image vault is virtually shared between back-end and legacy EcoTaxa, i.e. front-end.

The back-end reads config.cfg from legacy and derives from there.

Launching the docker DB server:

* `cd docker`
* `docker-compose up`
