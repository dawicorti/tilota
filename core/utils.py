# -*- coding: utf-8 *-*
import os
import uuid
import zmq
import re
import logging
from tilota import settings
from tilota.core.console import Console


def logger():
    logger = logging.getLogger('Utils')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(os.path.join(
        os.path.dirname(__file__), 'utils.log'))
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-8s %(name)-8s %(message)s'))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


def create_new_game(game_cmd):
    logger().debug('Create new game with cmd : %s', game_cmd)
    tmp_ipc = 'ipc://%s/%s.ipc' % (settings.CACHE_PATH, str(uuid.uuid1()))
    logger().debug('Connecting to %s', tmp_ipc)
    tmp_socket = zmq.Socket(zmq.Context(), zmq.PULL)
    tmp_socket.bind(tmp_ipc)
    daemon_socket = zmq.Socket(zmq.Context(), zmq.PUSH)
    daemon_socket.connect(settings.DAEMON_INBOX)
    game = Console('dmtcp_checkpoint %s' % game_cmd)
    daemon_socket.send_json(
        {'name': 'get_game_id', 'pid': game.process.pid, 'reply_ipc': tmp_ipc}
    )
    logger().debug('Waiting for game id')
    game_id = tmp_socket.recv_json()['game_id']
    logger().debug('Retreive game id = %s', str(game_id))
    daemon_socket.send_json({'name': 'save_checkpoints', 'reply_ipc': tmp_ipc})
    tmp_socket.recv_json()
    tmp_socket.close()
    return game_id


def play(game_id, cmd):
    tmp_ipc = 'ipc://%s/%s.ipc' % (settings.CACHE_PATH, str(uuid.uuid1()))
    tmp_socket = zmq.Socket(zmq.Context(), zmq.PULL)
    tmp_socket.bind(tmp_ipc)
    daemon_socket = zmq.Socket(zmq.Context(), zmq.PUSH)
    daemon_socket.connect(settings.DAEMON_INBOX)
    game = Console(os.path.join(
        settings.CACHE_PATH,
        'dmtcp_restart_script_%s.sh' % game_id
    ))
    return_text = game.cmd(cmd)
    daemon_socket.send_json({'name': 'save_checkpoints', 'reply_ipc': tmp_ipc})
    tmp_socket.recv_json()
    tmp_socket.close()
    lines = return_text.split('\n')
    lines.reverse()
    end_of_text_reached = False
    formated_text = ''
    for line in lines:
        if end_of_text_reached:
            if re.compile('(|[^\w])(%s|gzip)(|[^\w])' % cmd).search(line):
                break
            else:
                formated_text = line + '\n' + formated_text
        else:
            if re.compile('[\w]').search(line) \
              and not re.compile('^(|[^\w])*%s(|[^\w])*$' % cmd).match(line):
                end_of_text_reached = True
                formated_text = line
    return formated_text
