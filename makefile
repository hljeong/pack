include makefile_utils/defaults.mk

CC = g++ -Wall -g -std=c++17
PYTHON = python3

.PHONY: test clean update setup cpp

test: cpp
	@ ./a.out
	@ . ./$(VENV_ACTIVATE) && python -m pytest -v
	@ echo "all tests passed"

clean: python-clean
	@ rm -rf a.out

update: git-submodule-update

setup: git-hook-install venv-setup

cpp: cpp/pack.h cpp/test.cc
	@ $(CC) cpp/test.cc

include makefile_utils/git.mk
include makefile_utils/python.mk
include makefile_utils/venv.mk
