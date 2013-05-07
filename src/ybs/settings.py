#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright © 2013 ivali.com
# Author: Zhongxin Huang <zhongxin.huang@gmail.com>
#

__version__ = '2.0'
__package_db__ = '/var/ypkg/db/package.db'
__package_db_table__ = 'world'
__depend_db__ = '/var/ybs/db/depend.db'
__depend_db_table__ = 'universe'
__ybs_conf__ = '/etc/ybs.conf'


class YbsConf(object):
    ''' ybs config class

    Attributes:
      path: string, path to ybs config file

    Methods:
      parse: parse ybs config file
      get: get value of ybs config file

    To Use:
      >>>import ybs.utils
      >>>ybsconf = ybs.utils.YbsConf()
      >>>ybsconf.parse('/etc/ybs.conf')
      >>>ybsconf.path
      '/etc/ybs.conf'
      >>>ybsconf.get('ARCH')
      'x86_64'

    '''
    def __init__(self):
        pass

    def parse(self, infile=__ybs_conf__):
        self.path = infile

    def get(self, item):
        with open(self.path, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '#' in line:
                    line = line[0:line.index('#')]
                (key, _, value) = line.partition("=")
                if item == key:
                    return value.strip('"')
            return None

ybsconf = YbsConf()
ybsconf.parse(__ybs_conf__)
__pbslib_path__ = ybsconf.get('PBSLIB_PATH')
__arch__ = ybsconf.get('ARCH')
