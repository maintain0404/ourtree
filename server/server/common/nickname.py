from __future__ import annotations

import random as rd
from itertools import product

RANDOM_NICKNAMES = [
    f"{a} {b} {c}"
    for a, b, c in product(
        [
            "활발한",
            "사랑스러운",
            "귀여운",
            "건들거리는",
            "자신감 넘치는",
            "놀란",
            "피곤한",
            "수다스러운",
            "조용한",
            "친절한",
        ],
        [c1 + c2 + c3 + c4 for c1, c2, c3, c4 in product("IE", "NS", "FT", "PJ")],
        [
            "고양이",
            "범고래",
            "토끼",
            "호랑이",
            "강아지",
            "하마",
            "펭귄",
            "비둘기",
            "원숭이",
            "거북이",
            "사자",
            "북극곰",
        ],
    )
]


def generate_random_nickname():
    return rd.choice(RANDOM_NICKNAMES)