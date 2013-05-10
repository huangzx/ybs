CC=gcc
CFLAGS=-O2
DESTDIR=
prefix=/usr
BINDIR=${DESTDIR}${prefix}/bin
SBINDIR=${DESTDIR}${prefix}/sbin
LIBDIR=${DESTDIR}${prefix}/lib/ybs
DATADIR=${DESTDIR}${prefix}/share/ybs
PYTHONSITE=${DESTDIR}/$(shell python -c 'import site; print site.getsitepackages()[0]')/ybs/

make:
    
install: 
	install -d -m755 ${BINDIR} ${SBINDIR} ${LIBDIR} ${DATADIR} ${PYTHONSITE} 
	install -m644 src/sh/funcs ${LIBDIR}
	install -m755 src/sh/ybs ${BINDIR}
	install -m755 src/{fileinfo,pybs,pypkg,ybs-*,ypk-*} ${BINDIR}
	install -m644 src/ybs/*.py ${PYTHONSITE}
	install -m755 utils/* ${SBINDIR}
	install -m644 samples/* ${DATADIR}

clean:
	@echo 'do nothing'
