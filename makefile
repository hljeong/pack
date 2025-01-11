# todo: python version, venv?
CC = g++ -Wall -g -std=c++17
PY = python3

.PHONY: all clean test update cpp py

all: test

clean:
	rm -rf a.out

test: cpp
	@./a.out
	@# see: https://stackoverflow.com/a/77321590
	@$(PY) -m py.test
	@echo "all tests passed"

update:
	@git submodule foreach git pull origin main

cpp: cpp/pack.h cpp/test.cc
	@$(CC) cpp/test.cc

py: py/pack.py py/test.py
