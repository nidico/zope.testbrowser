##############################################################################
#
# Copyright (c) 2010 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""A minimal WSGI application used as a test fixture."""

import os
import mimetypes
from datetime import datetime

from webob import Request, Response
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

class NotFound(Exception):
    pass

_HERE = os.path.dirname(__file__)

class MyPageTemplateFile(PageTemplateFile):

    def pt_getContext(self, args, *extra_args, **kw):
        namespace = super(MyPageTemplateFile, self).pt_getContext(args, *extra_args, **kw)
        namespace['request'] = args[0]
        return namespace

class WSGITestApplication(object):

    def __call__(self, environ, start_response):
        req = Request(environ)
        handler = {'/set_status.html': set_status,
                   '/echo.html': echo,
                   '/echo_one.html': echo_one,
                   '/set_header.html': set_header,
                   '/set_cookie.html': set_cookie,
                   '/get_cookie.html': get_cookie,
                   '/inner/set_cookie.html': set_cookie,
                   '/inner/get_cookie.html': get_cookie,
                   '/inner/path/set_cookie.html': set_cookie,
                   '/inner/path/get_cookie.html': get_cookie,
                   }.get(req.path_info)
        if handler is None and req.path_info.startswith('/@@/testbrowser/'):
            handler = handle_resource
        if handler is None:
            handler = handle_notfound
        try:
            resp = handler(req)
        except Exception, exc:
            if not environ.get('wsgi.handleErrors', True):
                raise
            resp = Response()
            resp.status = {NotFound: 404}.get(type(exc), 500)
        resp.headers.add('X-Powered-By', 'Zope (www.zope.org), Python (www.python.org)')
        return resp(environ, start_response)

def handle_notfound(req):
    raise NotFound(req.path_info)

def handle_resource(req):
    filename = req.path_info.split('/')[-1]
    type, _ = mimetypes.guess_type(filename)
    path = os.path.join(_HERE, filename)
    if type == 'text/html':
        pt = MyPageTemplateFile(path)
        contents = pt(req)
    else:
        contents = open(path, 'r').read()
    return Response(contents, content_type=type)

def get_cookie(req):
    cookies = ['%s: %s' % i for i in sorted(req.cookies.items())]
    return Response('\n'.join(cookies))
    
def set_cookie(req):
    cookie_parms = {'path': None}
    cookie_parms.update(dict((str(k), str(v)) for k, v in req.params.items()))
    name = cookie_parms.pop('name')
    value = cookie_parms.pop('value')
    if 'max-age' in cookie_parms:
        cookie_parms['max_age'] = int(cookie_parms.pop('max-age'))
    if 'expires' in cookie_parms:
        cookie_parms['expires'] = datetime.strptime(cookie_parms.pop('expires'), '%a, %d %b %Y %H:%M:%S GMT')
    resp = Response()
    resp.set_cookie(name, value, **cookie_parms)
    return resp

def set_header(req):
    resp = Response()
    body = [u"Set Headers:"]
    for k, v in sorted(req.params.items()):
        body.extend([k, v]) 
        resp.headers.add(k, v)
    resp.unicode_body = u'\n'.join(body)
    return resp

_interesting_environ = ('CONTENT_LENGTH',
                        'CONTENT_TYPE',
                        'HTTP_ACCEPT_LANGUAGE',
                        'HTTP_CONNECTION',
                        'HTTP_HOST',
                        'HTTP_USER_AGENT',
                        'PATH_INFO',
                        'REQUEST_METHOD')

def echo(req):
    items = []
    for k in _interesting_environ:
        v = req.environ.get(k, None)
        if v is None:
            continue
        items.append('%s: %s' % (k, v))
    items.extend('%s: %s' % x for x in sorted(req.params.items())) 
    if req.method == 'POST' and req.content_type == 'application/x-www-form-urlencoded':
        body = ''
    else:
        body = req.body
    items.append('Body: %r' % body)
    return Response('\n'.join(items))

def echo_one(req):
    resp = repr(req.environ.get(req.params['var']))
    return Response(resp)

def set_status(req):
    status = req.params.get('status')
    if status:
        resp = Response('Just set a status of %s' % status)
        resp.status = int(status)
        return resp
    return Response('Everything fine')
