#!/usr/bin/env python

import os
import subprocess
import tomllib
import logging

from typing import Any
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger()
'''
- workflow:
    . xcursor: svg -> recolor -> png -> xcursor
    . hyprcursor: svg -> recolor -> hyprcursor

- tools:
    . recolor: cbmp, sed
    . xcursor: clickgen, xcursorgen

- layout:
    ~/.local/share/icons/myCursorTheme/manifest.hl

    export HYPRCURSOR_THEME = myCursorTheme
'''


class Utils:

    @staticmethod
    def config_logging(loglevel: int = logging.DEBUG):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(loglevel)
        console_handler.setFormatter(
            logging.Formatter(fmt='{asctime}.{msecs:03.0f} {levelname[0]}: {message}',
                              style='{',
                              datefmt='%H%M%S'))

        logger = logging.getLogger()
        logger.setLevel(loglevel)
        logger.addHandler(console_handler)

    @staticmethod
    def run(cmd: str | list[str], wait: bool = False, **kwargs) -> subprocess.Popen:
        p = subprocess.Popen(cmd, shell=isinstance(cmd, str), **kwargs)
        if p and wait:
            p.wait()
        return p


@dataclass
class HyprManifest:
    name: str
    description: str
    version: str = '0.1'
    directory: str = 'hyprcursors'

    @property
    def cursor_root(self) -> str:
        return f'{self.name}/{self.directory}'

    def dumps(self):
        lines = []
        lines.append(f'name = {self.name}')
        lines.append(f'description = {self.description}')
        lines.append(f'version = {self.version}')
        lines.append(f'cursors_directory = {self.directory}')
        return '\n'.join(lines)

    def write(self, path: str = 'manifest.hl'):
        Path(self.cursor_root).mkdir(parents=True)
        with open(f'{self.name}/{path}', 'w') as f:
            f.write(self.dumps())


@dataclass
class CursorMeta:
    name: str
    resize: str = 'none' # ^(bilinear)|(nearest)|(none)$
    hotX: float = 0.0    # [0.0, 1.0]
    hotY: float = 0.0    # [0.0, 1.0]
    override: list[str] = field(default_factory=list)
    size: list[tuple[str]] = field(default_factory=list)

    def dumps(self):
        lines = []
        lines.append(f'resize_algorithm = {self.resize}')
        lines.append(f'hotspot_x = {self.hotX}')
        lines.append(f'hotspot_y = {self.hotY}')

        if self.override:
            lines.append('')
            for item in self.override:
                lines.append(f'define_override = {item}')

        if self.size:
            lines.append('')
            for item in self.size:
                lines.append(f'define_size = {', '.join(item)}')

        return '\n'.join(lines)

    def write(self, path: str = 'meta.hl'):
        dir_path = f'{self.name}'
        Path(dir_path).mkdir()
        with open(f'{dir_path}/{path}', 'w') as f:
            f.write(self.dumps())


class CursorBuilder:
    config: dict[str, Any]

    def __init__(self) -> None:
        self.load_config()

    def load_config(self, path: str = 'build.toml'):
        with open(path, 'rb') as f:
            self.config = tomllib.load(f)

    def get_cursors(self) -> Iterable[CursorMeta]:
        fallback: dict[str, Any] = self.config['cursors'].pop('fallback_settings')
        getV = lambda params, key, default: params.get(key, fallback.get(key, default))

        for name, params in self.config['cursors'].items():
            x11_name = params.get('x11_name', '')
            x11_symlinks = getV(params, 'x11_symlinks', [])
            hotX = getV(params, 'x_hotspot', 0) / 256 # TODO: ..
            hotY = getV(params, 'y_hotspot', 0) / 256 # TODO: ..

            if name != x11_name:
                logger.debug(f'name: {name} -> {x11_name}')

            if not x11_name:
                logger.warning(f'skip non x11_name: {name}')
                continue

            yield CursorMeta(name=x11_name, override=x11_symlinks, hotX=hotX, hotY=hotY)

    def gen_hyprcursor(self):
        desc = self.config.get('theme', {}).get('name', '')

        manifest = HyprManifest(name='Bibata', description=desc)
        manifest.write()

        counter = 0
        os.chdir(manifest.cursor_root)

        for cursor in self.get_cursors():
            logger.info(f'-> {cursor.name} ..')
            cursor.write()
            counter += 1

        logger.info(f'cursor count: {counter}')


if __name__ == '__main__':
    Utils.config_logging()

    builder = CursorBuilder()
    builder.gen_hyprcursor()
