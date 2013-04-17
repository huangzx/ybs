#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
# Copyright © 2013 ivali.com
# Author: Zhongxin Huang <zhongxin.huang@gmail.com>
#

import os
import sys
from ybs import ybsutils
import sqlite3
import argparse
import time
import StringIO
import multiprocessing


PROCESSES_NUM = 4
SHOW_INSTALLED_ONLY = False
SHOW_UNINSTALLED_ONLY = False
INSTALL_FORCE = False
IS_VERBOSE = False


def ybs_list_available(pbslib):
    ''' display name and version of package in pbslib.

    Args:
      pbslib: dict, map of pbslib

    '''
    for key in pbslib:
        print(' '.join((key, pbslib[key][-1])))


def ybs_list_installed(package_db):
    ''' display name and version of package installed.

    Args:
      package_db: sqlite3 database created by ypkg

    '''
    conn = sqlite3.connect(package_db)
    for res in conn.execute("SELECT name, version FROM {}".format('world')):
        print(' '.join(res))
    conn.close()


def ybs_status(name):
    '''

    Args:
      name: string

    Returns:
      result: tuple, looks like: (u'leafpad', u'0.8.18.1', u'', 1365583434)

    '''
    result = ybsutils.is_installed(name)
    if result is None:
        sys.stderr.write("'{}' not found. Be sure it is installed.\n".format(name))
        return ()
    else:
        return result


def ybs_showpbs(name, pbslib):
    '''

    Args:
     name: string, name of package
     pbslib: dict, map of pbslib

    Returns:
      string: path to pbsfile, such as:
        '/var/ybs/pbslib/app-editors/leafpad/leafpad_0.8.18.1.pbs'

    '''
    if not name in pbslib:
        sys.stderr.write("'{}' not found in {}.\n".format(name, ybsutils.__pbslib_path__))
        sys.exit(1)
    else:
        return ybsutils.file_in_dir(ybsutils.__pbslib_path__, name + '_' + pbslib[name][-1] + '.pbs')


def ybs_search(name, pbslib):
    ''' search package in pbslib

    Args:
      name: string, name of package
      pbslib: dict, map of pbslib

    '''
    name = name.lower()
    suffix_match = False
    prefix_match = False
    if name.endswith('$'):
        suffix_match = True
        name = name.rstrip('$')
    if name.startswith('^'):
        prefix_match = True
        name = name.lstrip('^')
    for pkgname in pbslib:
        pkgname_lower = pkgname.lower()
        if name in pkgname_lower:
            if suffix_match:
                if not pkgname_lower.endswith(name):
                    continue
            if prefix_match:
                if not pkgname_lower.startswith(name):
                    continue
            version = pbslib[pkgname][-1]
            installed_info = ybsutils.is_installed(pkgname)
            if SHOW_INSTALLED_ONLY:
                if not installed_info:
                    continue
            if SHOW_UNINSTALLED_ONLY:
                if installed_info:
                    continue
            flag = '[]'
            installed_version = 'None'
            installed_time = ''
            if installed_info:
                installed_version = installed_info[1]
                ret = ybsutils.compare_version(str(version), str(installed_version))
                if ret == 1:
                    flag = '[U]'
                if ret == -1:
                    flag = '[D]'
                if ret == 0:
                    flag = '[I]'
                installed_time = installed_info[-1]
                installed_time = time.localtime(installed_time)
                installed_time = time.strftime("%Y-%m-%d %H:%M:%S", installed_time)
            pbspath = ybs_showpbs(pkgname, pbslib)
            pbsfile = ybsutils.PbsFile()
            pbsfile.parse(pbspath)
            category = pbspath.split('/')[4]
            print('''{} {}/{}
      Installed: {} {}
      Available: {}
      Homepage: {}
      Description: {}
                  '''.format(flag, category, pkgname, installed_version,
                             installed_time, ', '.join(pbslib[pkgname]),
                             (' '.join(pbsfile.get('HOMEPAGE'))),
                             (' '.join(pbsfile.get('DESCRIPTION')))))


