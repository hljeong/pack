# todo: python version, venv?
CC = g++ -Wall -g -std=c++17
PY = python3

.PHONY: all clean test cpp

all: test

clean:
	rm -rf a.out

test: cpp
	@./a.out
	@$(PY) py/test.py
	@echo "all tests passed"


cpp: cpp/pack.h cpp/test.cc
	@$(CC) cpp/test.cc

py: py/pack.py py/test.py
