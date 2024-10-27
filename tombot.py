#!/usr/bin/env python3

import argparse
import collections
import re
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Callable, TypeAlias, TypedDict

version = "1"


Transformers: TypeAlias = dict[str, Callable[[str], str]]


class Config(TypedDict):
    variables: dict[str, str]


CONFIG_FILE_NAME = "config.toml"

DEFAULT_TRANSFORMERS: Transformers = {
    "to_camel_case": lambda s: re.sub(
        r"(?:^|[\s_-])+(\w)", lambda m: m.group(1).upper(), s
    ),
    "to_kebab_case": lambda s: re.sub(r"[\s_]+", "-", s.lower()),
    "to_snake_case": lambda s: re.sub(r"[\s-]+", "_", s.lower()),
}


class Variables(collections.UserDict):
    delimiter = r"\$"
    idpattern = r"[_a-z][_a-z0-9]*"
    pipe = r"\|"

    _pattern = re.compile(
        rf"""
        {delimiter}(?:
        (?P<escaped>{delimiter})  # escape sequence of two delimiters
        | (?P<named>{idpattern})  # delimiter and an identifier
        | {{(?P<braced>{idpattern}(?:{pipe}{idpattern})*)}}  # delimieter and a braced
                                                             # identifier following
                                                             # optional transformers
        | (?P<invalid>)  # other ill-formed delimiter expressions
        )
        """,
        re.VERBOSE,
    )

    def __init__(self, variables: dict[str, str], transformers: Transformers) -> None:
        super().__init__(variables)
        self._transformers = transformers

    def _transform(self, string: str, *transforms: str) -> str:
        for transform in transforms:
            string = self._transformers[transform](string)
        return string

    def _replacement(self, match: re.Match) -> str:
        if var := match.group("named") or match.group("braced"):
            var, *transforms = re.split(self.pipe, var)
            return self._transform(self.data[var], *transforms)
        if delimeter := match.group("escaped"):
            return delimeter
        raise ValueError(f'template "{match.string}" is invalid')

    def substitute(self, string: str) -> str:
        return re.sub(self._pattern, self._replacement, string)


def build_variables(
    initialdata: dict[str, str],
    transformers: Transformers,
) -> Variables:
    variables = Variables(initialdata, transformers)
    for key, value in variables.items():
        value = variables.substitute(value)
        answer = input(f"{key} [{value}]: ")
        variables[key] = answer or value
    return variables


def load_config(filename: Path) -> Config:
    with filename.open(mode="rb") as f:
        return Config(**tomllib.load(f))


def process_path(path: Path, *, variables: Variables) -> Path:
    parts = (re.sub(r"^dot-", ".", variables.substitute(part)) for part in path.parts)
    return Path(*parts)


def bootstrap_files(src_dir: Path, dst_dir: Path, *, variables: Variables) -> None:
    dirqueue: collections.deque[Path] = collections.deque((src_dir,))
    while dirqueue:
        for child in dirqueue.pop().iterdir():
            if child.is_symlink():
                continue
            if child.is_dir():
                dirqueue.appendleft(child)
            elif child.is_file():
                dst_file_path = dst_dir.joinpath(
                    process_path(child.relative_to(src_dir), variables=variables)
                )
                dst_file_path.parent.mkdir(parents=True, exist_ok=True)
                with child.open("rt") as src_file, dst_file_path.open("wt") as dst_file:
                    while line := src_file.readline():
                        dst_file.write(variables.substitute(line))


def bootstrap_project(
    src_root_dir: Path,
    dst_root_dir: Path,
    *,
    variables: Variables,
) -> None:
    for child in src_root_dir.iterdir():
        if child.is_symlink() or not child.is_dir():
            continue
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            bootstrap_files(child, tmp_dir, variables=variables)
            dst_dir = dst_root_dir.joinpath(
                process_path(child.relative_to(src_root_dir), variables=variables)
            )
            shutil.copytree(tmp_dir, dst_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="bootstrap project from a template")
    parser.add_argument("-t", "--template", required=True, help="template name")
    parser.add_argument("directory", metavar="DIR", help="directory to place files in")
    args = parser.parse_args()

    template_dir = Path(__file__).resolve().parents[1].joinpath(args.template)
    config = load_config(template_dir.joinpath(CONFIG_FILE_NAME))
    variables = build_variables(config["variables"], DEFAULT_TRANSFORMERS)
    bootstrap_project(template_dir, Path(args.directory), variables=variables)
