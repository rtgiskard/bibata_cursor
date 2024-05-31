#!/usr/bin/env python

import logging
import subprocess
import tomllib
import json
import re
import zipfile

from typing import Any
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger()


class Utils:

    @classmethod
    def config_logging(cls, loglevel: int = logging.INFO):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(loglevel)
        console_handler.setFormatter(
            logging.Formatter(fmt='{asctime}.{msecs:03.0f} {levelname[0]}: {message}',
                              style='{',
                              datefmt='%H%M%S'))

        logger = logging.getLogger()
        logger.setLevel(loglevel)
        logger.addHandler(console_handler)

    @classmethod
    def run(cls, cmd: str | list[str], wait: bool = False, **kwargs) -> subprocess.Popen:
        p = subprocess.Popen(cmd, shell=isinstance(cmd, str), **kwargs)
        if p and wait:
            p.wait()
        return p

    @classmethod
    def traverse_dir(cls, rootdir: Path, depth_limit: int = 8) -> Iterable[Path]:
        for path in rootdir.iterdir():
            if path.is_file():
                yield path
            elif path.is_dir() and depth_limit > 0:
                yield from Utils.traverse_dir(path, depth_limit - 1)

    @classmethod
    def zip_dir(cls, cdir: Path, out: Path):
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for item in cls.traverse_dir(cdir):
                zipf.write(item, arcname=item.relative_to(cdir))

    @classmethod
    def svg_convert(cls, src: Path, dst: Path, width: int = 0, height: int = 0):
        cmd = ['rsvg-convert', '-a']

        if dst.suffix == '.svg':
            cmd.extend(['-f', 'svg'])
        elif dst.suffix == '.png':
            cmd.extend(['-f', 'png'])
        else:
            logger.error(f'svg: invalid convert: {src} -> {dst}')
            return

        if width > 0:
            cmd.extend(['-w', str(width)])
        if height > 0:
            cmd.extend(['-h', str(height)])

        cmd.extend(['-o', str(dst), str(src)])
        cls.run(cmd, True)

    @classmethod
    def svg_recolor(cls, color_maps: list[dict], src: Path, dst: Path):
        svg_data = src.read_text()
        for cmap in color_maps:
            svg_data = svg_data.replace(cmap['match'], cmap['replace'])

        if not dst.parent.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)

        dst.write_text(svg_data)


@dataclass
class CursorRender:
    name: str
    desc: str
    dir: str
    color_maps: list[dict[str, str]]


@dataclass
class HyprManifest:
    name: str
    description: str
    version: str = '0.1'
    directory: str = 'hyprcursors'

    def dumps(self):
        lines = []
        lines.append(f'name = {self.name}')
        lines.append(f'description = {self.description}')
        lines.append(f'version = {self.version}')
        lines.append(f'cursors_directory = {self.directory}')
        return '\n'.join(lines)

    def write(self, cdir: str = ''):
        dirPath = cdir if cdir else self.name
        Path(f'{dirPath}/{self.directory}').mkdir(parents=True, exist_ok=True)
        Path(f'{dirPath}/manifest.hl').write_text(self.dumps())


@dataclass
class XManifest:
    name: str
    description: str
    directory: str = 'cursors'

    def dumps(self):
        lines = []
        lines.append('[Icon Theme]')
        lines.append(f'Name={self.name}')
        lines.append(f'Comment={self.description}')
        lines.append('Inherits=hicolor')
        return '\n'.join(lines)

    def write(self, cdir: str = ''):
        dirPath = cdir if cdir else self.name
        Path(f'{dirPath}/{self.directory}').mkdir(parents=True, exist_ok=True)
        Path(f'{dirPath}/index.theme').write_text(self.dumps())


