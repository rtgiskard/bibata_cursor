import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.cursor_utils import CursorBuilder, CursorMeta, CursorRender


class ScalableCursorTests(unittest.TestCase):
    def test_animation_keeps_numeric_frame_order_and_delays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            for number, color in [(10, '#0000ff'), (2, '#00ff00'), (1, '#ff0000')]:
                (source / f'wait-{number}.svg').write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256">'
                    f'<path fill="{color}" d="M0 0H256V256H0Z"/></svg>'
                )
            cursor = CursorMeta('wait', hotX=0.5, hotY=0.25, overrides=['watch'])
            cursor.scan_size_and_render(str(source), [24, 48], delay=40)
            target = root / 'wait'
            cursor.write(str(target), 'svg')
            cursor.render(CursorRender('test', '', str(source), []), str(target))
            cursor.post_setup(str(target), 'svg')

            frames = json.loads((root / 'watch' / 'metadata.json').read_text())
            colors = [
                ElementTree.parse(target / frame['filename']).getroot()[0].attrib['fill']
                for frame in frames
            ]
            self.assertEqual(colors, ['#ff0000', '#00ff00', '#0000ff'])
            self.assertEqual([frame['delay'] for frame in frames], [40, 40, 40])
            for frame in frames:
                self.assertEqual(frame['nominal_size'], 256)
                self.assertEqual(frame['hotspot_x'], 128)
                self.assertEqual(frame['hotspot_y'], 64)

    def test_right_hand_hotspots_keep_fractional_source_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            (source / 'left_ptr.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256">'
                '<path fill="red" d="M0 0H256V256H0Z"/></svg>'
            )
            builder = CursorBuilder()
            builder.outDir = tmp
            builder.config_right = {
                'cursor_defaults': {},
                'cursors': {
                    'left_ptr': {
                        'x11_name': 'left_ptr',
                        'x_hotspot': 64.5,
                        'y_hotspot': 128.5,
                        'x11_symlinks': ['default'],
                    }
                },
            }
            render = CursorRender('test-Right', '', str(source), [])
            builder.gen_cursor(render, 'svg')
            cursor = Path(tmp) / 'test-Right' / 'cursors_scalable' / 'default'
            frames = json.loads((cursor / 'metadata.json').read_text())
            self.assertEqual(len(frames), 1)
            frame = frames[0]
            self.assertEqual(frame['hotspot_x'] / frame['nominal_size'], 64.5 / 256)
            self.assertEqual(frame['hotspot_y'] / frame['nominal_size'], 128.5 / 256)
            self.assertEqual(frame['delay'], 0)


if __name__ == '__main__':
    unittest.main()
