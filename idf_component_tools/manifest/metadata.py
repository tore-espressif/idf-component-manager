# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from ..errors import MetadataError
from .constants import KNOWN_BUILD_METADATA_FIELDS, KNOWN_INFO_METADATA_FIELDS
from .schemas import serialize_list_of_list_of_strings

try:
    import typing as t
except ImportError:
    pass


def _flatten_manifest_file_keys(manifest_tree, stack=None, level=1):
    if stack is None:
        stack = []

    res = []
    if isinstance(manifest_tree, dict):
        for k, v in manifest_tree.items():
            cur = stack + [k]

            if k == 'dependencies' and level == 1:
                if isinstance(v, dict):
                    for _k, _v in v.items():
                        # _k doesn't matter here, use '*'
                        res.extend(_flatten_manifest_file_keys(_v, cur + ['*'], level + 1))
                else:
                    # List of components should be a dictionary.
                    raise MetadataError(
                        'List of dependencies should be a dictionary.'
                        ' For example:\ndependencies:\n  some-component: ">=1.2.3,!=1.2.5"')
            else:
                res.extend(_flatten_manifest_file_keys(v, cur, level + 1))

    elif isinstance(manifest_tree, (list, set)):
        for item in manifest_tree:
            res.extend(_flatten_manifest_file_keys(item, stack + ['type:array'], level + 1))
    else:
        if isinstance(manifest_tree, bool):
            res.append(stack + ['type:boolean'])
        elif isinstance(manifest_tree, str):
            res.append(stack + ['type:string'])
        elif isinstance(manifest_tree, (int, float)):
            res.append(stack + ['type:number'])
        else:
            raise MetadataError('Unknown key type {} for key {}'.format(type(manifest_tree), manifest_tree))

    return res


class Metadata(object):
    def __init__(self, build_metadata_keys=None, info_metadata_keys=None):
        self.build_metadata_keys = build_metadata_keys or []
        self.info_metadata_keys = info_metadata_keys or []

    @classmethod
    def load(cls, manifest_tree):  # type: (dict) -> 'Metadata'
        build_metadata_keys, info_metadata_keys = cls._parse_metadata_from_manifest(manifest_tree)

        return cls(build_metadata_keys, info_metadata_keys)

    @staticmethod
    def _parse_metadata_from_manifest(manifest_tree):  # type: (t.Any) -> tuple[list[str], list[str]]
        metadata_keys = _flatten_manifest_file_keys(manifest_tree)
        build_metadata_keys = []
        info_metadata_keys = []

        errors = []

        for _k in metadata_keys:
            if _k[0] in KNOWN_BUILD_METADATA_FIELDS:
                if _k not in build_metadata_keys:
                    build_metadata_keys.append(_k)
            elif _k[0] in KNOWN_INFO_METADATA_FIELDS:
                if _k not in info_metadata_keys:
                    info_metadata_keys.append(_k)
            else:
                errors.append('Unknown key {}'.format('-'.join(_k)))

        if errors:
            raise MetadataError(*errors)

        return serialize_list_of_list_of_strings(build_metadata_keys), serialize_list_of_list_of_strings(
            info_metadata_keys)
