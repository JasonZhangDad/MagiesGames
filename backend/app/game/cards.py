"""牌的编码与牌堆。

card id: 0..53。id < 52 时 rank = id//4 + 3(3..15,15 即扑克 2),suit = id%4;
52 = 小王(rank 16),53 = 大王(rank 17)。rank 顺序即大小顺序:3<4<...<K<A<2<小王<大王。
顺子/连对/飞机只允许 rank <= 14(到 A 为止)。
"""
import random

SMALL_JOKER = 52
BIG_JOKER = 53

RANK_LABEL = {**{n: str(n) for n in range(3, 11)},
              11: "J", 12: "Q", 13: "K", 14: "A", 15: "2", 16: "王", 17: "王"}


def rank_of(card: int) -> int:
    if card == SMALL_JOKER:
        return 16
    if card == BIG_JOKER:
        return 17
    return card // 4 + 3


def suit_of(card: int) -> int:
    return card % 4 if card < 52 else -1


def new_deck(rng: random.Random | None = None) -> list[int]:
    deck = list(range(54))
    (rng or random).shuffle(deck)
    return deck


def deal(deck: list[int]) -> tuple[list[list[int]], list[int]]:
    """三家各 17 张 + 3 张底牌。"""
    hands = [sorted(deck[i * 17:(i + 1) * 17], key=rank_of) for i in range(3)]
    return hands, deck[51:]
