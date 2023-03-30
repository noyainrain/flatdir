# flatdir

Web aggregator of flat ads from different real estate companies.

You can give it a try at [berlin.flat.directory](https://berlin.flat.directory/).

## System requirements

The following software must be installed on your system:

* Python >= 3.9

flatdir should work on any [POSIX](https://en.wikipedia.org/wiki/POSIX) system.

## Installing dependencies

To install all dependencies, run:

```sh
make deps
```

## Running flatdir

To run flatdir, use:

```sh
python3 -m flatdir
```

The configuration file `flatdir.ini` is used, if present. See `flatdir/res/default.ini` for
documentation.

## Contributors

* Sven Pfaller &lt;sven AT inrain.org>

Copyright (C) 2023 flatdir contributors
