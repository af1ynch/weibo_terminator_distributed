# -*- coding:utf-8 -*-

"""
@version: 
@author: lynch
@contact: 
@site: https://github.com/af1ynch
@software: PyCharm
@file: main.py
@time: 2017/5/3 18:44
"""

from optparse import OptionParser
from core import Dispatcher
from settings.config import DEFAULT_USER_ID

usage = 'usage: python3 %prog [options] arg1 arg2'
parser = OptionParser()
parser.add_option('-i', '--id',
                  default=DEFAULT_USER_ID,
                  help='set user id, default=DEFAULT_USER_ID')
parser.add_option('-f', '--filter',
                  default='0',
                  help='set tweet filter flag. if filter is 1, then tweet are all original, '
                       'if 0, tweet contains repost one. default is 0')
parser.add_option('-d', '--debug',
                  default='0',
                  help='debug mode for develop. set 1 on, set 0 off. default is 0')

(options, args) = parser.parse_args()
if options.debug == '1':
    uid = options.id
    print('[debug mode] crawling tweet from id {}'.format(uid))
    dis_patcher = Dispatcher(uid=uid)
    dis_patcher.execute()
elif options.debug == '0':
    uid = options.id
    filter_flag = options.filter
    print('crawling tweet from id {}'.format(uid))
    dis_patcher = Dispatcher(uid=uid, filter_flag=filter_flag)
    dis_patcher.execute()
else:
    print('debug mode error, set 1 on, set 0 off.')
