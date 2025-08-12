.PHONY: update-format format test test-dist build types upload cov init

python=./.venv/bin/python
pytest=./.venv/bin/pytest
package=memory_lane

version_file1=./src/memory_lane/version.py

VERSION=$(shell cat ${version_file1} | egrep -o "([0-9]{1,}\.)+[0-9]{1,}")
VERSION_PATCH=$(shell echo ${VERSION} | cut -d'.' -f3)
VERSION_MINOR=$(shell echo ${VERSION} | cut -d'.' -f2)
VERSION_MAJOR=$(shell echo ${VERSION} | cut -d'.' -f1)
GIT_COMMIT=$(shell git rev-parse --short HEAD)

all: init

# Env

init:
	make .venv
	uv pip install -r ./requirements.txt
	uv pip install -e ".[test]"
	make .git/hooks/pre-commit

.git/hooks/pre-commit:
	${python} -m pre_commit install

.venv:
	uv venv

## Development

update-format:
	${python} -m pre_commit autoupdate

format:
	${python} -m pre_commit run --all-files

test:
	${python} -m pytest ./tests

test-dist:
	${python} -m twine check dist/*

types:
	${python} -m monkeytype run $$(which ${pytest}) ./tests
	${python} -m monkeytype list-modules | grep ${package} | parallel -j1 "${python} -m monkeytype apply {} > /dev/null && echo {}"

cov:
	${python} -m pytest --cov=${package} --cov-config .coveragerc --cov-report html tests

build:
	${python} -m build --skip-dependency-check  .

upload:
	${python} -m twine upload ./dist/*

start-jupyter:
	${python} -m jupyterlab

## Version

version:
	echo ${VERSION}

bump-version-dev:
	test ! -z "${VERSION}"
	test ! -z "${GIT_COMMIT}"
	exit 1 # Not Implemented

bump-version-patch:
	test ! -z "${VERSION_PATCH}"
	make set-version VERSION=${VERSION_MAJOR}.${VERSION_MINOR}.$(shell awk 'BEGIN{print ${VERSION_PATCH}+1}')

bump-version-minor:
	test ! -z "${VERSION_MINOR}"
	make set-version VERSION=${VERSION_MAJOR}.$(shell awk 'BEGIN{print ${VERSION_MINOR}+1}').0

bump-version-major:
	test ! -z "${VERSION_MAJOR}"
	make set-version VERSION=$(shell awk 'BEGIN{print ${VERSION_MAJOR}+1}').0.0

set-version:
	test ! -z "${VERSION}"
	sed -i 's/\(^\|.*:\)__version__ = .*/__version__ = "${VERSION}"/' ${version_file1}

commit-tag-version:
	# git tag --list | grep -qix "${VERSION}"
	git commit -m "Version ${VERSION}" --no-verify ${version_file1}
	git tag '${package}-${VERSION}'

## Clean

clean:
	find ./rmsd/ -type f \
		-name "*.so" \
		-name "*.pyc" \
		-name ".pyo" \
		-delete
	rm -rf ./rmsd/*.egg-info/
	rm -rf *.whl
	rm -rf ./build/ ./__pycache__/
	rm -rf ./dist/

clean-env:
	rm -rf ./env/
	rm ./.git/hooks/pre-commit
