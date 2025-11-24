# Nyarchiver (Nercone Archiver)
A simple and easy-to-use CLI tool for manipulating compressed files

## Requiments
- CPython 3.9+
- `uv` [PyPI↗︎](https://pypi.org/project/uv/) or `pip3` [PyPI↗︎](https://pypi.org/project/pip/) 
- `nercone-modern` [PyPI↗︎](https://pypi.org/project/nercone-modern/)
- `py7zr` [PyPI↗︎](https://pypi.org/project/py7zr/)
- `rarfile` [PyPI↗︎](https://pypi.org/project/rarfile/)
- `pyzipper` [PyPI↗︎](https://pypi.org/project/pyzipper/)

## Installation

### using uv (recommended)
```
uv tool install nercone-archiver
```

### using pip3

**System Python:**
```
pip3 install nercone-archiver --break-system-packages
```

**Venv Python:**
```
pip3 install nercone-archiver
```

## Update

### using uv (recommended)
```
uv tool install nercone-archiver --upgrade
```

### using pip3

**System Python:**
```
pip3 install nercone-archiver --upgrade --break-system-packages
```

**Venv Python:**
```
pip3 install nercone-archiver --upgrade
```

## Usage

### Interactive mode
```
nyarchiver
```

### Show helps
```
nyarchiver [-h] [--help]
```

### List files in an archive
```
nyarchiver ls <path>
```

### Create a new archive file
```
nyarchiver create [--dest-path <path inside the archive>] [--password <password for encrypted archives>] [--format <force compression format>] <archive> <source>
```

### Extract an archive
```
nyarchiver extract [--password <password for encrypted archives>] <archive> [<dest>]
```

### Add file/dir to an existing archive
```
nyarchiver add [--dest-path <path inside the archive>] [--password <password for encrypted archives>] [--out <output archive path>] [--format <force compression format>] <archive> <source>
```

### Remove file/dir from an existing archive
```
nyarchiver rm [--password <password for encrypted archives>] [--out <output archive path>] [--format <force compression format>] <archive> <target>
```
