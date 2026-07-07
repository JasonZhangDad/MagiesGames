"""AI 机器人:候选招法生成 + 入门级策略(规则+权重,优先保证合法、不卡局)。

同一套函数同时服务于:机器人补位、玩家托管、出牌提示。
"""
from collections import defaultdict

from .cards import BIG_JOKER, SMALL_JOKER, rank_of
from .patterns import CHAIN_MAX, Pattern, detect

# ---------- 基础工具 ----------


def _groups(hand: list[int]) -> dict[int, list[int]]:
    g: dict[int, list[int]] = defaultdict(list)
    for c in sorted(hand, key=rank_of):
        g[rank_of(c)].append(c)
    return g


def _runs(g: dict, need: int, length: int, min_hi: int) -> list[list[int]]:
    """所有满足 每点数>=need 张、连续 length 个点数、最高点> min_hi 的窗口(低→高)。"""
    ranks = sorted(r for r in g if len(g[r]) >= need and r <= CHAIN_MAX)
    out = []
    for i in range(len(ranks) - length + 1):
        win = ranks[i:i + length]
        if win[-1] - win[0] == length - 1 and win[-1] > min_hi:
            out.append(win)
    return out


def _wings(g: dict, exclude: set[int], count: int, pair: bool) -> list[int] | None:
    """挑翅膀:优先小的孤张/孤对,尽量不拆三张和炸弹。"""
    def pick(max_group: int):
        cards: list[int] = []
        need_each = 2 if pair else 1
        for r in sorted((r for r in g if r not in exclude and len(g[r]) <= max_group
                         and len(g[r]) >= need_each and (not pair or r <= 15)),
                        key=lambda r: (len(g[r]) != need_each, r)):
            cards.extend(g[r][:need_each])
            if len(cards) >= count * need_each:
                return cards[:count * need_each]
        return None
    return pick(2) or pick(4)


def _break_penalty(move: list[int], g: dict) -> int:
    """拆牌惩罚:出的牌把完整对子/三张/炸弹拆散了就加分(越少越好)。"""
    used: dict[int, int] = defaultdict(int)
    for c in move:
        used[rank_of(c)] += 1
    pen = 0
    for r, u in used.items():
        size = len(g[r])
        if 0 < u < size and size >= 2:
            pen += size * size  # 拆炸弹惩罚远高于拆对
    return pen


# ---------- 跟牌候选 ----------

def gen_beats(hand: list[int], last: Pattern) -> list[list[int]]:
    """能压过 last 的所有候选(普通牌型在前按点数升序,炸弹/王炸在最后)。"""
    g = _groups(hand)
    moves: list[list[int]] = []

    if last.kind not in ("bomb", "rocket"):
        k, key, ln = last.kind, last.key, last.length
        if k == "single":
            moves += [[g[r][0]] for r in sorted(g) if r > key]
        elif k == "pair":
            moves += [g[r][:2] for r in sorted(g) if r > key and len(g[r]) >= 2 and r <= 15]
        elif k == "trio":
            moves += [g[r][:3] for r in sorted(g) if r > key and len(g[r]) >= 3]
        elif k in ("trio_single", "trio_pair"):
            for r in sorted(g):
                if r > key and len(g[r]) >= 3:
                    w = _wings(g, {r}, 1, pair=(k == "trio_pair"))
                    if w:
                        moves.append(g[r][:3] + w)
        elif k == "straight":
            moves += [[g[r][0] for r in win] for win in _runs(g, 1, ln, key)]
        elif k == "pair_straight":
            moves += [sum((g[r][:2] for r in win), []) for win in _runs(g, 2, ln, key)]
        elif k in ("plane", "plane_single", "plane_pair"):
            for win in _runs(g, 3, ln, key):
                body = sum((g[r][:3] for r in win), [])
                if k == "plane":
                    moves.append(body)
                else:
                    w = _wings(g, set(win), ln, pair=(k == "plane_pair"))
                    if w:
                        moves.append(body + w)
        elif k in ("four_two", "four_two_pair"):
            for r in sorted(g):
                if r > key and len(g[r]) == 4:
                    w = _wings(g, {r}, 2, pair=(k == "four_two_pair"))
                    if w:
                        moves.append(g[r][:4] + w)

    if last.kind != "rocket":
        min_bomb = last.key if last.kind == "bomb" else 0
        moves += [g[r][:4] for r in sorted(g) if len(g[r]) == 4 and r > min_bomb]
        if SMALL_JOKER in hand and BIG_JOKER in hand:
            moves.append([SMALL_JOKER, BIG_JOKER])
    return moves


