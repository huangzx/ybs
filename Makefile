CC=gcc
CFLAGS=-O2
DESTDIR=
prefix=/usr
BINDIR=${DESTDIR}${prefix}/bin
SBINDIR=${DESTDIR}${prefix}/sbin
LIBDIR=${DESTDIR}${prefix}/lib/ybs
DATADIR=${DESTDIR}${prefix}/share/ybs
PYTHONSITE=${DESTDIR}/$(shell python -c 'import site; print site.getsitepackages()[0]')

make:
    

install: 
	install -d -m755 ${BINDIR} ${SBINDIR} ${LIBDIR} ${DATADIR} ${PYTHONSITE} 
	install -m755 src/{fileinfo,pybs,ybs,ybs-deps-check,ybs-diff-check,ybs-scanrdeps,ypk-conflict-check,ypk-scanpackages} ${BINDIR}
	install -m755 utils/* ${SBINDIR}
	install -m644 src/ybsutils.py ${PYTHONSITE}
	cp src/funcs ${LIBDIR}
	cp samples/* ${DATADIR}

clean:
	@echo 'do nothing'
