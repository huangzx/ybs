CC=gcc
CFLAGS=-O2


all: fileinfo
	@echo "Done"

sources=file_info.c md5.c mddriver.c
headers=global.h md5.h


fileinfo: ${sources}
	${CC} ${CFLAGS}  -o $@ ${sources}

clean:
	rm -f fileinfo
	
