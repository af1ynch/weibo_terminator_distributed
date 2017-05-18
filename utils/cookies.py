# -*- coding: utf-8 -*-
# file: cookies.py
# author: JinTian
# time: 17/04/2017 12:55 PM
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
to get weibo_terminator switch accounts automatically, please be sure install:

PhantomJS, from http://phantomjs.org/download.html

"""
import os
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import InvalidElementStateException
from selenium.webdriver.remote.command import Command
import time
import sys
from tqdm import *
import pickle
import random

from settings.accounts import accounts
from settings.config import LOGIN_URL, PHANTOM_JS_PATH, COOKIES_SAVE_PATH, CHROME_PATH

from PIL import Image
import math
from io import BytesIO
from utils.ims import ims


def count_time():
    for i in tqdm(range(40)):
        time.sleep(0.5)


def get_cookie_from_network(account_id, account_password):
    url_login = LOGIN_URL
    # phantom_js_driver_file = os.path.abspath(PHANTOM_JS_PATH)
    chrome_driver_file = os.path.abspath(CHROME_PATH)
    if os.path.exists(chrome_driver_file):
        try:
            print('loading Chromedriver from {}'.format(chrome_driver_file))
            # driver = webdriver.PhantomJS(phantom_js_driver_file)
            # must set window size or will not find element
            driver = webdriver.Chrome(chrome_driver_file)
            driver.set_window_size(1920, 1080)
            driver.get(url_login)
            # before get element sleep for 4 seconds, waiting for page render complete.
            print('opening wei bo login page, this is first done for prepare for cookies. be patience to waite load '
                  'complete.')
            count_time()
            driver.find_element_by_xpath('//input[@id="loginName"]').send_keys(account_id)
            driver.find_element_by_xpath('//input[@id="loginPassword"]').send_keys(account_password)
            # driver.find_element_by_xpath('//input[@id="loginPassword"]').send_keys(Keys.RETURN)
            print('account id: {}'.format(account_id))
            print('account password: {}'.format(account_password))

            driver.find_element_by_xpath('//a[@id="loginAction"]').click()
        except InvalidElementStateException as e:
            print(e)
            print('error, account id {} is not valid, pass this account, you can edit it and then '
                  'update cookies. \n'
                  .format(account_id))

        try:
            cookie_list = driver.get_cookies()
            cookie_string = ''
            if not cookie_list:
                t_type = get_type(driver)
                print('Result: {}'.format(t_type))
                draw(driver, t_type)
                time.sleep(5)
                cookie_list = driver.get_cookies()
                print(cookie_list)

            for cookie in cookie_list:
                if 'name' in cookie and 'value' in cookie:
                    cookie_string += cookie['name'] + '=' + cookie['value'] + ';'
            if 'SSOLoginState' in cookie_string:
                print('success get {} account cookies!! \n '.format(account_id))
                if os.path.exists(COOKIES_SAVE_PATH):
                    with open(COOKIES_SAVE_PATH, 'rb') as f:
                        cookies_dict = pickle.load(f)
                    if account_id not in cookies_dict.keys():
                        cookies_dict[account_id] = cookie_string
                        with open(COOKIES_SAVE_PATH, 'wb') as f:
                            pickle.dump(cookies_dict, f)
                        print('successfully save cookies into {}. \n'.format(COOKIES_SAVE_PATH))
                    else:
                        pass
                else:
                    cookies_dict = dict()
                    cookies_dict[account_id] = cookie_string
                    with open(COOKIES_SAVE_PATH, 'wb') as f:
                        pickle.dump(cookies_dict, f)
                    print('successfully save cookies into {}. \n'.format(COOKIES_SAVE_PATH))
                return cookie_string
            else:
                print('error, account id {} is not valid, pass this account, you can edit it and then '
                      'update cookies. \n'
                      .format(account_id))
                pass

        except Exception as e:
            print(e)

    else:
        print('can not find chromedriver driver, please download from http://npm.taobao.org/mirrors/chromedriver based on your '
              'system.')

PIXELS = []


def get_type(driver):

    t_type = ''
    time.sleep(3.5)
    im0 = Image.open(BytesIO(driver.get_screenshot_as_png()))
    box = driver.find_element_by_id('patternCaptchaHolder')
    im = im0.crop((int(box.location['x']) + 10, int(box.location['y']) + 100, int(box.location['x']) +
                   box.size['width'] - 10, int(box.location['y']) + box.size['height'] - 10)).convert('L')
    new_box = get_exactly(im)
    im = im.crop(new_box)
    width = im.size[0]
    height = im.size[1]
    for png in ims.keys():
        is_going_on = True
        for i in range(width):
            for j in range(height):
                # 以245为临界值，大约245为空白，小于245为线条；两个像素之间的差大约10，是为了去除245边界上的误差
                if ((im.load()[i, j] >= 245 and ims[png][i][j] < 245)
                    or (im.load()[i, j] < 245 and ims[png][i][j] >= 245)) and \
                                abs(ims[png][i][j] - im.load()[i, j]) > 10:
                    is_going_on = False
                    break
            if is_going_on is False:
                t_type = ''
                break
            else:
                t_type = png
        else:
            break
    px0_x = box.location['x'] + 40 + new_box[0]
    px1_y = box.location['y'] + 130 + new_box[1]
    PIXELS.append((px0_x, px1_y))
    PIXELS.append((px0_x + 100, px1_y))
    PIXELS.append((px0_x, px1_y + 100))
    PIXELS.append((px0_x + 100, px1_y + 100))
    return t_type


def get_exactly(im):
    """ 精确剪切"""
    i_min = -1
    i_max = -1
    j_min = -1
    j_max = -1
    row = im.size[0]
    col = im.size[1]
    for i in range(row):
        for j in range(col):
            if im.load()[i, j] != 255:
                i_max = i
                break
        if i_max == -1:
            i_min = i

    for j in range(col):
        for i in range(row):
            if im.load()[i, j] != 255:
                j_max = j
                break
        if j_max == -1:
            j_min = j
    new_box = (i_min + 1, j_min + 1, i_max + 1, j_max + 1)
    return new_box


def move(browser, coordinate, coordinate0):
    """ 从坐标coordinate0，移动到坐标coordinate """
    time.sleep(0.05)
    length = math.sqrt((coordinate[0] - coordinate0[0]) ** 2 + (coordinate[1] - coordinate0[1]) ** 2)  # 两点直线距离
    if length < 4:  # 如果两点之间距离小于4px，直接划过去
        ActionChains(browser).move_by_offset(coordinate[0] - coordinate0[0], coordinate[1] - coordinate0[1]).perform()
        return
    else:  # 递归，不断向着终点滑动
        step = random.randint(3, 5)
        x = int(step * (coordinate[0] - coordinate0[0]) / length)  # 按比例
        y = int(step * (coordinate[1] - coordinate0[1]) / length)
        ActionChains(browser).move_by_offset(x, y).perform()
        move(browser, coordinate, (coordinate0[0] + x, coordinate0[1] + y))


def draw(browser, t_type):
    """ 滑动 """
    if len(t_type) == 4:
        px0 = PIXELS[int(t_type[0]) - 1]
        login = browser.find_element_by_id('loginAction')
        ActionChains(browser).move_to_element(login).move_by_offset(px0[0] - login.location['x'] -
                                                                    int(login.size['width'] / 2), px0[1] -
                                                                    login.location['y'] -
                                                                    int(login.size['height'] / 2)).perform()
        browser.execute(Command.MOUSE_DOWN, {})

        px1 = PIXELS[int(t_type[1]) - 1]
        move(browser, (px1[0], px1[1]), px0)

        px2 = PIXELS[int(t_type[2]) - 1]
        move(browser, (px2[0], px2[1]), px1)

        px3 = PIXELS[int(t_type[3]) - 1]
        move(browser, (px3[0], px3[1]), px2)
        browser.execute(Command.MOUSE_UP, {})
    else:
        print('Sorry! Failed! Maybe you need to update the code.')

#
# if __name__ == '__main__':
#     un = '1085703880@qq.com'
#     pw = 'sinaweibo123..'
#     get_cookie_from_network(un, pw)
