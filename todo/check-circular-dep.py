#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys
import sqlite3
import argparse

DEPEND_DB = '/var/ybs/db/depend.db'


def check_circular(pkg):
        ''' '''
        conn = sqlite3.connect(DEPEND_DB)
        cur = conn.cursor()
        
        def _get_rdep(pkg):
            cur.execute("SELECT {} FROM universe WHERE name = '{}'".format('rdep', pkg))
            results = cur.fetchone()
            if results:
                results = [x.split('(')[0] for x in results[0].split()]
            return results
        
        previous = [pkg]
        print previous
        for i in range(10):
            current = []
            for x in previous:
                a = _get_rdep(x)
                if a:
                    current.extend(a)
                    print a,
                else:
                    current.append('')
                    print [],
            print '\n'
            previous = current
        
        conn.close()


if __name__  == '__main__':
    argvs = sys.argv[1:]
    if not argvs:
        argvs = ['-h']
    desc = 'checking for circular dependency of package.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('pkg', nargs='*', help='pkg name')
    args = parser.parse_args(argvs)
    if args.pkg:
        for pkg in args.pkg:
            check_circular(pkg)