def ybs_whatrequires(name, dbfile):
    ''' display what require given package

    Args:
      name: string, name of package
      dbfile: sqlite3 database created by pybs

    '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute("SELECT name, version FROM universe;")
    # cur.fetchall() returns a list looks like:
    # [(u'lxrandr', u'1.2'), (u'lxmenu-data', u'1,3',)]
    for pkg in cur.fetchall():
        pkg_name, pkg_version = pkg
        if SHOW_INSTALLED_ONLY:
            if not ybsutils.is_installed(pkg_name):
                continue
        if SHOW_UNINSTALLED_ONLY:
            if ybsutils.is_installed(pkg_name):
                continue
        for type_ in ('rdep', '[R]'), ('bdep', '[B]'), ('redep', '[A]'), ('cdep', '[C]'):
            type_, flag = type_
            cur.execute("SELECT {} FROM universe WHERE name = '{}';".format(type_, pkg_name))
            # cur.fetchone() returns a tuple looks like:
            # (u'gtk2(>=1.27) menu-cache startup-notification',)
            deps = [x.split('(')[0] for x in cur.fetchone()[0].split()]
            if name in deps:
                #if ybsutils.is_installed(pkg_name):
                #    flag = flag + '[I]'
                print('{} {} {}'.format(flag, pkg_name, pkg_version))
    cur.close()
    conn.close()


def ybs_update_db(dbfile):
    ''' update dbfile

    Args:
      dbfile: string, path to dbfile

    '''
    if os.path.exists(dbfile):
        os.remove(dbfile)
    ybs_init_db(dbfile)


def get_deps_from_file(infile):
    ''' display dependency of pbsfile.

    Args:
      infile: string, path to pbsfile

    '''
    pbsfile = ybsutils.PbsFile()
    pbsfile.parse(infile)
    name, version = pbsfile.name, pbsfile.version
    rdep = ' '.join(pbsfile.get('RDEPEND'))
    bdep = ' '.join(pbsfile.get('BDEPEND'))
    redep = ' '.join(pbsfile.get('RECOMMENDED'))
    cdep = ' '.join(pbsfile.get('CONFLICT'))
    return (name, version, rdep, bdep, redep, cdep)


def ybs_init_db(dbfile, processes_num=PROCESSES_NUM):
    ''' creat dbfile with muti-processings

    Args:
      dbfile: string, path to dbfile
      processes_num: int, numbers of muti-processings

    '''
    if os.path.exists(dbfile):
        return 0
    dir_ = os.path.dirname(dbfile)
    if not os.path.isdir(dir_):
        os.mkdir(dir_)
    sys.stderr.write("Parsing dependency tree of '{}' to '{}'...\n".format(ybsutils.__pbslib_path__, dbfile))
    # Creat memory type database
    conn = sqlite3.connect(':memory:')
    conn.execute("CREATE TABLE IF NOT EXISTS universe (name TEXT, version TEXT, \
      rdep TEXT, bdep TEXT, redep TEXT, cdep TEXT);")

    pool = multiprocessing.Pool(processes_num)
    files = ybsutils.files_in_dir(ybsutils.__pbslib_path__, '.pbs', filte='version')
    result = pool.map(get_deps_from_file, files)
    pool.close()
    pool.join()
    if len(result) != len(files):
        sys.stderr.write('Missing datas: found {}, handled {}\n'.format(len(files), len(result)))
        sys.exit(1)
    # Write to memory type database
    for res in result:
        conn.execute('INSERT INTO universe (name, version, rdep, bdep, redep, cdep) VALUES (?, ?, ?, ?, ?, ?)', res)
    # Write data of RAM to file
    str_buffer = StringIO.StringIO()
    for line in conn.iterdump():
        str_buffer.write('{}\n'.format(line))
    conn.close()
    # Write to real database
    conn = sqlite3.connect(dbfile)
    conn.executescript(str_buffer.getvalue())
    conn.close()


def ybs_compare_version(s1, s2):
    ''' compare version

    Args:
      s1: string, verison
      s2: string, verison

    '''
    g = ybsutils.GetNameVersion()
    g.parse(s1)
    v1 = g.version
    g.parse(s2)
    v2 = g.version
    return (ybsutils.compare_version(v1, v2))


def ybs_get_rdeps(deptype, pkg, dbfile):
    ''' get run-time dependency from dbfile

    Args:
      deptype: string, type of dependency, such as: rdep
      pkg: string, name of package
      dbfile: dbfile

    Returns:
      yield generator, contains string items

    '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute("SELECT {} FROM universe WHERE name = '{}'".format(deptype, pkg))
    results = cur.fetchone()
    if results:
        for res in [x.split('(')[0] for x in results[0].split()]:
            yield res
    else:
        sys.stderr.write("'{}' not found in {}, run 'pybs --update_db' and retry.\n".format(pkg, dbfile))
        sys.exit(1)
    cur.close()
    conn.close()


