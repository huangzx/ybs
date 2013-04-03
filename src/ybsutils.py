#!/usr/bin/env python
# -*- coding: utf8 -*-

#   Copyright © 2012 ivali.com
#   Maintainer: Zhongxin Huang <huangzhongxin@ivali.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os
import signal
import sqlite3


def signal_int():
    ''' signal SIGINT handler
    '''
    def _signal_handler():
        sys.stderr.write('You pressed Ctrl+C!')
        sys.exit(1)
    signal.signal(signal.SIGINT, _signal_handler)


def is_installed(name):
    '''
    Args:
      name: A string of pkgname
    
    Returns:
      None or tuple, format is: (u'name', u'version', u'repo', install_time)
      For example:
        (u'firefox', u'19.0', u'stable', 1361523561)

    '''
    world = '/var/ypkg/db/package.db'
    conn = sqlite3.connect(world)
    cursor = conn.cursor()
    cursor.execute("SELECT name, version, repo, install_time FROM \
                world Where name='{}'".format(name))
    # Use fetchone here, because package's name is just only one. 
    result = cursor.fetchone()
    conn.close()
    return result


def compare_version(v1, v2):
    '''version compare

    Args:
      v1, v2: Two strings of version, for example:
      '2.0', '3.0'
      '2.0', '1.0'
      '2.0', '2.0'
      '2.0', '2.0-alpha'
      '2.0', '2.0-beta'
      '2.0', '2.0-rc'
      '2.0', '2.0-r'
      human readable: alpha < beta < rc < r

    Returns:
      A integer value. for example:
      v1 is less than v2, return -1
      v1 is equal to v2, return 0
      v2 is greater then v2, return 1

    To use:
      >>>import ybsutils
      >>>ybsutils.compare_version('2,0', '3.0')
      -1

    '''
    from distutils.version import LooseVersion

    # splite major and rel version
    v1 = v1.lower()
    v2 = v2.lower()
    v1_major = v1.split('-')[0]
    v1_rel = v1.split('-')[1:]
    v2_major = v2.split('-')[0]
    v2_rel = v2.split('-')[1:]
    # first, compare major version
    v1_major += '.0'
    v2_major += '.0'
    # be sure compare two version with same length
    v1_major_len = len(v1_major.split('.'))
    v2_major_len = len(v2_major.split('.'))
    more = v1_major_len - v2_major_len
    if more > 0:
        v2_major += '.0' * abs(more)
    else:
        v1_major += '.0' * abs(more)
    _cmp = lambda x, y: LooseVersion(x).__cmp__(y)
    ret = _cmp(v1_major, v2_major)
    if ret != 0:
        return ret
    # second, compare rel version
    # note that, rel version is a list

    def _replacement(inlist):
        inlist = [x.replace('alpha', 'a') for x in inlist]
        inlist = [x.replace('beta', 'b') for x in inlist]
        inlist = [x.replace('rc', 'c') for x in inlist]
        return inlist

    v1_rel = _replacement(v1_rel)
    v2_rel = _replacement(v2_rel)
    # be sure compare two version with same length
    v1_rel_len = len(v1_rel)
    v2_rel_len = len(v2_rel)
    more = v1_rel_len - v2_rel_len
    absmore = abs(more)
    if more > 0:
        while absmore > 0:
            v2_rel.append('r0')
            absmore -= 1
    else:
        while absmore > 0:
            v1_rel.append('r0')
            absmore -= 1
    for x, y in zip(v1_rel, v2_rel):
        ret = _cmp(x, y)
        if ret != 0:
            return ret
    return 0


