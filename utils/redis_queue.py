# -*- coding:utf-8 -*-

"""
@version: 
@author: lynch
@contact: 
@site: https://github.com/af1ynch
@software: PyCharm
@file: redis_queue.py
@time: 2017/5/3 16:11
"""
import redis
from settings.config import REDIS_HOST, REDIS_PORT, REDIS_KEY_NAMESPACE


class RedisQueue(object):

    def __init__(self, name, **kwargs):

        self._db = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.key = "{0}:{1}".format(REDIS_KEY_NAMESPACE, name)
        self.set_key = "{0}:{1}_set".format(REDIS_KEY_NAMESPACE, name)

    def qsize(self):
        """Return the approximate size of the redisqueue"""
        return self._db.llen(self.key)

    def set_size(self):
        """Return set size"""
        return self._db.scard(self.set_key)

    def empty(self):
        """Return True if the redisqueue is empty, False otherwise"""
        return self.qsize() == 0

    def set_empty(self):
        """Return True if the set is empty, False othersize"""
        return self.set_size() == 0

    def put(self, item):
        """Put item into redisqueue
        :param item:
        """
        self._db.rpush(self.key, item)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the redisqueue
        If optional args block is true and timeout is None(default),
        block if necessary until an item is available.
        :param timeout:
        :param block: """
        if block:
            item = self._db.blpop(self.key, timeout=timeout)
        else:
            item = self._db.lpop(self.key)

        if item:
            item = item[1]
        return item

    def get_nowait(self):
        """Equivalent to get(False)"""
        return self.get(False)

    def set_add(self, *item):
        """Add item into set
        :param item:
        """
        self._db.sadd(self.set_key, *item)

    def set_pop(self):
        """get an item form set"""
        return self._db.spop(self.set_key)

    def set_is_member(self, item):
        """Check item is in the set
        :param item"""
        return True if self._db.sismember(self.set_key, item) else False
