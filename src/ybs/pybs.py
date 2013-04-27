#!/usr/bin/env python2
# -*- coding: utf-8 -*-
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

PBSLIB_PATH = ybsutils.__pbslib_path__
DEPEND_DB = ybsutils.__depend_db__
DEPEND_DB_TABLE = ybsutils.__depend_db_table__
PACKAGE_DB = ybsutils.__package_db__
PACKAGE_DB_TABLE = ybsutils.__package_db_table__


def ybs_list_available(pbslib):
    ''' Display name and version of package in pbslib.

    Args:
      pbslib: dict, map of pbslib

    '''
    for key in pbslib:
        name, version = key, pbslib[key][-1]
        installed_info = ybsutils.is_installed(name)
        if installed_info:
            version_installed = installed_info[1]
            ret = ybsutils.compare_version(version_installed, version)
            if ret == '<':
                print('[U] {} {} -> {}'.format(name, version_installed, version))
            if ret == '>':
                print('[D] {} {} -> {}'.format(name, version_installed, version))
            if ret == '=':
                print('[E] {} {}'.format(name, version))
        else:
            print('[N] {} {}'.format(name, version))


def ybs_list_installed(dbtable=PACKAGE_DB_TABLE, dbfile=PACKAGE_DB):
    ''' Display name and version of package installed.

    Args:
      dbfile: sqlite3 database created by ypkg

    '''
    conn = sqlite3.connect(dbfile)
    for res in conn.execute("SELECT name, version FROM {}".format(dbtable)):
        print(' '.join(res))
    conn.close()


def ybs_status(name):
    ''' Display information of packages installed
    
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
        name, version, repo, installed_time = result
        print(' '.join((name, version, repo, ybsutils.what_time(installed_time))))


def ybs_showpbs(name, pbslib):
    ''' Display path to pbsfile directory.

    Args:
     name: string, name of package
     pbslib: dict, map of pbslib

    Returns:
      string: path to pbsfile, such as:
        '/var/ybs/pbslib/app-editors/leafpad/leafpad_0.8.18.1.pbs'

    '''
    if not name in pbslib:
        sys.stderr.write("'{}' not found in {}.\n".format(name, PBSLIB_PATH))
        sys.exit(1)
    else:
        return ybsutils.file_in_dir(PBSLIB_PATH, name + '_' + pbslib[name][-1] + '.pbs')


def ybs_search(name, pbslib):
    ''' Search package in pbslib

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
            flag = '[N]'
            installed_version = 'None'
            installed_time = ''
            if installed_info:
                installed_version = installed_info[1]
                ret = ybsutils.compare_version(str(installed_version), str(version))
                if ret == '<':
                    flag = '[U]'
                if ret == '>':
                    flag = '[D]'
                if ret == '=':
                    flag = '[E]'
                installed_time = ybsutils.what_time(installed_info[-1])
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


def ybs_whatrequires(name, dbtable=DEPEND_DB_TABLE, dbfile=DEPEND_DB):
    ''' Display what require given package

    Args:
      name: string, package name
      dbfile: sqlite3 database created by pybs

    '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute("SELECT name, version FROM {};".format(dbtable))
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
            cur.execute("SELECT {} FROM {} WHERE name = '{}';".format(type_, dbtable, pkg_name))
            # cur.fetchone() returns a tuple looks like:
            # (u'gtk2(>=1.27) menu-cache startup-notification',)
            deps = [x.split('(')[0] for x in cur.fetchone()[0].split()]
            if name in deps:
                #if ybsutils.is_installed(pkg_name):
                #    flag = flag + '[I]'
                print('{} {} {}'.format(flag, pkg_name, pkg_version))
    cur.close()
    conn.close()


def ybs_update_db(dbfile=DEPEND_DB, dbtable=DEPEND_DB_TABLE):
    ''' Update dbfile

    Args:
      dbfile: string, path to dbfile

    '''
    if os.path.exists(dbfile):
        os.remove(dbfile)
    ybs_init_db(dbfile, dbtable)


def get_deps_from_file(infile):
    ''' Display dependency of pbsfile.

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


def get_deps_from_db(pkg, dep_type, dbfile=DEPEND_DB, dbtable=DEPEND_DB_TABLE):
    ''' Get run-time dependency from dbfile

    Args:
      dep_type: string, type of dependency, such as: rdep, bdep
      pkg: string, name of package
      dbfile: dbfile

    Returns:
      yield generator, contains string items

    '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute("SELECT {} FROM {} WHERE name = '{}'".format(dep_type, dbtable, pkg))
    results = cur.fetchone()
    if results:
        for res in [x.split('(')[0] for x in results[0].split()]:
            yield res
    else:
        sys.stderr.write("'{}' not found in {}, run 'pybs --update_db' and retry.\n".format(pkg, dbfile))
        sys.exit(1)
    cur.close()
    conn.close()


def ybs_init_db(dbfile=DEPEND_DB, dbtable=DEPEND_DB_TABLE, processes_num=PROCESSES_NUM):
    ''' Creat dbfile with muti-processings

    Args:
      dbfile: string, path to dbfile
      processes_num: int, numbers of muti-processings

    '''
    if os.path.exists(dbfile):
        return 0
    dir_ = os.path.dirname(dbfile)
    if not os.path.isdir(dir_):
        os.mkdir(dir_)
    sys.stderr.write("Parsing dependency tree of '{}' to '{}'...\n".format(PBSLIB_PATH, dbfile))
    # Creat memory type database
    conn = sqlite3.connect(':memory:')
    conn.execute("CREATE TABLE IF NOT EXISTS {} (name TEXT, version TEXT, rdep TEXT, bdep TEXT, redep TEXT, cdep TEXT);".format(dbtable))

    pool = multiprocessing.Pool(processes_num)
    files = ybsutils.files_in_dir(PBSLIB_PATH, '.pbs', filte='version')
    result = pool.map(get_deps_from_file, files)
    pool.close()
    pool.join()
    if len(result) != len(files):
        sys.stderr.write('Missing datas: found {}, handled {}\n'.format(len(files), len(result)))
        sys.exit(1)
    # Write to memory type database
    for res in result:
        conn.execute('INSERT INTO {} (name, version, rdep, bdep, redep, cdep) VALUES (?, ?, ?, ?, ?, ?)'.format(dbtable), res)
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
    ''' Compare version

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


