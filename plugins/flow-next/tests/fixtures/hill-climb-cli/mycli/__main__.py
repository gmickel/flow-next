import sys

from mycli import VERSION, plugins, tables


def main(argv):
    registry = plugins.validate(plugins.discover())
    if argv[:1] == ["--version"]:
        print(f"mycli {VERSION}")
        return 0
    if argv[:1] == ["list"]:
        for name in sorted(registry):
            print(name)
        return 0
    if argv[:1] == ["stats"]:
        print(f"primes: {len(tables.PRIMES)}")
        return 0
    print("usage: mycli --version | list | stats", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
