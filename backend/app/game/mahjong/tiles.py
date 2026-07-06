"""四川麻将牌编码与牌墙:只有万筒条,无字牌。

kind:0-8 万1-9,9-17 筒1-9,18-26 条1-9。tile id = kind*4 + 第几张(0..3),共 108 张。
"""
import random

SUITS = ["万", "筒", "条"]
NUM_KINDS = 27


def kind_of(tile: int) -> int:
    return tile // 4


def kind_label(kind: int) -> str:
    return f"{kind % 9 + 1}{SUITS[kind // 9]}"


def suit_of(kind: int) -> int:
    """0万 1筒 2条"""
    return kind // 9


def new_wall(rng: random.Random | None = None) -> list[int]:
    wall = list(range(108))
    (rng or random).shuffle(wall)
    return wall
