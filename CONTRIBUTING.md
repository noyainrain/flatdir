# Contributing to flatdir

## How to contribute

Would you like to contribute to flatdir? Awesome! 💖

1. [Create an issue](https://github.com/noyainrain/flatdir/issues) describing the intended change.
2. Your draft is reviewed by a team member. Make the requested changes, if any.
3. Create a topic branch.
4. Code…
6. Run the code checks and fix any reported issues.
5. [Create a pull request](https://github.com/noyainrain/flatdir/pulls).
7. Your contribution is reviewed by a team member. Make the requested changes, if any.
8. Your contribution is merged by a team member. 🥳

A good issue description contains:

* If the API is modified, any class or function signature
* If the UI is modified, an outline of the text
* If a dependency is introduced, the reason why it is a better choice than alternatives

## Installing development dependencies

To install all development dependencies, run:

```sh
make deps-dev
```

## Running code checks

To run all unit tests, use:

```sh
make
```

All available code checks (type, test and style) can be run with:

```sh
make check
```
