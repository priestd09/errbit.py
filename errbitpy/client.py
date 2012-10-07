import logging
import threading
import traceback
import urllib2
import sys
import xmlbuilder

app_name='ErrbitPy'
version='0.0.1'
source_url='http://github.com/mkorenkov/errbitpy'

def log_error(method):
    def wrap_error():
        try:
            method()
        except Exception, e:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.ERROR)
            logger.exception(e)

    wrap_error.__name__ = method.__name__
    return wrap_error

class MyHandler(urllib2.HTTPHandler):
    @log_error
    def http_response(self, req, response):
        status = response.getcode
        if status == 200:
            return

        exceptionMessage = "Unexpected status code {0}".format(str(status))

        if status == 403:
            exceptionMessage = "Unable to send using SSL"
        elif status == 422:
            exceptionMessage = "Invalid XML sent"
        elif status == 500:
            exceptionMessage = "Destination server is unavailable. Please check the remote server status."
        elif status == 503:
            exceptionMessage = "Service unavailable. You may be over your quota."

        raise Exception(exceptionMessage)

class ErrbitClient:
    def __init__(self, service_url, api_key, component, node, environment):
        self.service_url = service_url
        self.api_key = api_key
        self.component_name = component
        self.node_name = node
        self.environment = environment

    @log_error
    def log(self, exception):
        message = self._generate_xml(exception, sys.exc_info())
        self._sendMessage(message)

    def _sendHttpRequest(self, headers, message):
        o = urllib2.build_opener(MyHandler())
        o.addheaders(headers)
        t = threading.Thread(target=o.open, args=(self.service_url, message))
        t.start()

    def _sendMessage(self, message):
        headers = {"Content-Type": "text/xml"}
        self._sendHttpRequest(headers, message)

    def _generate_xml(self, exc, trace):
        message = "{0}: {1}".format(exc.message, str(exc))

        xml = xmlbuilder.XMLBuilder()
        with xml.notice(version=2.0):
            xml << ('api-key', self.api_key)
            with xml.notifier:
                xml << ('name', app_name)
                xml << ('version', version)
                xml << ('url', source_url)
            with xml('server-environment'):
                xml << ('environment-name', self.environment)
            with xml.request:
                xml << ("url", "")
                xml << ("component", self.component_name)
                with xml("cgi-data"):
                    with xml("var", key="nodeName"):
                        xml << self.node_name
                    with xml("var", key="componentName"):
                        xml << self.component_name
            with xml.error:
                xml << ('class', '' if exc is None else exc.__class__.__name__)
                xml << ('message', message)
                if trace:
                    with xml.backtrace:
                        [xml << ('line', {'file': filename, 'number': line_number, 'method': "{0}: {1}".format(function_name, text)})\
                         for filename, line_number, function_name, text in traceback.extract_tb(trace)]
        return str(xml)