import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_TOKEN_RANK = {**{str(n): n for n in range(3, 11)},
               "J": 11, "Q": 12, "K": 13, "A": 14, "2": 15, "x": 16, "X": 17}


def cards_of(spec: str) -> list[int]:
    """把 "3 3 4 J Q K A 2 x X" 这类牌面串转成互不重复的 card id 列表。"""
    used: dict[int, int] = {}
    out = []
    for tok in spec.split():
        rank = _TOKEN_RANK[tok]
        if rank == 16:
            out.append(52)
        elif rank == 17:
            out.append(53)
        else:
            suit = used.get(rank, 0)
            assert suit < 4, f"同点数超过4张: {tok}"
            used[rank] = suit + 1
            out.append((rank - 3) * 4 + suit)
    assert len(set(out)) == len(out)
    return out
