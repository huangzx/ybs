CC=gcc
CFLAGS=-O2
DESTDIR=
prefix=/usr
BIN=ybs
BINDIR=${DESTDIR}${prefix}/bin
LIBDIR=${DESTDIR}${prefix}/lib/${BIN}
DATADIR=${DESTDIR}${prefix}/share/${BIN}
PKGDIR=${DESTDIR}/var/ypkg/packages
DBDIR=${DESTDIR}/var/ypkg/db

all: fileinfo
	@echo "Done"

fileinfo: FORCE
	make -C fileinfo

install: fileinfo
	install -d -m755 ${BINDIR} ${LIBDIR} ${DATADIR} ${PBSDIR} ${SRCDIR} ${PKGDIR} ${DBDIR}
	install -m755 fileinfo/fileinfo ybs ykms ybs-scanpackages ${BINDIR}
	cp funcs ${LIBDIR}
	cp ybs.conf.sample ${DATADIR}
	@echo "Done"

clean: FORCE
	make -C fileinfo clean
	@echo "Done"

FORCE:

