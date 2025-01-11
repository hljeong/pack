# todo: python version, venv?
CC = g++ -Wall -g -std=c++17
PY = python3

.PHONY: all clean test update cpp py

all: test

clean:
	rm -rf a.out

test: cpp py
	@./a.out
	@# see: https://stackoverflow.com/a/77321590
	@$(PY) -m pytest -v
	@echo "all tests passed"

update:
	@git submodule foreach git pull origin main

cpp: cpp/pack.h cpp/test.cc
	@$(CC) cpp/test.cc

py: py/pack/pack.py py/test_pack.py
