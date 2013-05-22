#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright © 2013 ivali.com
# Author: Zhongxin Huang <zhongxin.huang@gmail.com>
#

import sys
import os
import sqlite3
import subprocess
from distutils.version import LooseVersion
import time
from hashlib import sha1, md5
from . import settings


def is_empty_dir(indir):
    ''' check if directory is empty, include sub directoris

    Args:
      indir: string, path to directory

    Returns:
      boolean value, True or False

    '''
    for root, dirs, files in os.walk(indir):
        if files:
            return False
    return True


def run_ypkg(cmd, para, extra_para=''):
    ''' run ypkg cli

    Args:
      cmd: string, cmd for ypkg, such as '-l'
      para: string, para for ypkg, such as pkgname 'leafpad'
      extra_para: string, extra para for ypkg, such '2 >/dev/null'

    Returns:
      tuple, contais two elements:
        first element is a list of ypkg output,
        second element is a integer, namely ypkg return code.
    
    To use:
      >>> import ybs.utils
      >>> test = ybs.utils.run_ypkg('-l', 'zlib')
      >>> print test # Omit redundant content for file list
      (['Contents of zlib 1.2.7:', 'D|      4096| /usr'], 0)
    
    '''
    while True:
        ypkg_cmd = 'ypkg ' + cmd + ' ' + para + ' ' + extra_para
        p = subprocess.Popen(ypkg_cmd, shell=True, stdout=subprocess.PIPE)
        # p.communicate method return a tuple like this:
        # (stdoutdata, stderrdata)
        stream = p.communicate()[0]
        ret = p.returncode
        if ret == 5:
            sys.stderr.write('database is locked')
            time.sleep(1)
        elif ret != 0:
            if '-l' in cmd or '--list-files' in cmd:
                sys.stderr.write("'{}' is not installed".format(para))
            else:
                sys.stderr.write("'{}' execution failed".format(ypkg_cmd))
            break
        elif ret == 0:
            break
    return ([x for x in stream.split('\n') if x.strip()], ret)


def what_time(value=None):
    '''

    '''
    if value is None:
        value = time.time()
    return time.strftime('%Y-%m-%d,%H:%M:%S', time.localtime(value))


def get_checksum(infile, tool):
    ''' get checksum of file

    Args:
      infile: string, path to file
      tool: string, md5 or sha1

    Return:
      string of checksum value

    To use:
      >>> import ybs.utils
      >>> ybs.utils.get_checksum('/tmp/test','sha1')
      'da39a3ee5e6b4b0d3255bfef95601890afd80709'
      >>> ybs.utils.get_checksum('/tmp/test','md5')
      'd41d8cd98f00b204e9800998ecf8427e'
    '''
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
    ''' get sha1sum of file

    Arg:
      infile: string, path to file

    Return:
      string of sha1sum value

    To use:
      >>> import ybs.utils
      >>> ybs.utils.get_sha1sum('/tmp/test')
      'da39a3ee5e6b4b0d3255bfef95601890afd80709'
    
    '''
    return get_checksum(infile, 'sha1')


def get_md5sum(infile):
    ''' get md5sum of file

    Arg:
      infile: string, path to file

    Return:
      string of md5sum value

    To use:
      >>> import ybs.utils
      >>> ybs.utils.get_md5sum('/tmp/test')
      'd41d8cd98f00b204e9800998ecf8427e'
    
    '''
    return get_checksum(infile, 'md5')


def is_pbsfile_likes(infile):
    ''' check whether infile is a valid pbsfile-likes or not

    pbsfile-likes, such as:
      mysql_5.5.29-x86_64.ypk
      mysql_5.5.29-i686.ypk
      mysql_5.5.29-any.ypk
      mysql_5.5.29.pbs
      mysql_5.5.29.xml
      mysql_5.5.29.ypk
      mysql_5.5.29-any.filelist

    Args:
      infile: string, path to file

    '''
    infile = os.path.basename(infile)
    suffixes = ('.pbs', '.ypk', '.xml', '.filelist')
    suffix = os.path.splitext(infile)[-1]
    if not suffix in suffixes:
        return False
    if '_' not in infile:
        return False
    return True


def installed_info(name, dbfile=settings.__package_db__, dbtable=settings.__package_db_table__):
    ''' show information of installed package from dbfile

    Args:
      name: string, package name
      dbfile: string, path to package.db which is created by ypkg
      dbtable: string, installed package table of debfile

    Returns:
      None or tuple, format is: (u'name', u'version', u'repo', install_time)
      For example:
        (u'firefox', u'19.0', u'stable', 1361523561)

    '''
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    cur.execute("SELECT name, version, repo, install_time FROM {} Where name='{}'".format(dbtable, name))
    # Use fetchone here, because installed package name is just only one.
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result


