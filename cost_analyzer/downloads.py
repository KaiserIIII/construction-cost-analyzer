"""Bounded, expiring report attachments held only in this process."""
import secrets
import threading
import time
from collections import OrderedDict


class DownloadStore:
    def __init__(self,ttl=600,max_count=64,max_bytes=32_000_000,clock=time.monotonic):
        self.ttl=ttl;self.max_count=max_count;self.max_bytes=max_bytes;self.clock=clock
        self._items=OrderedDict();self._bytes=0;self._lock=threading.Lock()

    def _remove(self,token):
        item=self._items.pop(token);self._bytes-=len(item[1])

    def _purge(self):
        now=self.clock()
        for token,item in list(self._items.items()):
            if item[0]<=now:self._remove(token)

    def put(self,body,filename,content_type):
        if len(body)>self.max_bytes:raise ValueError('Report exceeds download capacity; export with the CLI')
        with self._lock:
            self._purge()
            while self._items and (len(self._items)>=self.max_count or self._bytes+len(body)>self.max_bytes):
                self._remove(next(iter(self._items)))
            token=secrets.token_urlsafe(24)
            self._items[token]=(self.clock()+self.ttl,body,filename,content_type);self._bytes+=len(body)
            return token

    def get(self,token):
        with self._lock:
            self._purge();item=self._items.get(token)
            return item[1:] if item else None