def ybs_get_bdeps(deptype, pkg, dbfile):
    ''' get build-time dependency from dbfile

    Args:
      deptype: string, type of dependency, such as: rdep
      pkg: string, name of package
      dbfile: dbfile

    Returns:
      list: contains string items

    '''
    def _do_get(inlist):
        result = []
        for pkg in inlist:
            cur.execute("SELECT {} FROM universe WHERE name = '{}'".format(deptype, pkg))
            pkg_rdep = cur.fetchone()
            # (u'ca-certificates libssh(>=0.2) openssl zlib rtmpdump',)
            if not pkg_rdep:
                sys.stderr.write("'{}' not found in {}, run 'pybs --update_db' and retry.\n".format(pkg, dbfile))
                sys.exit(1)
            pkg_rdep = [x.split('(')[0] for x in pkg_rdep[0].split()]
            #result.extend(pkg_rdep)
            for x in pkg_rdep:
                if x not in result:
                    result.append(x)
        return result

    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    record = [pkg]
    while True:
        pre = len(record)
        for x in _do_get(record):
            if x not in record:
                record.append(x)
        if len(record) == pre:
            break

    order = []
    for x in record:
        #print x
        for y in order:
            if x in _do_get([y]):
                order.insert(order.index(y), x)
                break
        if x not in order:
            order.append(x)
        #print order

    cur.close()
    conn.close()
    return order


def ybs_pretend(pkg, pbslib):
    ''' instead of actually build, display what to do.

    These flag means:
     [N] -- new install
     [U] -- upgrade
     [D] -- downgrade
     [E] -- same version

    '''
    flag = ''
    if INSTALL_FORCE:
        flag = 'F'

    bdeps = ybs_get_bdeps('bdep', pkg, ybsutils.__depend_db__)

    for bdep in bdeps:
        version = pbslib[bdep][-1]
        installed_info = ybsutils.is_installed(bdep)
        if installed_info:
            installed_version = installed_info[1]
            ret = ybsutils.compare_version(version, installed_version)
            if ret == 0:
                if IS_VERBOSE or INSTALL_FORCE:
                    print('[{}] {} {}'.format('E'+flag, bdep, version))
            if ret == 1:
                print('[{}] {} {} -> {}'.format('U'+flag, bdep, installed_version, version))
            if ret == -1:
                print('[{}] {} {} -> {}'.format('D'+flag, bdep, installed_version, version))
        else:
            print('[{}] {} {}'.format('N'+flag, bdep, version))


