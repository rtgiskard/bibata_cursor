#!/usr/bin/env python

from pathlib import Path


def gen_symlinks(src_dirs: list[str], dst_dir: str) -> None:
    dst = Path(dst_dir)
    if not dst.is_dir():
        dst.mkdir()

    print(f'== symlink for `{dst_dir}`:')
    for src_dir in src_dirs:
        for item in Path(src_dir).iterdir():
            link = dst / item.name
            if link.exists():
                link.unlink()

            print(f'-> {link.name} ..')
            link.symlink_to(item.relative_to(dst, walk_up=True))


# Linking Bibata Modern
gen_symlinks(
    [
        'groups/modern',
        'groups/modern-arrow',
        'groups/shared',
        'groups/hand',
    ],
    'modern',
)

# Linking Bibata Modern Right
gen_symlinks(
    [
        'groups/modern-right',
        'groups/modern-arrow',
        'groups/shared',
        'groups/hand-right',
    ],
    'modern-right',
)

# Linking Bibata Original
gen_symlinks(
    [
        'groups/original',
        'groups/original-arrow',
        'groups/shared',
        'groups/hand',
    ],
    'original',
)

# Linking Bibata Original Right
gen_symlinks(
    [
        'groups/original-right',
        'groups/original-arrow',
        'groups/shared',
        'groups/hand-right',
    ],
    'original-right',
)
