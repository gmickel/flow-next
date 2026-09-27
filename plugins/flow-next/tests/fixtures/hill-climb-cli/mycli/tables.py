"""Lookup tables for the `stats` subcommand, built eagerly at import."""


def _sieve(limit):
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for n in range(2, int(limit**0.5) + 1):
        if flags[n]:
            flags[n * n :: n] = bytearray(len(flags[n * n :: n]))
    return [n for n, flag in enumerate(flags) if flag]


PRIMES = _sieve(3_000_000)
