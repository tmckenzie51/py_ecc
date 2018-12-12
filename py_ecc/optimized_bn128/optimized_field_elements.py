from __future__ import absolute_import

from typing import (  # noqa: F401
    cast,
    List,
    Sequence,
    Tuple,
    Union,
)

field_modulus = 21888242871839275222246405745257275088696311157297823662689037894645226208583
FQ2_MODULUS_COEFFS = [1, 0]
FQ12_MODULUS_COEFFS = [82, 0, 0, 0, 0, 0, -18, 0, 0, 0, 0, 0]  # Implied + [1]
FQ2_MC_TUPLES = [(0, 1)]
FQ12_MC_TUPLES = [(i, c) for i, c in enumerate(FQ12_MODULUS_COEFFS) if c]


# Extended euclidean algorithm to find modular inverses for
# integers
def prime_field_inv(a: int, n: int) -> int:
    if a == 0:
        return 0
    lm, hm = 1, 0
    low, high = a % n, n
    while low > 1:
        r = high // low
        nm, new = hm - lm * r, high - low * r
        lm, low, hm, high = nm, new, lm, low
    return lm % n


IntOrFQ = Union[int, "FQ"]


# A class for field elements in FQ. Wrap a number in this class,
# and it becomes a field element.
class FQ(object):
    n = None  # type: int

    def __init__(self, val: IntOrFQ) -> None:
        if isinstance(val, FQ):
            self.n = val.n
        else:
            self.n = val % field_modulus
        assert isinstance(self.n, int)

    def __add__(self, other: IntOrFQ) -> "FQ":
        on = other.n if isinstance(other, FQ) else other
        return FQ((self.n + on) % field_modulus)

    def __mul__(self, other: IntOrFQ) -> "FQ":
        on = other.n if isinstance(other, FQ) else other
        return FQ((self.n * on) % field_modulus)

    def __rmul__(self, other: IntOrFQ) -> "FQ":
        return self * other

    def __radd__(self, other: IntOrFQ) -> "FQ":
        return self + other

    def __rsub__(self, other: IntOrFQ) -> "FQ":
        on = other.n if isinstance(other, FQ) else other
        return FQ((on - self.n) % field_modulus)

    def __sub__(self, other: IntOrFQ) -> "FQ":
        on = other.n if isinstance(other, FQ) else other
        return FQ((self.n - on) % field_modulus)

    def __mod__(self, other: Union[int, "FQ"]) -> "FQ":
        return self.__mod__(other)

    def __div__(self, other: IntOrFQ) -> "FQ":
        on = other.n if isinstance(other, FQ) else other
        assert isinstance(on, int)
        return FQ(self.n * prime_field_inv(on, field_modulus) % field_modulus)

    def __truediv__(self, other: IntOrFQ) -> "FQ":
        return self.__div__(other)

    def __rdiv__(self, other: IntOrFQ) -> "FQ":
        on = other.n if isinstance(other, FQ) else other
        assert isinstance(on, int), on
        return FQ(prime_field_inv(self.n, field_modulus) * on % field_modulus)

    def __rtruediv__(self, other: IntOrFQ) -> "FQ":
        return self.__rdiv__(other)

    def __pow__(self, other: int) -> "FQ":
        if other == 0:
            return FQ(1)
        elif other == 1:
            return FQ(self.n)
        elif other % 2 == 0:
            return (self * self) ** (other // 2)
        else:
            return ((self * self) ** int(other // 2)) * self

    def __eq__(self, other: IntOrFQ) -> bool:  # type:ignore # https://github.com/python/mypy/issues/2783 # noqa: E501
        if isinstance(other, FQ):
            return self.n == other.n
        else:
            return self.n == other

    def __ne__(self, other: IntOrFQ) -> bool:    # type:ignore # https://github.com/python/mypy/issues/2783 # noqa: E501
        return not self == other

    def __neg__(self) -> "FQ":
        return FQ(-self.n)

    def __repr__(self) -> str:
        return repr(self.n)

    def __int__(self) -> int:
        return self.n

    @classmethod
    def one(cls) -> "FQ":
        return cls(1)

    @classmethod
    def zero(cls) -> "FQ":
        return cls(0)


# Utility methods for polynomial math
def deg(p: Sequence[IntOrFQ]) -> int:
    d = len(p) - 1
    while p[d] == 0 and d:
        d -= 1
    return d


def poly_rounded_div(a: Sequence[IntOrFQ],
                     b: Sequence[IntOrFQ]) -> Sequence[IntOrFQ]:
    dega = deg(a)
    degb = deg(b)
    temp = [x for x in a]
    o = [0 for x in a]
    for i in range(dega - degb, -1, -1):
        o[i] = int(o[i] + temp[degb + i] * prime_field_inv(int(b[degb]), field_modulus))
        for c in range(degb + 1):
            temp[c + i] = (temp[c + i] - o[c])
    return [x % field_modulus for x in o[:deg(o) + 1]]


# A class for elements in polynomial extension fields
class FQP(object):
    degree = 0  # type: int
    mc_tuples = None  # type: List[Tuple[int, int]]

    def __init__(self,
                 coeffs: Sequence[IntOrFQ],
                 modulus_coeffs: Sequence[IntOrFQ]=None) -> None:
        assert len(coeffs) == len(modulus_coeffs)
        self.coeffs = coeffs
        # The coefficients of the modulus, without the leading [1]
        self.modulus_coeffs = modulus_coeffs
        # The degree of the extension field
        self.degree = len(self.modulus_coeffs)

    def __add__(self, other: "FQP") -> "FQP":
        assert isinstance(other, type(self))
        return type(self)([
            int(x + y) % field_modulus
            for x, y
            in zip(self.coeffs, other.coeffs)
        ])

    def __sub__(self, other: "FQP") -> "FQP":
        assert isinstance(other, type(self))
        return type(self)([
            int(x - y) % field_modulus
            for x, y
            in zip(self.coeffs, other.coeffs)
        ])

    def __mod__(self, other: Union[int, "FQP"]) -> "FQP":
        return self.__mod__(other)

    def __mul__(self, other: Union[int, "FQP"]) -> "FQP":
        if isinstance(other, int):
            return type(self)([int(c) * other % field_modulus for c in self.coeffs])
        else:
            # assert isinstance(other, self.__class__)
            b = [0] * (self.degree * 2 - 1)
            inner_enumerate = list(enumerate(other.coeffs))
            for i, eli in enumerate(self.coeffs):
                for j, elj in inner_enumerate:
                    b[i + j] += int(eli * elj)
            # MID = len(self.coeffs) // 2
            for exp in range(self.degree - 2, -1, -1):
                top = b.pop()
                for i, c in self.mc_tuples:
                    b[exp + i] -= top * c
            return type(self)([x % field_modulus for x in b])

    def __rmul__(self, other: Union[int, "FQP"]) -> "FQP":
        return self * other

    def __div__(self, other: Union[int, "FQ", "FQP"]) -> "FQP":
        if isinstance(other, int):
            return type(self)([
                int(c) * prime_field_inv(other, field_modulus) % field_modulus
                for c
                in self.coeffs
            ])
        else:
            assert isinstance(other, type(self))
            return self * other.inv()

    def __truediv__(self, other: Union[int, "FQ", "FQP"]) -> "FQP":
        return self.__div__(other)

    def __pow__(self, other: int) -> "FQP":
        o = type(self)([1] + [0] * (self.degree - 1))
        t = self
        while other > 0:
            if other & 1:
                o = o * t
            other >>= 1
            t = t * t
        return o

    # Extended euclidean algorithm used to find the modular inverse
    def inv(self) -> "FQP":
        lm, hm = [1] + [0] * self.degree, [0] * (self.degree + 1)
        low, high = (
            # Ignore mypy yelling about the inner types for the lists being incompatible
            cast(List[IntOrFQ], list(self.coeffs + [0])),  # type: ignore
            cast(List[IntOrFQ], list(self.modulus_coeffs + [1])),  # type: ignore
        )
        low, high = list(self.coeffs + [0]), self.modulus_coeffs + [1]  # type: ignore
        while deg(low):
            r = cast(List[IntOrFQ], poly_rounded_div(high, low))
            r += [0] * (self.degree + 1 - len(r))
            nm = [x for x in hm]
            new = [x for x in high]
            # assert len(lm) == len(hm) == len(low) == len(high) == len(nm) == len(new) == self.degree + 1  # noqa: E501
            for i in range(self.degree + 1):
                for j in range(self.degree + 1 - i):
                    nm[i + j] -= lm[i] * int(r[j])
                    new[i + j] -= low[i] * r[j]
            nm = [x % field_modulus for x in nm]
            new = [int(x) % field_modulus for x in new]
            lm, low, hm, high = nm, new, lm, low
        return type(self)(lm[:self.degree]) / low[0]

    def __repr__(self) -> str:
        return repr(self.coeffs)

    def __eq__(self, other: "FQP") -> bool:     # type: ignore # https://github.com/python/mypy/issues/2783 # noqa: E501
        assert isinstance(other, type(self))
        for c1, c2 in zip(self.coeffs, other.coeffs):
            if c1 != c2:
                return False
        return True

    def __ne__(self, other: "FQP") -> bool:     # type: ignore # https://github.com/python/mypy/issues/2783 # noqa: E501
        return not self == other

    def __neg__(self) -> "FQP":
        return type(self)([-c for c in self.coeffs])

    @classmethod
    def one(cls) -> "FQP":
        return cls([1] + [0] * (cls.degree - 1))

    @classmethod
    def zero(cls) -> "FQP":
        return cls([0] * cls.degree)


# The quadratic extension field
class FQ2(FQP):
    degree = 2
    mc_tuples = FQ2_MC_TUPLES

    def __init__(self, coeffs: Sequence[IntOrFQ]) -> None:
        super().__init__(coeffs, FQ2_MODULUS_COEFFS)
        assert self.degree == 2
        assert self.mc_tuples == FQ2_MC_TUPLES


# The 12th-degree extension field
class FQ12(FQP):
    degree = 12
    mc_tuples = FQ12_MC_TUPLES

    def __init__(self, coeffs: Sequence[IntOrFQ]) -> None:
        super().__init__(coeffs, FQ12_MODULUS_COEFFS)
        assert self.degree == 12
        assert self.mc_tuples == FQ12_MC_TUPLES
