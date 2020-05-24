__copyright__ = "Copyright (c) 2020 Jina AI Limited. All rights reserved."
__license__ = "Apache-2.0"

import logging
import os

from argparse import _StoreAction, _StoreTrueAction
from jina import JINA_GLOBAL, __version__
from jina.helper import yaml
from jina.logging import default_logger
from jina.logging.queue import __sse_queue__, __profile_queue__
from jina.main.parser import set_pod_parser


def start_sse_logger(server_config_path: str, flow_yaml: str = None):
    """Start a logger that emits server-side event from the log queue, so that one can use a browser to monitor the logs

    :param host: host address of the server
    :param port: port of the server
    :param endpoint_log: endpoint for the log
    :param endpoint_yaml: endpoint for the yaml

    Example:

    .. highlight:: javascript
    .. code-block:: javascript

        var stream = new EventSource('http://localhost:5000/log/stream');
        stream.onmessage = function (e) {
            console.info(e.data);
        };
        stream.onerror = function (err) {
            console.error("EventSource failed:", err);
            stream.close()
        };

    """
    try:
        from flask import Flask, Response, jsonify
        from flask_cors import CORS
    except ImportError:
        raise ImportError('Flask or its dependencies are not fully installed, '
                          'they are required for serving HTTP requests.'
                          'Please use pip install "jina[http]" to install it.')

    try:
        with open(server_config_path) as fp:
            _config = yaml.load(fp)
    except Exception as ex:
        default_logger.error(ex)
    JINA_GLOBAL.logserver.address = f'http://{_config["host"]}:{_config["port"]}'

    JINA_GLOBAL.logserver.ready = JINA_GLOBAL.logserver.address + _config['endpoints']['ready']
    JINA_GLOBAL.logserver.shutdown = JINA_GLOBAL.logserver.address + _config['endpoints']['shutdown']

    app = Flask(__name__)
    CORS(app)

    @app.route(_config['endpoints']['log'])
    def get_log():
        """Get the logs, endpoint `/log/stream`  """
        return Response(_log_stream(), mimetype="text/event-stream")

    @app.route(_config['endpoints']['yaml'])
    def get_yaml():
        """Get the yaml of the flow  """
        return flow_yaml

    @app.route(_config['endpoints']['profile'])
    def get_profile():
        """Get the profile logs, endpoint `/profile/stream`  """
        return Response(_profile_stream(), mimetype='text/event-stream')

    @app.route(_config['endpoints']['podapi'])
    def get_podargs():
        """Get the default args of a pod"""
        port_attr = ('help', 'choices', 'default')
        d = {}
        parser = set_pod_parser()
        for a in parser._actions:
            if isinstance(a, _StoreAction) or isinstance(a, _StoreTrueAction):
                d[a.dest] = {p: getattr(a, p) for p in port_attr}
                if a.type:
                    d[a.dest]['type'] = a.type.__name__
                elif isinstance(a, _StoreTrueAction):
                    d[a.dest]['type'] = 'bool'
                else:
                    d[a.dest]['type'] = a.type

        d = {'pod': d, 'version': __version__, 'usage': parser.format_help()}
        return jsonify(d)

    @app.route(_config['endpoints']['shutdown'])
    def shutdown():
        from flask import request
        if not 'werkzeug.server.shutdown' in request.environ:
            raise RuntimeError('Not running the development server')
        request.environ['werkzeug.server.shutdown']()
        return 'Server shutting down...'

    @app.route(_config['endpoints']['ready'])
    def is_ready():
        return Response(status=200)

    os.environ['WERKZEUG_RUN_MAIN'] = 'true'
    log = logging.getLogger('werkzeug')
    log.disabled = True

    try:
        app.logger.disabled = True
        app.run(port=_config['port'], host=_config['host'])
    except Exception as ex:
        default_logger.error(ex)


def _log_stream():
    while True:
        try:
            message = __sse_queue__.get()
            yield 'data: {}\n\n'.format(message.msg)
        except EOFError:
            yield 'LOG ENDS\n\n'
            break


def _profile_stream():
    while True:
        try:
            message = __profile_queue__.get()
            yield 'data: {}\n\n'.format(message.msg)
        except EOFError:
            yield 'PROFILE ENDS\n\n'
            break