def compare_version(v1, v2):
    ''' version compare

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
      string. for example:
      v1 is less than v2, return '<'
      v1 is equal to v2, return '='
      v1 is greater then v2, return '>'

    To use:
      >>> import ybs.utils
      >>> ybs.utils.compare_version('2.0', '3.0')
      '<'
      >>> ybs.utils.compare_version('2.0', '1.0')
      '>'
      >>> ybs.utils.compare_version('2.0', '2.0')
      '='

    '''
    # Splite major and rel version
    v1 = str(v1.lower())
    v2 = str(v2.lower())
    v1_major = v1.split('-')[0]
    v1_rel = v1.split('-')[1:]
    v2_major = v2.split('-')[0]
    v2_rel = v2.split('-')[1:]

    # First, compare major version
    v1_major += '.0'
    v2_major += '.0'
    # Be sure compare two version with same length
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
        #return ret
        if ret == 1:
            return '>'
        if ret == -1:
            return '<'

    # Second, compare rel version

    def _replacement(inlist):
        inlist = [x.replace('alpha', 'a') for x in inlist]
        inlist = [x.replace('beta', 'b') for x in inlist]
        inlist = [x.replace('rc', 'c') for x in inlist]
        return inlist

    # Note:
    # rel version is a list
    v1_rel = _replacement(v1_rel)
    v2_rel = _replacement(v2_rel)

    # Be sure compare two version with same length
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
            #return ret
            if ret == 1:
                return '>'
            if ret == -1:
                return '<'
    #return 0
    return '='


class GetNameVersion(object):
    ''' get name, version and arch from pbs-likes file

    Args:
      infile: string, path to file

    Attributes:
      infile: string, file name
      arch: string, arch
      name: string, name
      version_major: string, version_major
      version_rel: string, version_rel
      version: string, version contains major and rel

    Methods:
      parse(self, infile)
        infile: string, path to file

    To use:
      >>> import ybs.utils
      >>> foo = ybs.utils.GetNameVersion()
      >>> foo.parse('mysql_5.5.29-1-rc1-x86_64.ypk')
      >>> foo.infile
      'mysql_5.5.29-1-rc1-x86_64.ypk'
      >>> foo.arch
      'x86_64'
      >>> foo.name
      'my_sql'
      >>> foo.version_major
      '5.5.29'
      >>> foo.version
      '5.5.29-1-rc1'
      >>> foo.version_rel
      '1-rc1'

    '''
    def __dir__(self):
        return ['infile', 'name', 'arch', 'version_major', 'version_rel', 'version']
    
    def __repr__(self):
        return "class '{}' for getting name, version or arch from pbsfile-likes file".format(self.__class__.__name__)

    __str__ = __repr__
    
    def parse(self, infile):
        self.infile = os.path.basename(infile)

        if is_pbsfile_likes(infile):
            # Strip suffix (.*)
            infile = os.path.splitext(self.infile)[0]
        
        ret = infile.split('-')
        arches = ('i686', 'x86_64', 'any')
        arch = ''
        for x in arches:
            if x == ret[-1]:
                arch = x
                break
        if arch:
            infile = '-'.join(infile.split('-')[0:-1])

        infile = infile.split('_')
        name = '_'.join(infile[0:-1])
        version = infile[-1]
        version_major = version.split('-')[0]
        version_rel = '-'.join(version.split('-')[1:])

        self.arch = arch
        self.name = name
        self.version_major = version_major
        self.version_rel = version_rel
        self.version = version_major + version_rel
        if version_rel:
            self.version = version_major + '-' + version_rel


def xfiles_in_dir(indir, suffix=None, type_='file'):
    ''' find all the files in directory
    
    you can specify suffix as '.xx' or type as one of 'file' and 'link'
    
    Args:
      indir: string, path to directory
      type: string, type of file, such as: file, link
      suffix: string, the suffix of file

    Returns:
      yield generator

    '''
    res = ''
    if not is_empty_dir(indir):
        for root, dirs, files in os.walk(indir):
            for file_ in files:
                absfile = (os.path.join(root, file_))
                if type_ == 'file' and os.path.isfile(absfile):
                    res = absfile
                if type_ == 'link' and os.path.islink(absfile):
                    res = absfile
                if res:
                    if suffix is not None:
                        if res.endswith(suffix):
                            yield res
                    else:
                        yield res


def pkgs_in_dir(indir, suffix, filter_by=None):
    ''' find all the files with suffix in directory.

    Args:
      indir: string, path to directory
      suffix: the suffix of file
      filte: show the max version of file

    Return:
      A list of absolute path to files

    To use:
      >>> import ybs.utils
      >>> ybs.utils.pkgs_in_dir('/tmp/test', '.ypk')
      ['/tmp/test/HTML-Parser_3.69-x86_64.ypk', '/tmp/test/HTTP-Cookies_6.01-any.ypk']

    '''
    result = [x for x in xfiles_in_dir(indir, suffix)]
    if filter_by is None:
        return result
    if filter_by == 'version':
        result_filter = {}
        record = {}
        pbsfile = PbsFile()
        for f in result:
            pbsfile.parse(f)
            name, version = pbsfile.name, pbsfile.version
            if name in record:
                if compare_version(version, record[name]) != '>':
                    continue
            result_filter[name] = f
            record[name] = version
        return [x for x in result_filter.viewvalues()]


