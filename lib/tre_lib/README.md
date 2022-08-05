# tre_lib

Common TRE Python library.

To build:

1. Ensure the version is set correctly in [`version.sh`](./version.sh)
2. Run [`./build.sh`](./build.sh)

Build output file (type `whl`) is created in the `./dist/` folder.

To run tests (from this folder):

```
# python3 runs in lib/tre_lib/tre_lib
(cd tre_lib && python3 -m unittest)
```

To install:

```
pip3 install "$(find dist -name 'tre_lib*.whl')"
```

To uninstall:

```
pip3 uninstall tre_lib --yes
```
