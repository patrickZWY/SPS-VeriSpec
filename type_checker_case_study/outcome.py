"""Outcome classification for a closed expression under the oracle.

The progressive loop does not just ask "does it type-check?" -- it records
*what holds*: either a normalized principal-type shape, or the specific error
class the checker reports. Error classes are derived from the failure-message
chain produced by Algorithm W, which is why we run ``infer_top`` directly here
rather than going through ``infer_top_type`` (which discards the reason).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .oracle.syntax import Expr
from .oracle.types import (
    InferFail,
    Ty,
    apply_subst_ty,
    infer_top,
    normalize_ty,
    show_ty,
)

# Ordered most-specific-first; the first substring found in the (nested)
# failure message wins. The innermost cause is appended last by the prefix
# chaining in types.py, so substring search recovers the root cause regardless
# of nesting depth.
_ERROR_SIGNATURES = (
    ("Occurs check failed", "occurs-check"),
    ("Unbound variable", "unbound-variable"),
    ("Condition must be of type Bool", "non-bool-condition"),
    ("Then and Else branch must be of same type", "heterogeneous-if"),
    ("Failed to unify function type", "application-mismatch"),
    ("Failed to unify types", "type-mismatch"),
)


@dataclass(frozen=True)
class Outcome:
    """What the oracle says about one closed expression.

    ``well_typed`` distinguishes the two halves of the ground truth. For
    well-typed expressions, ``type_shape`` is the normalized principal type
    (the canonical key two expressions share when they have the same scheme).
    For ill-typed expressions, ``error_class`` names the failure.
    """

    well_typed: bool
    type_shape: Optional[Ty]
    error_class: Optional[str]

    @property
    def label(self) -> str:
        if self.well_typed:
            assert self.type_shape is not None
            return show_ty(self.type_shape)
        assert self.error_class is not None
        return f"error:{self.error_class}"


def _classify_error(message: str) -> str:
    for needle, label in _ERROR_SIGNATURES:
        if needle in message:
            return label
    return "other"


def classify(expr: Expr) -> Outcome:
    """Run the oracle and report the validated outcome for ``expr``."""
    try:
        subst, ty, _ = infer_top(expr)
    except InferFail as exc:
        return Outcome(False, None, _classify_error(str(exc)))
    shape = normalize_ty(apply_subst_ty(subst, ty))
    return Outcome(True, shape, None)
