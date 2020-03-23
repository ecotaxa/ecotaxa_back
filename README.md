# ecotaxa-back

#### Backend (decoupled from UI) for EcoTaxa

In this directory:
- `py` is for Python back-end
- `java` is for Java back-end
- `docker` is a simple docker-compose configuration for setting up a DB server quickly, without impacting your whole system. It also embeds a PgAdmin4 docker image.
- `QA` contains all tests & measurements on the code 

What is shared between back-end and legacy EcoTaxa:
* Database
* Image vault
* Temporary directory

The back-end reads config.cfg from legacy and derives from there.

Launching the docker DB server:
* `cd docker`
* `docker-compose up`

TODO:
- [ ] Looks like the DB is utf-8, to fix. First phase we need a DB setup compatible with what's in 2.2.
- [ ] utf-8 seems to be an issue in files as well, see oceanomics/ecotaxa_dev#334
