EcoTaxa automated tests directory
==

You will find here a suite of quality-related automated tests and checks. This suite runs in GitHub actions after each
commit, but should run flawlessly as well on each developper PC before a commit.

Virtual env
--
After some setup, the GitHub action mainly runs tox https://tox.wiki/en/latest/ as the entry point of everything.

The tests need a _specific_ venv, this allows addition of QA-related tools without polluting the main `requirements.txt`
. Tox installs and manages its own venvs during its run, but for running individually one of the tests, you will need to
setup one in your favorite IDE. As a consequence, the synchronization b/w main requirements.txt and present one has to
be done manually (so far).

Customization
--
Note: **Postgresql** main path is hardcoded in `tools/dbBuildSQL.py` file. Please adapt to your own local installation.
Tests will stop very early if the path is not OK. You will need server PG tools (i.e. **initdb**) as well as the usual
client-side ones.

Typings
--
Automated tests cannot find all issues. So EcoTaxa uses, as a prevention
measure, [typings](https://docs.python.org/3/library/typing.html)
and [mypy](http://mypy-lang.org/) to check that the typings are OK. It's a good idea to be familiar with type checking
in python, as mypy errors can be quite obscure. You will find in main directory a documented `mypy.ini`, and in code a few
places where typings was on-purpose ignored.