def get_name_version(infile, fm='class'):
    '''get name and version from ypk-file

    Args:
      infile: The path to ypk-file, format is: name_version-relversion-arch.pbs
        For examples:
        mysql_5.5.29-x86_64.ypk
        mysql_5.5.29-i686.ypk
        mysql_5.5.29-any.ypk
        mysql_5.5.29.pbs
        mysql_5.5.29.xml
        mysql_5.5.29.ypk

      fm: format of return value: class or raw
        class: ['name', 'version']
        raw: ['name', 'version', 'relversion']

    Returns:
        A list with two items, see above.
 
    To use:
      >>>import ybsutils
      >>>ybsutils.get_name_version('mysql_5.5.29.pbs')
      ['mysql', '5.5.29']
      >>>ybsutils.get_name_version('mysql_5.5.29-rc1.pbs', fm='raw')
      ['mysql', '5.5.29', '-rc1']

    '''
    infile = os.path.basename(infile)
    arches = ('-i686', '-x86_64', '-any')
    suffixes = ('.pbs', '.ypk', '.xml', '.filelist')
    for i in suffixes + arches:
        infile = (lambda x: infile.replace(x, ''))(i)
    infile = infile.split('_')
    name, version = '_'.join(infile[0:-1]), infile[-1]
    if fm == 'class':
        return [name, version]
    elif fm == 'raw':
        if '-' in version:
            version = version.split('-')
            version, relversion = version[0], '-' + '-'.join(version[1:])
            return [name, version, relversion]
        else:
            return [name, version, '']


def get_checksum(infile, tool):
    '''get checksum of file

    Args:
      infile: The path to file
      tool: Two common checksum tools: md5, sha1

    Return:
      A string of checksum value
    
    To use:
      >>>import ybsutils
      >>>ybsutils.get_checksum('/tmp/test','sha1')
      'da39a3ee5e6b4b0d3255bfef95601890afd80709'
      >>>ybsutils.get_checksum('/tmp/test','md5')
      'd41d8cd98f00b204e9800998ecf8427e'
    '''
    from hashlib import sha1, md5
    
    try:
        with open(infile, 'rb') as fd:
            if tool == 'sha1':
                sha1sum = sha1()
                sha1sum.update(fd.read())
                return sha1sum.hexdigest()
            if tool == 'md5':
                md5sum = md5()
                md5sum.update(fd.read())
                return md5sum.hexdigest()
    except IOError:
        pass


def get_sha1sum(infile):
    '''get sha1sum of file
 
    Arg:
      infile: A string of path to file
    
    Return:
      A string of sha1sum value
    
    To use:
      >>>import ybsutils
      >>>ybsutils.get_sha1sum('/tmp/test')
      'da39a3ee5e6b4b0d3255bfef95601890afd80709'
    
    '''
    
    return get_checksum(infile, 'sha1')


def get_md5sum(infile):
    '''get md5sum of file
    
    Arg:
      infile: A string of path to file
    
    Return:
      A string of md5sum value
    
    To use:
      >>>import ybsutils
      >>>ybsutils.get_md5sum('/tmp/test')
      'd41d8cd98f00b204e9800998ecf8427e'
    
    '''
    return get_checksum(infile, 'md5')


def files_in_dir(indir, suffix, filte=None):
    '''find all the files with suffix in directory.

    Args:
      indir: A string of path to directory
      suffix: The suffix of file
      filte: Show the max version of file
    
    Return:
      A list of absolute path to files

    To use:
      >>>import ybsutils
      >>>ybsutils.files_in_dir('/tmp/test', '.ypk')
      ['/tmp/test/HTML-Parser_3.69-x86_64.ypk', '/tmp/test/HTTP-Cookies_6.01-any.ypk']
    
    '''
    result = []
    for root, dirs, files in os.walk(indir):
        for f in files:
            if f.endswith(suffix):
                result.append(os.path.join(root, f))
    if filte is None:
        return result
    if filte == 'version':
        pbsfile = PbsFile()
        result_filter = {}
        record = {}
        for f in result:
            pbsfile.parse(f)
            name, version = pbsfile.name, pbsfile.version + pbsfile.relversion
            if name in record:
                if compare_version(version, record[name]) != 1:
                    continue
            result_filter[name] = f
            record[name] = version
        return [x for x in result_filter.viewvalues()]        
           

def file_in_dir(indir, filename):
    '''find single file specified in dir 
    
    Args:
      indir: A string of path to directory
      filename: A string of filename
    
    Return:
      A list of abspath to files
    
    To use:
      >>>import ybsutils
      >>>ybsutils.file_in_dir('/tmp/test, 'HTML-Parser_3.69-x86_64.ypk')
      ['/var/ybs/packages/h/HTML-Parser/HTML-Parser_3.69-x86_64.ypk']
    
    '''
    for root, dirs, files in os.walk(indir):
        for f in files:
            if f == filename:
                return os.path.join(root, f)


