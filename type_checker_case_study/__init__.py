"""Type-checker case study: progressive, test-validated composition.

This package realizes the README's priority milestone -- use composable,
combinator-style expressions to expose type-checker errors, by extracting the
elementary expression forms and progressively composing them, validating each
composite against a trusted oracle rather than proving everything up front.
"""
