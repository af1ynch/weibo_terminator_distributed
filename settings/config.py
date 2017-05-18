# -*- coding: utf-8 -*-
# file: settings.py
# author: JinTian
# time: 13/04/2017 10:10 AM
# Copyright 2017 JinTian. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------
"""
all configurations set here, follow the instructions
"""

# you should not change this properly
# DEFAULT_USER_ID = '5670158492'
DEFAULT_USER_ID = '3217179555'
# DEFAULT_USER_ID = '6202737026'
LOGIN_URL = 'https://passport.weibo.cn/signin/login'
#
# change this to your Chromedirver unzip path, point to bin/chromedriver executable file, full path
# PHANTOM_JS_PATH = '/Users/jintian/phantomjs-2.1.1-macosx/bin/phantomjs'
PHANTOM_JS_PATH = 'D:/phantomjs-2.1.1-windows/bin/phantomjs.exe'
CHROME_PATH = 'D:/Program Files (x86)/chromedriver_win32/chromedriver.exe'


COOKIES_SAVE_PATH = 'settings/cookies.pkl'
CORPUS_SAVE_DIR = 'scraped_corpus/'
DISTRIBUTE_IDS = 'distribute_ids.pkl'
SCRAPED_MARK = 'settings/scraped.mark'

# set redis host and port
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_KEY_NAMESPACE = 'twitter'
REDIS_SCHEDULE_KEY = 'new_uid'
REDIS_DUPEFILTER_KEY = 'crawled_uid'

# # set print colors
# ERROR_COLOR = '\033[5;31m'
# SUCCESS_COLOR = '\033[5;34m'
# DEBUG_COLOR = '\033[5;32m'