def main():
    ''' '''
    ybsutils.signal_int()
    argvs = sys.argv[1:]
    if not argvs:
        argvs = ['-h']

    parser = argparse.ArgumentParser(description='ybs (StartOS Build System) backend.')
    parser.add_argument('-V', '--version', action='store_true',
                        dest='V', help='show version')
    parser.add_argument('-v', '--verbose', action='store_true',
                        dest='v', help='enable verbose mode')
    parser.add_argument('-F', '--force', action='store_true',
                        dest='F', help='force build flag')
    parser.add_argument('-I', '--installed', action='store_true',
                        dest='I', help='only matches the installed packages')
    parser.add_argument('-N', '--uninstalled', action='store_true',
                        dest='N', help='only matches the uninstalled packages')
    parser.add_argument('-l', '--list', action='store_true',
                        dest='l', help='list all availabe packages')
    parser.add_argument('-L', '--list_installed', action='store_true',
                        dest='L', help='list all installed packages')
    parser.add_argument('-t', '--status', nargs='*', metavar='pkg',
                        dest='t', help='show information of pkg installed')
    parser.add_argument('-s', '--search', nargs='*', metavar='pkg',
                        dest='s', help='search package in pbslib')
    parser.add_argument('-p', '--pretend', nargs='*', metavar='pkg',
                        dest='p', help='instead of actually build, display what to do')
    parser.add_argument('-w', '--showpbs', nargs='*', metavar='pkg',
                        dest='w', help='show available pbsfile in pbsdir')
    parser.add_argument('-gr', '--get_rdeps', nargs='*', metavar='pkg',
                        dest='gr', help='show run-time dependency of package')
    parser.add_argument('-gb', '--get_bdeps', nargs='*', metavar='pkg',
                        dest='gb', help='show build-time dependency of package')
    parser.add_argument('-wr', '--whatrequires', nargs='*', metavar='pkg',
                        dest='wr', help='show what require given package')
    parser.add_argument('-u', '--update_db', action='store_true',
                        dest='u', help='update dependency database')
    parser.add_argument('-cv', '--compare_version', nargs=2, metavar='ver',
                        dest='cv', help='comprare two version strings')
    args = parser.parse_args(argvs)

    if args.v:
        global IS_VERBOSE
        IS_VERBOSE = True

    if args.V:
        print(ybsutils.__version__)
        sys.exit()

    if args.F:
        global INSTALL_FORCE
        INSTALL_FORCE = True

    if args.I:
        global SHOW_INSTALLED_ONLY
        SHOW_INSTALLED_ONLY = True

    if args.N:
        global SHOW_UNINSTALLED_ONLY
        SHOW_UNINSTALLED_ONLY = True

    if args.u:
        ybs_update_db(ybsutils.__depend_db__)

    if args.l:
        pbslib_map = ybsutils.parse_pbslib(ybsutils.__pbslib_path__)
        ybs_list_available(pbslib_map)

    if args.L:
        ybs_list_installed(ybsutils.__package_db__)

    if args.cv:
        x, y = args.cv
        print(ybs_compare_version(x, y))

    if args.w:
        pbslib_map = ybsutils.parse_pbslib(ybsutils.__pbslib_path__)
        for i in args.w:
            print(ybs_showpbs(i, pbslib_map))

    if args.s:
        pbslib_map = ybsutils.parse_pbslib(ybsutils.__pbslib_path__)
        for i in args.s:
            ybs_search(i, pbslib_map)

    if args.p:
        pbslib_map = ybsutils.parse_pbslib(ybsutils.__pbslib_path__)
        for i in args.p:
            ybs_pretend(i, pbslib_map)

    if args.t:
        for i in args.t:
            for x in ybs_status(i):
                print(x),

    if args.gb:
        ybs_init_db(ybsutils.__depend_db__)
        for i in args.gb:
            for x in ybs_get_bdeps('bdep', i, ybsutils.__depend_db__):
                print(x),

    if args.gr:
        ybs_init_db(ybsutils.__depend_db__)
        for i in args.gr:
            for x in ybs_get_rdeps('rdep', i, ybsutils.__depend_db__):
                print(x),

    if args.wr:
        ybs_init_db(ybsutils.__depend_db__)
        for i in args.wr:
            print('{} is related with:\n'.format(i))
            ybs_whatrequires(i, ybsutils.__depend_db__)


if __name__ == '__main__':
    main()