def file_in_dir(indir, filename):
    ''' find single file specified in directory

    Args:
      indir: string, path to directory
      filename: string, filename

    Return:
      list of abspath to files

    To use:
      >>> import ybs.utils
      >>> ybs.utils.file_in_dir('/tmp/test, 'HTML-Parser_3.69-x86_64.ypk')
      ['/var/ybs/packages/h/HTML-Parser/HTML-Parser_3.69-x86_64.ypk']

    '''
    for root, dirs, files in os.walk(indir):
        for f in files:
            if f == filename:
                return os.path.join(root, f)


def parse_pbslib(indir, suffix='.pbs'):
    ''' find all the pbsfile in given directory

    Arg:
      indir: string, path to directory

    Return:
      dict mapping, keys are package names, value are versions in ascending order

    To use:
      >>> import ybs.utils
      >>> ybs.utils.parse_pbslib('/var/ybs/pbslib')
      {'gtk-vnc': ['0.5.1-rc1','0.5.1','0.5.2'], 'epdfview': ['0.1.7']}

    '''
    pbsfiles = {}
    pbsfile = PbsFile()
    for f in pkgs_in_dir(indir, suffix):
        pbsfile.parse(f)
        name, version = pbsfile.name, pbsfile.version
        if name in pbsfiles:
            pbsfiles[name].append(version)
        else:
            pbsfiles[name] = [version]
    # Return pbsfiles
    for item in pbsfiles:
        item_versions = pbsfiles[item]
        pbsfiles[item] = sorted_version(item_versions)
    return pbsfiles


def minimum_version(inlist):
    ''' find minimum value in list of versions

    Arg:
      list of versions

    Return:
      string of mininum version

    To use:
      >>> import ybs.utils
      >>> ybs.utils.minimum_version(['1', '3', '2', '1-rc1'])
      '1-rc1'

    '''
    result = inlist[0]
    for i in inlist:
        ret = compare_version(i, result)
        if ret == '<':
            result = i
    return result


def sorted_version(inlist):
    ''' sorted version

    Arg:
      list of version

    Return:
      list of sorted version

    To use:
      >>> import ybs.utils
      >>> ybs.utils.sorted_version(['1', '1-rc1', '1-r1'])
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
    ''' pbsfile class

    Attributes:
      path: string, path to pbsfile
      basename: string, name of pbsfile
      dirname: string, dirname of pbsfile
      name: string, name of package
      version: string, main version of package
      version_rel: string, rel version of package

    Methods:
      parse: 
      get: get value of pbsfile

    To Use:
      >>> import ybs.utils
      >>> pbsfile = ybs.utils.PbsFile()
      >>> pbsfile.parse('/var/ybs/pbslib/sys-apps/ypkg2/ypkg2_20130217-rc1.pbs')
      >>> pbsfile.path
      '/var/ybs/pbslib/sys-apps/ypkg2/ypkg2_20130217.pbs'
      >>> pbsfile.basename
      'ypkg2_20130217.pbs'
      >>> pbsfile.dirname
      '/var/ybs/pbslib/sys-apps/ypkg2'
      >>> pbsfile.name
      'ypkg2'
      >>> pbsfile.version
      '20130217-rc1'
      >>> pbsfile.version_major
      '20130217'
      >>> pbsfile.version_rel
      '-rc1'
      >>> pbsfile.get('RDEPEND')
      ['libarchive(>=3.0.4)', 'curl', 'pcre', 'sqlite', 'rtmpdump', 'nettle']
      >>> pbsfile.get('LICENSE')
      ['GPL,LGPL']

    '''
    def __dir__(self):
        return ['path', 'basename', 'dirname', 'name', 'version', 'version_major', 'version_rel']

    def __repr__(self):
        return "class '{}' for parsing pbsfile".format(self.__class__.__name__)

    __str__ = __repr__
    
    def parse(self, infile):
        self.path = os.path.realpath(infile)
        self.basename = os.path.basename(infile)
        self.dirname = os.path.dirname(infile)
        get = GetNameVersion()
        get.parse(infile)
        self.name = get.name
        self.version_major = get.version_major
        self.version_rel = get.version_rel
        self.version = get.version
   
    def get(self, item):
        cmd = ['dosource', self.path, self.name, self.version_major, self.version_rel]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        for line in proc.stdout:
            line = line.strip()
            (key, _, value) = line.partition("=")
            if item == key:
                return value.split()