def get_deps_from_db_deep(pkg, dep_type, dbfile=DEPEND_DB, dbtable=DEPEND_DB_TABLE):
    ''' Get build-time dependency from dbfile

    Args:
      dep_type: string, type of dependency 'bdep'
      pkg: string, name of package
      dbfile: dbfile

    Returns:
      list: contains string items

    '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    
    def _do_get(inlist):
        result = []
        for pkg in inlist:
            cur.execute("SELECT {} FROM {} WHERE name = '{}'".format(dep_type, dbtable, pkg))
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
    ''' Instead of actually build, display what to do.

    These flag means:
     [N] -- new install
     [U] -- upgrade
     [D] -- downgrade
     [E] -- same version

    '''
    flag = ''
    if INSTALL_FORCE:
        flag = 'F'

    bdeps = get_deps_from_db_deep(pkg, dep_type='bdep')

    for bdep in bdeps:
        version = pbslib[bdep][-1]
        installed_info = ybsutils.is_installed(bdep)
        if installed_info:
            installed_version = installed_info[1]
            ret = ybsutils.compare_version(version, installed_version)
            if ret == '=':
                if IS_VERBOSE or INSTALL_FORCE:
                    print('[{}] {} {}'.format('E'+flag, bdep, version))
            if ret == '<':
                print('[{}] {} {} -> {}'.format('U'+flag, bdep, installed_version, version))
            if ret == '>':
                print('[{}] {} {} -> {}'.format('D'+flag, bdep, installed_version, version))
        else:
            print('[{}] {} {}'.format('N'+flag, bdep, version))


def main():
    argvs = sys.argv[1:]
    if not argvs:
        argvs = ['-h']

    parser = argparse.ArgumentParser(description='Backend of ybs')
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
                        dest='t', help='show information of package installed')
    parser.add_argument('-s', '--search', nargs='*', metavar='pkg',
                        dest='s', help='search package in pbslib')
    parser.add_argument('-p', '--pretend', nargs='*', metavar='pkg',
                        dest='p', help='instead of actually build, display what to do')
    parser.add_argument('-w', '--showpbs', nargs='*', metavar='pkg',
                        dest='w', help='show available pbsfile in pbsdir')
    parser.add_argument('-gr', '--get_rdeps', nargs='*', metavar='pkg',
                        dest='gr', help='show run-time dependency of package')
    parser.add_argument('-grd', '--get_rdeps_deep', nargs='*', metavar='pkg',
                        dest='grd', help='show run-time dependency tree of package')
    parser.add_argument('-gb', '--get_bdeps', nargs='*', metavar='pkg',
                        dest='gb', help='show build-time dependency of package')
    parser.add_argument('-gbd', '--get_bdeps_deep', nargs='*', metavar='pkg',
                        dest='gbd', help='show build-time dependency tree of package')
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
        ybs_update_db()

    if args.l:
        pbslib_map = ybsutils.parse_pbslib(PBSLIB_PATH)
        ybs_list_available(pbslib_map)

    if args.L:
        ybs_list_installed()

    if args.cv:
        x, y = args.cv
        print(ybs_compare_version(x, y))

    if args.w:
        pbslib_map = ybsutils.parse_pbslib(PBSLIB_PATH)
        for pkg in args.w:
            print(ybs_showpbs(pkg, pbslib_map))

    if args.s:
        pbslib_map = ybsutils.parse_pbslib(PBSLIB_PATH)
        for pkg in args.s:
            ybs_search(pkg, pbslib_map)

    if args.p:
        pbslib_map = ybsutils.parse_pbslib(PBSLIB_PATH)
        for pkg in args.p:
            ybs_pretend(pkg, pbslib_map)

    if args.t:
        for pkg in args.t:
            ybs_status(pkg)
    
    if args.gb:
        ybs_init_db()
        for pkg in args.gb:
            for x in get_deps_from_db(pkg, dep_type='bdep'):
                print(x),
    
    if args.gbd:
        ybs_init_db()
        for pkg in args.gbd:
            for x in get_deps_from_db_deep(pkg, dep_type='bdep'):
                print(x),

    if args.gr:
        ybs_init_db()
        for pkg in args.gr:
            for x in get_deps_from_db(pkg, dep_type='rdep'):
                print(x),
    
    if args.grd:
        ybs_init_db()
        for pkg in args.grd:
            for x in get_deps_from_db_deep(pkg, dep_type='rdep'):
                print(x),

    if args.wr:
        ybs_init_db()
        for pkg in args.wr:
            print('{} is related with:\n'.format(pkg))
            ybs_whatrequires(pkg)


if __name__ == '__main__':
    main()
