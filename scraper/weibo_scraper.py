# -*- coding: utf-8 -*-
# file: sentence_similarity.py
# author: JinTian
# time: 24/03/2017 6:46 PM
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
using guide:
setting accounts first:

under: weibo_terminator/settings/accounts.py
you can set more than one accounts, WT will using all accounts one by one,
if one banned, another will move on.

if you care about security, using subsidiary accounts instead.

"""
import re
import sys
import os
import requests
from lxml import etree
import traceback
from settings.config import *
from utils import RedisQueue
import pickle
import time
import codecs
import logging
import numpy as np


class WeiBoScraper(object):

    def __init__(self, using_account, uuid, filter_flag=0):
        """
        uuid user id, filter flag indicates wei bo type
        :param uuid:
        :param filter_flag:
        """
        self.using_account = using_account
        self.cookie = dict()
        self._init_cookies()
        self._init_headers()

        self.user_id = uuid
        self.filter = filter_flag
        self.user_name = ''
        self.tweets_num = 0
        self.wei_bo_scraped = 0
        self.following = 0
        self.followers = 0
        self.wei_bo_content = []
        self.num_zan = []
        self.num_forwarding = []
        self.num_comment = []
        self.wei_bo_detail_urls = []
        self.uid_queue = RedisQueue(REDIS_SCHEDULE_KEY)
        self.has_crawled_queue = RedisQueue(REDIS_DUPEFILTER_KEY)

        self.tweet_save_file = os.path.join(CORPUS_SAVE_DIR, 'weibo_content.pkl')
        self.tweet_and_comment_save_file = os.path.join(CORPUS_SAVE_DIR, 'weibo_content_and_comment.pkl')
        self.fans_save_file = os.path.join(CORPUS_SAVE_DIR, 'weibo_fans.pkl')

    def _init_cookies(self):
        try:
            with open(COOKIES_SAVE_PATH, 'rb') as f:
                cookies_dict = pickle.load(f)
            cookies_string = cookies_dict[self.using_account]
            cookie = {
                "Cookie": cookies_string
            }
            print('setting cookie..')
            self.cookie = cookie
        except FileNotFoundError:
            print('have not get cookies yet.')

    def _init_headers(self):
        """
        avoid span
        :return:
        """
        headers = requests.utils.default_headers()
        user_agent = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko/20100101 Firefox/11.0'
        }
        headers.update(user_agent)
        self.headers = headers

    def crawl(self):
        # this is the most time-cost part, we have to catch errors, return to dispatch center
        try:
            self._get_html()
            self._get_user_name()
            self._get_user_info()

            self._get_following_id()
            self._get_wei_bo_content()
            self._get_wei_bo_content_and_comment()
            print(' SUCCESS CRAWL TWITTER USER: {}'.format(self.user_id))
            return True
        except Exception as e:
            print(' ERROR: {}'.format(e))
            print(' current account maybe was banned, return to dispatch center, resign for new account..')
            return False

    def _get_html(self):
        try:
            url = 'http://weibo.cn/%s?filter=%s&page=1' % (self.user_id, self.filter)
            print(url)
            self.html = requests.get(url, cookies=self.cookie, headers=self.headers).content
            print('success load html..')
        except Exception as e:
            print(e)

    def _get_user_name(self):
        print('\n' + '-'*30)
        print('getting user name')
        try:
            selector = etree.HTML(self.html)
            user_name = selector.xpath('//table//div[@class="ut"]/span[1]/text()')
            if user_name:
                self.user_name = user_name[0].split('\xa0')[0]
                print('current user name is: {}'.format(self.user_name))
        except Exception as e:
            print(e)
            print('html not properly loaded, maybe cookies out of date or account being banned. '
                  'change an account please')
            # exit()

    def _get_user_info(self):
        print('\n' + '-' * 30)
        print('getting user info')
        selector = etree.HTML(self.html)
        pattern = r"\d+\.?\d*"
        str_wb = selector.xpath('//span[@class="tc"]/text()')[0]
        g_uid = re.findall(pattern, str_wb, re.S | re.M)
        for value in g_uid:
            num_wb = int(value)
            break
        self.tweets_num = num_wb

        str_gz = selector.xpath("//div[@class='tip2']/a/text()")[0]
        g_uid = re.findall(pattern, str_gz, re.M)
        self.following = int(g_uid[0])

        str_fs = selector.xpath("//div[@class='tip2']/a/text()")[1]
        g_uid = re.findall(pattern, str_fs, re.M)
        self.followers = int(g_uid[0])
        print('current user has posted {} tweets, following {}, followers {}'.format(self.tweets_num, self.following,
                                                                                     self.followers))
    # def _get_more_ids(self):
    #     print('-- get follow people uid')
    #     url = 'https://weibo.cn/{}/follow'.format(self.user_id)
    #     follow_page = requests.get(url, cookies=self.cookie, headers=self.headers)
    #     if follow_page.status_code == 200:
    #         selector = etree.HTML(follow_page.content)
    #         following = selector.xpath(
    #             'body//table/tr/td/a[text()="\u5173\u6ce8\u4ed6" or text()="\u5173\u6ce8\u5979"]/@href')
    #         # check if has follows or fans
    #         if len(following):
    #             new_user_ids = re.findall('uid=(\d+)', ";".join(following), re.S)
    #         print('--- get {} people uid'.format(len(new_user_ids)))
    #     for uid in new_user_ids:
    #         self.uid_queue.set_add(uid)

    def _get_following_id(self):
        """
        This method can get more ids to scrap
        :return:
        """
        print('\n' + '-' * 30)
        print('getting following ids...')
        print(self.user_name + 'has followed {} people.'.format(self.following))
        if self.following < 1:
            pass
        else:
            following_ids = []
            if os.path.exists(self.fans_save_file):
                with codecs.open(self.fans_save_file, 'rb') as f:
                    following_ids = pickle.load(f)

            follow_url = 'https://weibo.cn/{}/follow?'.format(self.user_id)
            print(follow_url)
            html_fans = requests.get(follow_url, cookies=self.cookie, headers=self.headers).content
            selector = etree.HTML(html_fans)
            try:
                if selector.xpath('//input[@name="mp"]') is None:
                    page_num = 1
                else:
                    page_num = int(selector.xpath('//input[@name="mp"]')[0].attrib['value'])
                print('all fans have {} pages.'.format(page_num))

                try:
                    for i in range(1, page_num+1):
                        if i % 5 == 0 and i != 0:
                            print('[REST] rest for cheating....')
                            time.sleep(20)
                        fans_url_child = 'https://weibo.cn/{}/fans?page={}'.format(self.user_id, i)
                        print('requesting fans url: {}'.format(fans_url_child))
                        html_child = requests.get(fans_url_child, cookies=self.cookie, headers=self.headers).content
                        selector_child = etree.HTML(html_child)
                        fans_ids_content = selector_child.xpath(
                            'body//table/tr/td/a[text()="\u5173\u6ce8\u4ed6" or text()="\u5173\u6ce8\u5979"]/@href')
                        ids = re.findall('uid=(\d+)', ";".join(fans_ids_content), re.S)
                        ids = list(set(ids))
                        for d in ids:
                            print('appending fans id {}'.format(d))
                            self.uid_queue.set_add(d)
                            following_ids.append(d)
                except Exception as e:
                    print('error: ', e)
                    dump_follow_list = list(set(following_ids))
                    print(dump_follow_list)
                    with codecs.open(self.fans_save_file, 'wb') as f:
                        pickle.dump(dump_follow_list, f)
                    print('fans ids not fully added, but this is enough, saved into {}'.format(
                        self.fans_save_file))
                dump_follow_list = list(set(following_ids))
                print(dump_follow_list)
                with codecs.open(self.fans_save_file, 'wb') as f:
                    pickle.dump(dump_follow_list, f)
                print('successfully saved fans id file into {}'.format(self.fans_save_file))

            except Exception as e:
                logging.error(e)

    def _get_wei_bo_content(self):
        print('\n' + '-' * 30)
        print('getting wei bo content...')
        selector = etree.HTML(self.html)
        try:
            if not selector.xpath('//input[@name="mp"]'):
                page_num = 1
            else:
                page_num = int(selector.xpath('//input[@name="mp"]')[0].attrib['value'])
            pattern = r"\d+\.?\d*"
            print('--- all wei bo page {}'.format(page_num))

            start_page = 1
            if os.path.exists(self.tweet_save_file):
                obj = pickle.load(codecs.open(self.tweet_save_file, 'rb'))
                if self.user_id in obj:
                    self.wei_bo_content = obj[self.user_id]['weibo_content']
                    start_page = obj[self.user_id]['last_scrap_page']
                    if start_page == page_num:
                        return 0
                    else:
                        start_page += 1
            try:
                # traverse all wei bo, and we will got wei bo detail urls
                # TODO: inside for loop must set sleep avoid banned by official.
                for page in range(start_page, page_num+1):
                    url2 = 'http://weibo.cn/%s?filter=%s&page=%s' % (self.user_id, self.filter, page)
                    html2 = requests.get(url2, cookies=self.cookie, headers=self.headers).content
                    selector2 = etree.HTML(html2)
                    info = selector2.xpath("//div[@class='c']")
                    print('---- current solving page {} of {}'.format(page, page_num))
                    if len(info) > 3:
                        for i in range(0, len(info) - 2):
                            detail = info[i].xpath("@id")[0]
                            self.wei_bo_detail_urls.append('http://weibo.cn/comment/{}?uid={}&rl=0'.
                                                           format(detail.split('_')[-1], self.user_id))

                            self.wei_bo_scraped += 1
                            str_t = info[i].xpath("div/span[@class='ctt']")
                            tweets = str_t[0].xpath('string(.)')
                            self.wei_bo_content.append(tweets)
                            print(tweets)

                            str_zan = info[i].xpath("div/a/text()")[-4]
                            g_uid = re.findall(pattern, str_zan, re.M)
                            num_zan = int(g_uid[0])
                            self.num_zan.append(num_zan)

                            forwarding = info[i].xpath("div/a/text()")[-3]
                            g_uid = re.findall(pattern, forwarding, re.M)
                            num_forwarding = int(g_uid[0])
                            self.num_forwarding.append(num_forwarding)

                            comment = info[i].xpath("div/a/text()")[-2]
                            g_uid = re.findall(pattern, comment, re.M)
                            num_comment = int(g_uid[0])
                            self.num_comment.append(num_comment)
                    print('[ATTEMPTING] rest for 3 seconds to cheat tweet site, avoid being banned.')
                    time.sleep(3)
            except etree.XMLSyntaxError as e:
                print('\n' * 2)
                print('=' * 20)
                print('wei bo user {} all wei bo content finished scrap.'.format(self.user_name))
                print('all wei bo {}, all like {}, all comments {}'.format(
                    len(self.wei_bo_content), np.sum(self.num_zan, dtype=np.int32), np.sum(self.num_comment, dtype=np.int32)))
                print('try saving wei bo content for now...')
                dump_obj = dict()
                if os.path.exists(self.tweet_save_file):
                    with codecs.open(self.tweet_save_file, 'rb') as f:
                        dump_obj = pickle.load(f)
                    self.wei_bo_content = list(set(self.wei_bo_content))
                    dump_obj[self.user_id] = {
                        'weibo_content': self.wei_bo_content,
                        'last_scrap_page': page
                    }
                    with codecs.open(self.tweet_save_file, 'wb') as f:
                        pickle.dump(dump_obj, f)
                dump_obj[self.user_id] = {
                    'weibo_content': self.wei_bo_content,
                    'last_scrap_page': page
                }
                with codecs.open(self.tweet_save_file, 'wb') as f:
                    pickle.dump(dump_obj, f)
                print('[CHEER] wei bo content saved into {}'.format(self.tweet_save_file))
                del self.wei_bo_content
            except Exception as e:
                print(e)
                print('\n' * 2)
                print('=' * 20)
                print('wei bo user {} content scrap error occurred {}.'.format(self.user_name, e))
                print('all wei bo {}, all like {}, all comments {}'.format(
                    len(self.wei_bo_content), np.sum(self.num_zan, dtype=np.int32),
                    np.sum(self.num_comment, dtype=np.int32)))
                print('try saving wei bo content for now...')
                dump_obj = dict()
                if os.path.exists(self.tweet_save_file):
                    with codecs.open(self.tweet_save_file, 'rb') as f:
                        dump_obj = pickle.load(f)
                    dump_obj[self.user_id] = {
                        'weibo_content': self.wei_bo_content,
                        'last_scrap_page': page
                    }
                    with codecs.open(self.tweet_save_file, 'wb') as f:
                        pickle.dump(dump_obj, f)

                dump_obj[self.user_id] = {
                    'weibo_content': self.wei_bo_content,
                    'last_scrap_page': page
                }
                with codecs.open(self.tweet_save_file, 'wb') as f:
                    pickle.dump(dump_obj, f)
                print('[CHEER] wei bo content saved into {}, next time will start from {} page'.format(
                    self.tweet_save_file, page))
                del self.wei_bo_content
            print('\n' * 2)
            print('=' * 20)
            print('all wei bo {}, all like {}, all comments {}'.format(
                len(self.wei_bo_content), np.sum(self.num_zan, dtype=np.int32),
                np.sum(self.num_comment, dtype=np.int32)))
            print('try saving wei bo content for now...')
            dump_obj = dict()
            if os.path.exists(self.tweet_save_file):
                with codecs.open(self.tweet_save_file, 'rb') as f:
                    dump_obj = pickle.load(f)
                dump_obj[self.user_id] = {
                    'weibo_content': self.wei_bo_content,
                    'last_scrap_page': page
                }
                with codecs.open(self.tweet_save_file, 'wb') as f:
                    pickle.dump(dump_obj, f)

            dump_obj[self.user_id] = {
                'weibo_content': self.wei_bo_content,
                'last_scrap_page': page
            }
            with codecs.open(self.tweet_save_file, 'wb') as f:
                pickle.dump(dump_obj, f)
            print('[CHEER] wei bo content saved into {}, next time will start from {} page'.format(
                self.tweet_save_file, page))
            del self.wei_bo_content
            if self.filter == 0:
                print('共' + str(self.wei_bo_scraped) + '条微博')
            else:
                print('共' + str(self.tweets_num) + '条微博，其中' + str(self.wei_bo_scraped) + '条为原创微博')

        except IndexError as e:
            print('get wei bo info done, current user {} has no wei bo yet.'.format(self.user_id))

    def _get_wei_bo_content_and_comment(self):
        """
        all wei bo will be saved into weibo_content_and_comment.pkl
        in format:
        {
            scrap_id: {
                'weibo_detail_urls': [....],
                'last_scrap_index': 5,
                'content_and_comment': [
                {'content': '...', 'comment': ['..', '...', '...', '...',]},
                {'content': '...', 'comment': ['..', '...', '...', '...',]},
                {'content': '...', 'comment': ['..', '...', '...', '...',]}
                ]
            }
        }
        :return:
        """
        print('\n' + '-' * 30)
        print('getting wei bo content and comment...')
        wei_bo_detail_urls = self.wei_bo_detail_urls
        start_scrap_index = 0
        content_and_comment = []
        if os.path.exists(self.tweet_save_file):
            print('loading previous wei_bo_content file from {}'.format(self.tweet_save_file))
            with codecs.open(self.tweet_save_file, 'rb') as f:
                obj = pickle.load(f)
            if self.user_id in obj:
                self.wei_bo_content = obj[self.user_id]['weibo_content']

        # 断点续爬
        if os.path.exists(self.tweet_and_comment_save_file):
            with codecs.open(self.tweet_and_comment_save_file, 'rb') as f:
                obj = pickle.load(f)
            if self.user_id in obj:
                obj = obj[self.user_id]
                wei_bo_detail_urls = obj['weibo_detail_urls']
                start_scrap_index = obj['last_scrap_index']
                content_and_comment = obj['content_and_comment']
                if start_scrap_index == len(wei_bo_detail_urls):
                    return 0
                else:
                    start_scrap_index += 1

        if wei_bo_detail_urls:
            try:
                for i in range(start_scrap_index, len(wei_bo_detail_urls)):
                    url = wei_bo_detail_urls[i]
                    one_content_and_comment = dict()
                    print('\n\nsolving wei bo detail from {}'.format(url))
                    print('No.{} wei bo of total {}'.format(i + 1, len(wei_bo_detail_urls)))
                    html_detail = requests.get(url, cookies=self.cookie, headers=self.headers).content
                    selector_detail = etree.HTML(html_detail)
                    all_comment_pages = selector_detail.xpath('//*[@id="pagelist"]/form/div/input[1]/@value')
                    print('\n这是{}的微博：'.format(self.user_name))
                    print('微博内容： {}'.format(self.wei_bo_content[i]))
                    if all_comment_pages:
                        all_comment_pages = all_comment_pages[0]
                        print('接下来是下面的评论：\n\n')

                        one_content_and_comment['content'] = self.wei_bo_content[i]
                        one_content_and_comment['comment'] = []

                        start_idx = 0
                        end_idx = int(all_comment_pages) - 2
                        if i == start_scrap_index and content_and_comment:
                            one_cac = content_and_comment[-1]
                            if 'last_idx' in one_cac:
                                print('\nTrying to recover from the last comment of last content...\n')
                                if one_cac['last_idx'] + 1 < end_idx:
                                    one_content_and_comment['comment'] = one_cac['comment']
                                    start_idx = one_cac['last_idx'] + 1
                                    print('last_idx: {}\n'.format(one_cac['last_idx']))

                        for page in range(start_idx, end_idx):
                            print('\n---- current solving page {} of {}'.format(page + 2, int(all_comment_pages) - 3))

                            if page % 5 == 0:
                                print('[ATTEMPTING] rest for 20 s to cheat wei bo site, avoid being banned.')
                                time.sleep(20)

                            detail_comment_url = url + '&page=' + str(page + 2)
                            print(detail_comment_url)
                            no_content_pages = []
                            try:
                                # from every detail comment url we will got all comment
                                html_detail_page = requests.get(detail_comment_url, cookies=self.cookie).content
                                selector_comment = etree.HTML(html_detail_page)

                                comment_div_element = selector_comment.xpath('//div[starts-with(@id, "C_")]')

                                for child in comment_div_element:
                                    single_comment_user_name = child.xpath('a[1]/text()')[0]
                                    if child.xpath('span[1][count(*)=0]'):
                                        single_comment_content = child.xpath('span[1][count(*)=0]/text()')[0]
                                    else:
                                        span_element = child.xpath('span[1]')[0]
                                        at_user_name = span_element.xpath('a/text()')[0]
                                        at_user_name = '$' + at_user_name.split('@')[-1] + '$'
                                        single_comment_content = span_element.xpath('text()')
                                        single_comment_content.insert(0, at_user_name)
                                        single_comment_content = ' '.join(single_comment_content)
                                    full_single_comment = '<' + single_comment_user_name + '>' + ': ' + \
                                                          single_comment_content
                                    print(full_single_comment)
                                    one_content_and_comment['comment'].append(full_single_comment)
                                    one_content_and_comment['last_idx'] = page
                            except etree.XMLSyntaxError as e:
                                no_content_pages.append(page)
                                print('\n\nThis page has no contents and is passed: ', e)
                                print('Total no_content_pages: {}'.format(len(no_content_pages)))
                            except Exception as e:
                                print('Raise Exception in _get_wei_bo_content_and_comment, error:', e)
                                print('\n' * 2)
                                print('=' * 20)
                                print('wei bo user {} content_and_comment scrap error occurred {}.'.
                                      format(self.user_name,e))
                                self._save_content_and_comment(i, one_content_and_comment, wei_bo_detail_urls)
                                print("\n\nComments are successfully save:\n User name: {}\n wei bo content: {}\n\n".
                                      format(self.user_name, one_content_and_comment['content']))
                        self._save_content_and_comment(i, one_content_and_comment, wei_bo_detail_urls)
                        print('*' * 30)
                        print("\n\nComments are successfully save:\n User name: {}\n we ibo content: {}".format(
                            self.user_name, one_content_and_comment['content']))
                    else:
                        print('\nThis wei bo has no comment.')
            except KeyboardInterrupt:
                print('manually interrupted.. try save wb_content_and_comment for now...')
                self._save_content_and_comment(i - 1, one_content_and_comment, wei_bo_detail_urls)

            print('\n' * 2)
            print('=' * 20)
            print('user {}, all wei bo content and comment finished.'.format(self.user_name))

        else:
            print('current user {} has no wei bo.'.format(self.user_id))
            return 0

    def _save_content_and_comment(self, i, one_content_and_comment, wei_bo_detail_urls):
        dump_dict = dict()
        if os.path.exists(self.tweet_and_comment_save_file):
            with codecs.open(self.tweet_and_comment_save_file, 'rb') as f:
                obj = pickle.load(f)
                dump_dict = obj
                if self.user_id in dump_dict:
                    dump_dict[self.user_id]['last_scrap_index'] = i
                    dump_dict[self.user_id]['content_and_comment'].append(one_content_and_comment)
                else:
                    dump_dict[self.user_id] = {
                        'weibo_detail_urls': wei_bo_detail_urls,
                        'last_scrap_index': i,
                        'content_and_comment': [one_content_and_comment]
                    }
        else:
            dump_dict[self.user_id] = {
                'weibo_detail_urls': wei_bo_detail_urls,
                'last_scrap_index': i,
                'content_and_comment': [one_content_and_comment]
            }
        with codecs.open(self.tweet_and_comment_save_file, 'wb') as f:
            print('try saving wei bo content and comment for now.')
            pickle.dump(dump_dict, f)

    def switch_account(self, new_account):
        assert isinstance(new_account, str), 'account must be string'
        self.using_account = new_account
        try:
            with open(COOKIES_SAVE_PATH, 'rb') as f:
                cookies_dict = pickle.load(f)
            cookies_string = cookies_dict[self.using_account]
            cookie = {
                "Cookie": cookies_string
            }
            print("switch to new cookie...")
            self.cookie = cookie
        except FileNotFoundError:
            print('have not get cookies yet.')


def main():
    account = 'juehe093@163.com'
    user_id = "2720241537"
    filter_flag = 1
    wb = WeiBoScraper(account, user_id, filter_flag)
    sess = requests.session()
    html_detail_page = sess.get('https://weibo.cn/comment/F1sfDh7Rb?uid=2720241537&rl=0&page=600', cookies=wb.cookie,
                                headers=wb.headers).content
    print(html_detail_page)
    selector_comment = etree.HTML(html_detail_page)
    comment_div_element = selector_comment.xpath('//div[starts-with(@id, "C_")]')
    for child in comment_div_element:
        single_comment_user_name = child.xpath('a[1]/text()')[0]
        if child.xpath('span[1][count(*)=0]'):
            single_comment_content = child.xpath('span[1][count(*)=0]/text()')[0]
        else:
            span_element = child.xpath('span[1]')[0]
            at_user_name = span_element.xpath('a/text()')[0]
            at_user_name = '$' + at_user_name.split('@')[-1] + '$'
            single_comment_content = span_element.xpath('text()')
            single_comment_content.insert(0, at_user_name)
            single_comment_content = ' '.join(single_comment_content)
        full_single_comment = '<' + single_comment_user_name + '>' + ': ' + \
                              single_comment_content
        print(full_single_comment)


if __name__ == '__main__':
    main()
