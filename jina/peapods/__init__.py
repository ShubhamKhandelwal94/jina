__copyright__ = "Copyright (c) 2020 Jina AI Limited. All rights reserved."
__license__ = "Apache-2.0"


from jina import __default_host__
from jina.helper import get_parsed_args
from jina.logging import default_logger
from jina.main.parser import set_pea_parser, set_pod_parser
from jina.peapods.pea import BasePea
from jina.peapods.container import ContainerPea
from jina.peapods.remote import RemotePea, RemoteMutablePod
from typing import Dict, Union   

if False:
    import argparse


def Pea(args: 'argparse.Namespace' = None, allow_remote: bool = True, **kwargs):
    """Initialize a :class:`BasePea`, :class:`RemotePea` or :class:`ContainerPea`

    :param args: arguments from CLI
    :param allow_remote: allow start a :class:`RemotePea`
    :param kwargs: all supported arguments from CLI

    """
    if args is None:
        _, args, _ = get_parsed_args(kwargs, set_pea_parser(), 'Pea')
    if not allow_remote:
        # set the host back to local, as for the remote, it is running "locally"
        if args.host != __default_host__:
            args.host = __default_host__
            default_logger.warning(f'setting host to {__default_host__} as allow_remote set to False')

    if args.host != __default_host__:
        return RemotePea(args)
    elif args.image:
        return ContainerPea(args)
    else:
        return BasePea(args)


def Pod(args: Union['argparse.Namespace', Dict] = None, allow_remote: bool = True, **kwargs):
    """Initialize a :class:`BasePod`, :class:`RemotePod`, :class:`MutablePod` or :class:`RemoteMutablePod`

    :param args: arguments from CLI
    :param allow_remote: allow start a :class:`RemotePod`
    :param kwargs: all supported arguments from CLI
    """
    if args is None:
        _, args, _ = get_parsed_args(kwargs, set_pod_parser(), 'Pod')
    if isinstance(args, dict):
        hosts = set()
        for k in args.values():
            if k:
                if not isinstance(k, list):
                    k = [k]
                for kk in k:
                    if not allow_remote and kk.host != __default_host__:
                        kk.host = __default_host__
                        default_logger.warning(f'host is reset to {__default_host__} as allow_remote=False')
                    hosts.add(kk.host)

        if len(hosts) == 1:
            if __default_host__ in hosts:
                from jina.peapods.pod import BasePod, MutablePod
                return MutablePod(args)
            else:
                return RemoteMutablePod(args)

    if not allow_remote and args.host != __default_host__:
        args.host = __default_host__
        default_logger.warning(f'host is reset to {__default_host__} as allow_remote=False')

    if args.host != __default_host__:
        return RemotePod(args)
    else:
        from jina.peapods.pod import BasePod
        return BasePod(args)