def parse_pbslib(indir, suffix='.pbs'):
    '''find all the pbs-files in given directory

    Arg:
      indir: A string of path to directory
    
    Return:
      A dict mapping keys to pbs-name, values to version.
      
      A sorted list of versions.

    To use:
      >>>import ybsutils
      >>>ybsutils.parse_pbslib('/var/ybs/pbslib')
      {'gtk-vnc': ['0.5.1-rc1','0.5.1','0.5.2'], 'epdfview': ['0.1.7']}
   '''
    pbsfiles = {}
    
    for f in files_in_dir(indir, suffix):
        pbsfile = PbsFile()
        pbsfile.parse(f)
        name, version = pbsfile.name, pbsfile.version + pbsfile.relversion
        if name in pbsfiles:
            pbsfiles[name].append(version)
        else:
            pbsfiles[name] = [version]
    #return pbsfiles
    for item in pbsfiles:
        item_versions = pbsfiles[item]
        pbsfiles[item] = sorted_version(item_versions)
    
    return pbsfiles


def minimum_version(inlist):
    ''' find minimum value in list of versions
    
    Arg:
      A list of versions

    Return:
      A string of mininum version

    To use:
      >>>import ybsutils
      >>>ybsutils.minimum_version(['1', '3', '2', '1-rc1'])
      '1-rc1'
    '''
    result = inlist[0]
    for i in inlist:
        ret = compare_version(i, result)
        if ret == -1:
            result = i
    return result


def sorted_version(inlist):
    ''' sorted version 
    
    Arg:
      A list of version
    
    Return:
      A list of sorted version

    To use:
      >>>import ybsutils
      >>>ybsutils.sorted_version(['1', '1-rc1', '1-r1'])
      ['1-rc1', '1', '1-r1']
    '''
    result = []
    length = len(inlist)
    if length == 1 or length == 0:
        return inlist
    elif length > 1:
        while inlist:
            ret = minimum_version(inlist)
            result.append(ret)
            inlist.remove(ret)
    return result     


class PbsFile(object):
    '''pbsfile class
    
    Attributes:
      path: A string of path to pbsfile
      basename: A string of name of pbsfile
      dirname: A string of dirname of pbsfile
      name: A string of name of package with pbsfile
      version: A string of version of package with pbsfile
      relversion: A string of version of package with pbsfile
    
    Methods:
      parse: Parse a pbsfile
      get: Get value of pbsfile
    
    To Use:
      >>>import ybsutils
      >>>pbsfile = ybsutils.PbsFile()
      >>>pbsfile.parse('/var/ybs/pbslib/sys-apps/ypkg2/ypkg2_20130217.pbs')
      >>>pbsfile.path
      '/var/ybs/pbslib/sys-apps/ypkg2/ypkg2_20130217.pbs'
      >>>pbsfile.basename
      'ypkg2_20130217.pbs'
      >>>pbsfile.dirname
      '/var/ybs/pbslib/sys-apps/ypkg2'
      >>>pbsfile.name
      'ypkg2'
      >>>pbsfile.version
      '20130217'
      >>>pbsfile.get('RDEPEND')
      ['libarchive(>=3.0.4)', 'curl', 'pcre', 'sqlite', 'rtmpdump', 'nettle']
      >>>pbsfile.get('LICENSE')
      ['GPL,LGPL']
    '''
    def __init__(self):
        pass
    
    def __dir__(self):
        return ['path', 'basename', 'dirname', 'name', 'version', 'relversion']

    def parse(self, infile):
        self.path = infile
        self.basename = os.path.basename(infile)
        self.dirname = os.path.dirname(infile)
        self.name, self.version, self.relversion = get_name_version(infile, 'raw')

    def get(self, item):
        import subprocess
        cmd = ['dosource', self.path, self.name, self.version, self.relversion]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        for line in proc.stdout:
            line = line.strip()
            (key, _, value) = line.partition("=")
            if item == key:
                return value.split()


class YbsConf(object):
    ''' '''
    def __init__(self):
        pass

    def parse(self, infile):
        self.path = infile

    def get(self, item):
        with open(self.path, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if not len(line) or line.startswith('#'):
                    continue
                if '#' in line:
                    line = line[0:line.index('#')]
                length = len(item)
                key = line[0:length]
                if item == key:
                    value = line[len(key)+1:]
                    return value.strip('"')
