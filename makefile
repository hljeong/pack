CC = g++
FLAGS = -Wall -g -std=c++17

.PHONY: all clean test cpp

all: test

clean:
	rm -rf a.out

test: cpp
	@./a.out
	@rm -rf a.out
	@echo "all tests passed"


cpp: cpp/pack.h cpp/test.cc
	@$(CC) cpp/test.cc
