prefix=
BASH_PATH=${prefix}/bin
CC=gcc
CFLAGS=-O2
DESTDIR=

all: fileinfo
	@echo "Done"


fileinfo: FORCE
	make -C fileinfo

install: fileinfo
	@echo "Install to ${DESTDIR}, bash is at ${BASH_PATH}"
	@mkdir -p ${DESTDIR}${prefix}/usr/bin ${DESTDIR}${prefix}/usr/lib/ybs ${DESTDIR}/etc 
	@install -m755 fileinfo/fileinfo ybs ${DESTDIR}${prefix}/usr/bin
	@cp funcs ${DESTDIR}${prefix}/usr/lib/ybs
	@sed -i "s@^\#\!/bin@\#\!${BASH_PATH}@" ${DESTDIR}${prefix}/usr/bin/ybs
	@chmod a+x ${DESTDIR}${prefix}/usr/bin/fileinfo
	@chmod a+x ${DESTDIR}${prefix}/usr/bin/ybs
	@install -d -m755 ${DESTDIR}/var/ybs/pbslib       
	@install -d -m777 ${DESTDIR}/var/ybs/sources
	@install -d -m755 ${DESTDIR}/var/ypkg/packages 
	@install -d -m755 ${DESTDIR}/var/ypkg/db
	@echo "Done"

clean: FORCE
	make -C fileinfo clean
	rm -rf ./test
	@echo "Done"

FORCE:

