# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

SHELL := /bin/bash -e
SCRIPTS := ../scripts
FIND_PYTHON_FILES := $(SCRIPTS)/find-python-files
PIPENV2 := $(SCRIPTS)/run-pipenv 2
PIPENV3 := $(SCRIPTS)/run-pipenv 3
PYTEST := $(PIPENV3) run py.test -vv
YAPF := $(PIPENV3) run yapf
BANDIT := $(PIPENV3) run bandit
MYPY := $(SCRIPTS)/run-mypy
ADDITIONAL_MYPY_ARGS :=

.PHONY: help prepare-node-modules test-docker test-pylint test-unit \
	test-mypy test-mypy-raw test-mypy3 test-mypy3-raw \
	clean test-packaging test-gui-crawl test-gui-crawl-docker \
	test-integration test-integration-docker \
	test-integration-docker-debug \
	test-composition-docker test-composition-docker-debug test-composition \
	test-format-python test-format-python3 \
	test-unit-coverage-html \
	test-pipenv-deps test-bandit test-agent-integration

help:
	@echo "test-mypy                     - Run mypy tests"
	@echo "test-mypy-raw                 - Run mypy tests with raw edition config"
	@echo "test-mypy3                    - Run mypy tests for Python 3"
	@echo "test-mypy3-raw                - Run mypy tests for Python 3 with raw edition config"
	@echo "test-format-python            - Run Python 2 formatting tests"
	@echo "test-format-python3           - Run Python 3 formatting tests"
	@echo "test-docker                   - Run docker tests"
	@echo "test-pylint                   - Run pylint based tests"
	@echo "test-unit                     - Run unit tests"
	@echo "test-unit-coverage-html       - Create HTML coverage report for unit tests"
	@echo "test-packaging                - Run packaging tests"
	@echo "test-gui-crawl                - Run GUI crawl locally"
	@echo "test-gui-crawl-docker         - Run GUI crawl in container"
	@echo "test-integration              - Run integration tests locally"
	@echo "test-integration-docker       - Run integration tests in container"
	@echo "test-integration-docker-debug - Run test container for manual debugging"
	@echo "test-composition              - Run composition tests locally"
	@echo "test-composition-docker       - Run composition tests in container"
	@echo "test-composition-docker-debug - Run test container for manual debugging"
	@echo "test-pipenv-deps              - Run pipenv dependency issue test"
	@echo "test-bandit                   - Run bandit (security) tests"
	@echo "test-agent-integration        - Run agent (plugin) related integration tests"

prepare-node-modules:
	$(MAKE) -C .. node_modules/.bin/webpack

test-docker:
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-pylint:
	$(PYTEST) -T pylint pylint

test-unit:
	$(PYTEST) -T unit unit

test-unit-coverage-html:
	$(PYTEST) \
	    --cov=cmk \
	    --cov-report=html \
	    --cov-config=.coveragerc_unit \
	    --no-cov-on-fail \
	    -T unit unit

test-mypy3:
	$(FIND_PYTHON_FILES) 3 | \
	`: filter out plugins, they are not real modules` \
	grep -v $$(realpath '../checks') | \
	grep -v $$(realpath '../inventory') | \
	if test -d ../enterprise; then \
	    grep -v $$(realpath '../agents')/bakery; \
	else \
	    cat; \
	fi | xargs -n 1500 $(MYPY) $(ADDITIONAL_MYPY_ARGS)

test-mypy3-raw:
	$(MAKE) test-mypy3 ADDITIONAL_MYPY_ARGS="--config-file=$(realpath ../mypy-raw.ini)"

MYPY2_FILES=$(shell \
    $(FIND_PYTHON_FILES) 2 | \
    `: filter out plugins, they are not real modules` \
    grep -v $$(realpath '../agents/plugins') | \
    grep -v $$(realpath '../checks') | \
    grep -v $$(realpath '../doc/skeleton_check') | \
    grep -v $$(realpath '../doc/predictive') | \
    grep -v $$(realpath '../doc/bi-example-oracle.mk') | \
    grep -v $$(realpath '../doc/bi-example.mk') | \
    if test -d ../enterprise; then \
        grep -v $$(realpath '../agents')/bakery | \
        grep -v $$(realpath '../enterprise/agents/plugins'); \
    else \
        cat; \
    fi | \
    grep -v $$(realpath '../inventory') | \
    `: We should really check these, but currently there are too many errors. :-/` \
    grep -v $$(realpath '../active_checks') | \
    grep -v $$(realpath '../agents/special') | \
    grep -v $$(realpath '../agents/windows') | \
    grep -v $$(realpath '../agents/wnx') | \
    grep -v $$(realpath '../doc/treasures') | \
    grep -v $$(realpath '../livestatus/api/python') | \
    grep -v $$(realpath '../notifications/sms') | \
    grep -v $$(realpath '../omd/packages') | \
    grep -v $$(realpath '../tests')) | \
    `: This is currently a base+GUI and py2/py3 mix. Reenable when GUI is py3` \
    grep -v $$(realpath '../bin/cmk-update-config')

test-mypy:
	$(MYPY) $(MYPY2_FILES)

test-mypy-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini)  $(MYPY2_FILES)

test-format-python: ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	@PYTHON_FILES=$${PYTHON_FILES-$$($(FIND_PYTHON_FILES) 2)} ; \
	$(YAPF) --parallel --style ../.style.yapf --verbose --diff $$PYTHON_FILES | \
	grep '^+++ .*(reformatted)$$' | \
	sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/' ; \
	exit $${PIPESTATUS[0]}

test-format-python3: ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	@if test -z "$$PYTHON_FILES"; then $(FIND_PYTHON_FILES) 3; else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(YAPF) --parallel --style ../.style.yapf --verbose --diff | \
	grep '^+++ .*(reformatted)$$' | \
	sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/' ; \
	exit $${PIPESTATUS[0]}

test-packaging:
	$(PYTEST) -T packaging packaging

test-gui-crawl: prepare-node-modules
	$(PYTEST) -T gui_crawl $(realpath gui_crawl/test_gui_crawl.py)

test-gui-crawl-docker:
	$(PIPENV3) run scripts/run-dockerized.py "test-gui-crawl"

test-integration: prepare-node-modules
	CI=true $(PIPENV3) run scripts/run-integration-test.py $(realpath integration)

test-integration-docker:
	$(PIPENV3) run scripts/run-dockerized.py "test-integration"

test-integration-docker-debug test-composition-docker-debug: prepare-node-modules
	$(PIPENV3) run scripts/run-dockerized.py debug

test-composition-docker:
	$(PIPENV3) run scripts/run-dockerized.py "test-composition"

# TODO: Need to either untie composition tests with agent updater code or migrate
# the agent updater to Python 3. The composition tests currently import the agent
# updater code for the test execution, which should not be done.
test-composition: prepare-node-modules
	$(PIPENV2) run py.test -vv -T composition $(realpath ../tests/composition)

test-pipenv-deps:
	$(PIPENV3) check

bandit.ini:
	( echo -n -e "[bandit]\ntargets: "; \
	  $(FIND_PYTHON_FILES) 3 | tr '\n' ',' | sed 's/,$$//'; \
	  echo ) > bandit.ini

test-bandit: bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-agent-integration:
	$(PYTEST) -T agent-integration $(realpath agent-integration)

clean:
	rm -rf .mypy_cache