@dataclass
class CursorMeta:
    name: str
    resize: str = 'none' # ^(bilinear)|(nearest)|(none)$
    hotX: float = 0.0    # [0.0, 1.0]
    hotY: float = 0.0    # [0.0, 1.0]
    overrides: list[str] = field(default_factory=list)
    sizes: list[tuple] = field(default_factory=list)
    renders: list[tuple[Path, str, int]] = field(default_factory=list)

    def dumps(self):
        lines = []
        lines.append(f'resize_algorithm = {self.resize}')
        lines.append(f'hotspot_x = {self.hotX:.2f}')
        lines.append(f'hotspot_y = {self.hotY:.2f}')

        if self.overrides:
            lines.append('')
            for item in self.overrides:
                lines.append(f'define_override = {item}')

        if self.sizes:
            lines.append('')
            for item in self.sizes:
                lines.append('define_size = {}'.format(', '.join([str(x) for x in item])))

        return '\n'.join(lines)

    def dumpsX(self):
        lines = []
        for item in self.sizes:
            size, dst = item[0], item[1]
            delay = item[2] if len(item) == 3 else 0
            hotX = int(size * self.hotX)
            hotY = int(size * self.hotY)

            line = f'{size} {hotX} {hotY} {dst}'
            if delay > 0:
                line += f' {delay}'
            lines.append(line)

        return '\n'.join(lines)

    def write(self, cdir: str = '', fmt: str = 'hypr'):
        dirPath = cdir if cdir else self.name
        Path(dirPath).mkdir(exist_ok=True)

        if fmt == 'hypr':
            Path(f'{dirPath}/meta.hl').write_text(self.dumps())
        elif fmt == 'x11':
            Path(f'{dirPath}/meta.x11').write_text(self.dumpsX())

    def render(self, render: CursorRender, cdir: str = ''):
        dirPath = cdir if cdir else self.name
        for src, basename, size in self.renders:
            dst = Path(f'{dirPath}/{basename}')

            if dst.suffix == '.svg':
                Utils.svg_recolor(render.color_maps, src, dst)
            elif dst.suffix == '.png':
                tmp = Path('/tmp/.cursor.0248.svg')
                Utils.svg_recolor(render.color_maps, src, tmp)
                Utils.svg_convert(tmp, dst, size, size)
                tmp.unlink()
            else:
                logger.warn(f'cursor `{self.name}`: undefined render suffix: {dst}')

    def post_process(self, cdir: str = '', fmt: str = 'hypr'):
        dirPath = cdir if cdir else self.name
        if fmt == 'hypr':
            Utils.zip_dir(Path(dirPath), Path(dirPath + '.hlc'))
        elif fmt == 'x11':
            Utils.run(['xcursorgen', '-p', dirPath, f'{dirPath}/meta.x11', f'{dirPath}.xcur'],
                      True,
                      stdout=subprocess.DEVNULL)

    def post_cleanup(self, cdir: str = '', fmt: str = ''):
        dirPath = cdir if cdir else self.name

        Utils.run(['rm', '-rf', dirPath], True)
        if fmt == 'x11':
            Path(f'{dirPath}.xcur').rename(dirPath)

    def scan_size_and_render(self,
                             refDir: str,
                             sizes: list[int],
                             delay: int = 0,
                             fmt: str = 'svg'):
        self.sizes.clear()
        self.renders.clear()

        renderRef: list[Path] = []
        for path in Utils.traverse_dir(Path(refDir)):
            if re.fullmatch(f'{self.name}([_-][0-9]+)?', path.stem):
                renderRef.append(path)

        if len(renderRef) == 0:
            logger.warn(f'cursor `{self.name}`: no renderRef')

        if fmt == 'svg':
            sizes = [0] # for hyprcursor with svg, size is ignored

        for size in sizes:
            basename = f'{self.name}_{size}' if size > 0 else self.name
            for seq, src in enumerate(renderRef):
                dst = basename
                if len(renderRef) > 1:
                    dst += f'_{seq:02}'
                dst += f'.{fmt}'

                if len(renderRef) > 1 and delay > 0:
                    self.sizes.append((size, dst, delay))
                else:
                    self.sizes.append((size, dst))

                self.renders.append((src, dst, size))


class CursorBuilder:
    render: dict[str, dict]       # cursor theme, color map
    config: dict[str, dict]       # left cursor
    config_right: dict[str, dict] # right cursor

    cleanup: bool = True
    outDir: str = 'out'
    renderList: list[str] = [
        'Bibata-Modern-Classic',
        'Bibata-Modern-Ice',
        'Bibata-Modern-Amber',
    ]

    def __init__(self) -> None:
        self.load_config()

    def load_config(self):
        with open('build.toml', 'rb') as f:
            self.config = tomllib.load(f)

        with open('build.right.toml', 'rb') as f:
            self.config_right = tomllib.load(f)

        with open('render.json', 'r') as f:
            self.render = json.load(f)

    def get_cursor_config(self, right: bool = False):
        config = self.config_right if right else self.config
        return config['cursors']

    def get_renders(self) -> Iterable[CursorRender]:
        for name in self.renderList:
            if name not in self.render:
                continue

            spec = self.render[name]
            yield CursorRender(name, spec['desc'], spec['dir'], spec['colors'])

    def ensure_render_source(self, render: CursorRender):
        if not Path(render.dir).exists():
            Utils.run('cd svg && ./link.py', True)

    def get_cursors(self, render: CursorRender, fmt: str = 'svg') -> Iterable[CursorMeta]:
        cursor_config = self.get_cursor_config(render.name.endswith('-Right'))

        fallback = cursor_config['fallback_settings']
        if 'x11_name' in fallback:
            logger.warn('fallback has x11_name: {}'.format(fallback.pop('x11_name')))

        def getValue(params: dict, key: str, default: Any):
            return params[key] if key in params else fallback.get(key, default)

        for name, params in cursor_config.items():
            x11_name = params.get('x11_name', '')

            if not x11_name:
                logger.debug(f'skip cursor `{name}`: no x11_name')
                continue

            hotX = getValue(params, 'x_hotspot', 0) / 256
            hotY = getValue(params, 'y_hotspot', 0) / 256

            x11_symlinks = getValue(params, 'x11_symlinks', [])
            x11_sizes = getValue(params, 'x11_sizes', [])
            x11_delay = getValue(params, 'x11_delay', 0)

            cursor = CursorMeta(name=x11_name, hotX=hotX, hotY=hotY, overrides=x11_symlinks)
            cursor.scan_size_and_render(render.dir, x11_sizes, x11_delay, fmt)
            yield cursor

    def gen_cursor(self, render: CursorRender, fmt: str = 'hypr'):
        logger.info(f'== {render.name} ({fmt})')

        Manifest = HyprManifest if fmt == 'hypr' else XManifest
        cursor_fmt = 'svg' if fmt == 'hypr' else 'png'

        cThemeDir = f'{self.outDir}/{render.name}'
        manifest = Manifest(name=render.name, description=render.desc)
        manifest.write(cThemeDir)

        for cursor in self.get_cursors(render, cursor_fmt):
            logger.info(f'- {render.name}/{cursor.name} ..')
            cdir = f'{cThemeDir}/{manifest.directory}/{cursor.name}'

            cursor.write(cdir, fmt)
            cursor.render(render, cdir)
            cursor.post_process(cdir, fmt)
            if self.cleanup:
                cursor.post_cleanup(cdir, fmt)

    def build(self, fmt: str = 'hypr'):
        for render in self.get_renders():
            self.ensure_render_source(render)
            self.gen_cursor(render, fmt)


if __name__ == '__main__':
    Utils.config_logging()

    builder = CursorBuilder()
    builder.build('hypr')
    builder.build('x11')
