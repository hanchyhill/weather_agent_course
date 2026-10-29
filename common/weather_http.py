"""天气课程 HTTP 请求：临时内网域名直连，其余地址沿用环境代理。"""
from urllib.parse import urlsplit

import requests


def get(url, **kwargs):
    if urlsplit(url).hostname == "tmp.gdmo.org":
        with requests.Session() as session:
            session.trust_env = False
            return session.get(url, **kwargs)
    return requests.get(url, **kwargs)