# ---------- 自由领出候选 ----------

def gen_leads(hand: list[int]) -> list[list[int]]:
    g = _groups(hand)
    moves: list[list[int]] = []
    # 顺子/连对/飞机:取每个起点能延伸到的最长窗口
    ranks1 = sorted(r for r in g if r <= CHAIN_MAX)
    for need, min_len in ((1, 5), (2, 3), (3, 2)):
        rs = [r for r in ranks1 if len(g[r]) >= need]
        i = 0
        while i < len(rs):
            j = i
            while j + 1 < len(rs) and rs[j + 1] == rs[j] + 1:
                j += 1
            if j - i + 1 >= min_len:
                win = rs[i:j + 1]
                moves.append(sum((g[r][:need] for r in win), []))
            i = j + 1
    # 三带二/三带一
    for r in sorted(g):
        if len(g[r]) == 3:
            for pair in (True, False):
                w = _wings(g, {r}, 1, pair=pair)
                if w:
                    moves.append(g[r][:3] + w)
                    break
            else:
                moves.append(g[r][:3])
    # 对子、单张
    moves += [g[r][:2] for r in sorted(g) if len(g[r]) == 2 and r <= 15]
    moves += [[g[r][0]] for r in sorted(g)]
    return moves


# ---------- 策略 ----------

def _key_of(move: list[int]) -> int:
    p = detect(move)
    return p.key if p else 99


def choose_action(match, seat: int) -> tuple[str, list[int] | None]:
    """机器人/托管的决策。返回 ("play", cards) 或 ("pass", None)。"""
    hand = match.hands[seat]
    g = _groups(hand)

    if match.is_leading():
        whole = detect(hand)
        if whole:  # 一手出完直接赢
            return "play", list(hand)
        cands = gen_leads(hand)
        my_role = match.role_of(seat)
        enemy_min = min((len(match.hands[s]) for s in range(3)
                         if match.role_of(s) != my_role), default=99)
        def lead_score(mv: list[int]) -> float:
            p = detect(mv)
            s = len(mv) * 100 - p.key * 3 - _break_penalty(mv, g)
            if p.key >= 15 and len(hand) > 6:
                s -= 800  # 大牌留后面
            if enemy_min == 1 and p.kind == "single":
                s += p.key * 8 - 120  # 敌方报单:小单等于送牌,单牌越大越好
            return s
        return "play", max(cands, key=lead_score)

    moves = gen_beats(hand, match.last_pattern)
    if not moves:
        return "pass", None
    for mv in moves:
        if len(mv) == len(hand):
            return "play", mv  # 直接出完
    normal = [m for m in moves if detect(m).kind not in ("bomb", "rocket")]
    bombs = [m for m in moves if detect(m).kind in ("bomb", "rocket")]

    last_seat = match.last_seat
    teammate = (match.role_of(seat) == "farmer" and match.role_of(last_seat) == "farmer")
    if teammate:
        if len(match.hands[last_seat]) <= 2:
            return "pass", None  # 队友快赢了,别压
        cheap = [m for m in normal if _key_of(m) <= 11 and _break_penalty(m, g) == 0]
        return ("play", cheap[0]) if cheap else ("pass", None)

    if normal:
        return "play", min(normal, key=lambda m: (_break_penalty(m, g), _key_of(m)))
    opp_left = len(match.hands[last_seat])
    if bombs and (opp_left <= 6 or len(hand) <= 8 or match.last_pattern.key >= 14):
        return "play", bombs[0]
    return "pass", None


def hint(match, seat: int) -> list[int] | None:
    """给人类玩家的提示,复用机器人决策。"""
    action, cards = choose_action(match, seat)
    return cards if action == "play" else None


def choose_call(hand: list[int], max_call: int, must: bool = False) -> int:
    """按牌力估叫分。must=True 时(避免反复流局)至少叫 1。"""
    g = _groups(hand)
    pts = 0.0
    if SMALL_JOKER in hand and BIG_JOKER in hand:
        pts += 3
    elif BIG_JOKER in hand:
        pts += 1
    elif SMALL_JOKER in hand:
        pts += 0.5
    pts += 2 * sum(1 for r in g if len(g[r]) == 4)
    pts += len(g.get(15, []))
    pts += 0.5 * len(g.get(14, []))
    score = 3 if pts >= 4 else 2 if pts >= 3 else 1 if pts >= 2 else 0
    if score <= max_call:
        score = 0
    if must and score == 0:
        score = max(1, max_call + 1) if max_call < 3 else 0
    return score
