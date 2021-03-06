import textwrap
from io import StringIO

import pytest

from check_python_versions.sources.travis import (
    XENIAL_SUPPORTED_PYPY_VERSIONS,
    get_travis_yml_python_versions,
    travis_normalize_py_version,
    update_travis_yml_python_versions,
)


def test_get_travis_yml_python_versions(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        python:
          - 2.7
          - 3.6
        matrix:
          include:
            - python: 3.7
            - name: something unrelated
        jobs:
          include:
            - python: 3.4
            - name: something unrelated
        env:
          - TOXENV=py35-docs
          - UNRELATED=variable
    """))
    assert get_travis_yml_python_versions(travis_yml) == [
        '2.7', '3.4', '3.5', '3.6', '3.7',
    ]


def test_get_travis_yml_python_versions_no_list(tmp_path):
    travis_yml = StringIO(textwrap.dedent("""\
        python: 3.7
    """))
    travis_yml.name = '.travis.yml'
    assert get_travis_yml_python_versions(travis_yml) == [
        '3.7',
    ]


def test_get_travis_yml_python_versions_no_python_only_matrix(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        matrix:
          include:
            - python: 3.7
    """))
    assert get_travis_yml_python_versions(travis_yml) == [
        '3.7',
    ]


@pytest.mark.parametrize('s, expected', [
    (3.6, '3.6'),
    ('3.7', '3.7'),
    ('pypy', 'PyPy'),
    ('pypy2', 'PyPy'),
    ('pypy2.7', 'PyPy'),
    ('pypy2.7-5.10.0', 'PyPy'),
    ('pypy3', 'PyPy3'),
    ('pypy3.5', 'PyPy3'),
    ('pypy3.5-5.10.1', 'PyPy3'),
    ('3.7-dev', '3.7-dev'),
    ('nightly', 'nightly'),
])
def test_travis_normalize_py_version(s, expected):
    assert travis_normalize_py_version(s) == expected


def test_update_travis_yml_python_versions():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - pypy
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.4"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_pypy():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["3.8"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 3.8
          - pypy3
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_pypy3():
    # yes this test case is massively unrealistic
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - pypy
        install: pip install -e .
        script: pytest tests
     """)


def test_update_travis_yml_python_versions_keeps_dev():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 3.7
          - 3.8
          - 3.9-dev
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["3.8"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 3.8
          - 3.9-dev
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_dist_trusty(monkeypatch):
    monkeypatch.setitem(
        XENIAL_SUPPORTED_PYPY_VERSIONS, 'pypy', 'pypy2.7-6.0.0')
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        dist: trusty
        python:
          - 2.7
          - pypy
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
          - pypy2.7-6.0.0
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_sudo():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        sudo: false
        dist: xenial
        python:
          - 2.7
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        dist: xenial
        python:
          - 2.7
          - 3.7
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_matrix():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.6
          - 2.7
        matrix:
          include:
            - python: 3.7
              sudo: required
              dist: xenial
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_keeps_matrix():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
        matrix:
          include:
            - python: 2.7
              env: MINIMAL=1
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
        matrix:
          include:
            - python: 2.7
              env: MINIMAL=1
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_one_to_many():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python: 2.7
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.4"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_matrix():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.3
            - python: pypy
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.4"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.4
            - python: pypy
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_matrix_xenial(monkeypatch):
    monkeypatch.setitem(
        XENIAL_SUPPORTED_PYPY_VERSIONS, 'pypy', 'pypy2.7-6.0.0')
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.3
            - python: pypy
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.7
            - python: pypy2.7-6.0.0
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """)
