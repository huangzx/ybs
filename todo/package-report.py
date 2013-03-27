#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# YPK 软件源 testing 目录监控报告
# 包含以下内容:
# 1. 放入 testing 目录, 超过 deadline_time (默认 14 天)的 ypk 包
# 2. testing 目录下和数据库内的 ypk 包数量
# 3. 过去 24 小时, 新加入 testing 目录的 ypk 包
# 
# 运行环境:
# 1. YPK 软件源服务器
# 2. crond 每日运行
# 3. 报告提交到 https://github.com/StartOS/package-report 
#

import os
import sys
import sqlite3
import time
import ybsutils

YPKDEST = '/var/ybs/packages/testing'
YPK_DB = '/tmp/package.db'
DEADLINE_TIME = 2


class PackageReport(object):
    '''

    '''
    def __init__(self, ypkdir, dbfile):
        ''' '''
        #
        # 测试目录下时候有 ypk 包
        self.ypks_in_dir = ybsutils.files_in_dir(ypkdir, '.ypk', 'version')
        if not self.ypks_in_dir:
            print ":( No ypk package found in '{}'".format(ypkdir)
            sys.exit(1)
        #
        # 连接数据库
        self.conn = sqlite3.connect(dbfile)
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS testing (path TEXT, intime INTEGER);")

    
    def _sync(self):
        ''' '''
        # 删除数据库内有, 但不存在 testing 目录的 ypk 包的记录
        # 即ypk 包已经从 testing 目录移出的情况
        self.cur.execute("SELECT path, intime from testing;")
        ypks = self.cur.fetchall()
        ypks_in_db = [ypk[0] for ypk in ypks]
        for ypk in ypks_in_db:
            if not ypk in self.ypks_in_dir:
                self.cur.execute("DELETE from testing WHERE path = '{}';".format(ypk))
                
    def _deadline(self):
        ''' '''
        #
        # 查找加入时间超过期限的 ypk 包
        self.cur.execute("SELECT path, intime from testing;")
        ypks = self.cur.fetchall()
        deadline_ypks = []
        for ypk, intime in ypks:
            if intime > DEADLINE_TIME:
                deadline_ypks.append((ypk.replace(YPKDEST + '/', ''), intime))
            else:
                self.cur.execute("UPDATE testing SET intime = intime+1 WHERE path = '{}';".format(ypk))
        
        total = len(deadline_ypks)
        
        if total:
            print '==> All packages in [testing] for more than {} days ({} total)'.format(DEADLINE_TIME, total)
            for ypk in deadline_ypks:
                path = ypk[0]
                day = ypk[1]
                since = time.strftime('%Y-%m-%d', time.localtime(time.time() - day * 24 * 60 * 60))
                print '{}: {} days, since {}'.format(path, day, since)
        
    
    def _news(self):
        ''' '''
        #
        # 查找过去 1 天, 新加入 testing 目录的 ypk 包
        self.cur.execute("SELECT path, intime from testing;")
        ypks = self.cur.fetchall()
        ypks_in_db = [ypk[0] for ypk in ypks]
        
        print '==> There are {} packages in [testing] currently.'.format(len(self.ypks_in_dir))
        print '==> There are {} packages in database.'.format(len(ypks_in_db))
        
        news_in_dir = set(self.ypks_in_dir) - set(ypks_in_db) 
     
        if news_in_dir:
            print '==> New packages in [testing] in last 24 hours ({} total)'.format(len(news_in_dir))
            for ypk in news_in_dir:
                print ypk.replace(YPKDEST + '/', '')
                self.cur.execute("INSERT INTO testing (path, intime) VALUES \
                            ('{}', '{}');".format(ypk, 0))

    def _close(self):
        ''' '''
        #
        # 写入并断开数据库连接
        self.conn.commit()
        self.conn.close()


if __name__ == '__main__':
    package_report = PackageReport(YPKDEST, YPK_DB)
    package_report._sync()
    package_report._deadline()
    package_report._news()
    package_report._close()
