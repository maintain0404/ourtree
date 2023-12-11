from __future__ import annotations

import asyncio as aio
import random as rd
from datetime import datetime, timedelta
from itertools import islice, product
from uuid import uuid4

import reflex as rx

from server.services.channel import (
    BaseUserConnection,
    Channel,
    ChannelController,
    Event,
    Object,
    Position,
    User,
)

NICKNAMES = [
    f"{a} {b} {c}"
    for a, b, c in product(
        [
            "활발한",
            "사랑스러운",
            "귀여운",
            "건들거리는",
            "자신감 넘치는",
            "피곤한",
            "놀란",
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

TREE_POSITION = (
    [(rd.randint(50, 351), 590) for x in range(30)]
    + [(rd.randint(70, 301), 540) for x in range(25)]
    + [(rd.randint(90, 281), 490) for x in range(21)]
    + [(rd.randint(110, 261), 440) for x in range(18)]
    + [(rd.randint(130, 241), 390) for x in range(15)]
    + [(rd.randint(150, 221), 340) for x in range(11)]
    + [(rd.randint(170, 201), 290) for x in range(7)]
)


IMAGES = [
    "/decos/bauble.png",
    "/decos/bauble3.png",
    "/decos/bauble4.png",
    "/decos/buable2.png",
    "/decos/candy-cane.svg",
    "/decos/candy-cane2.svg",
    "/decos/christmas-bell.svg",
    "/decos/christmas-bell2.svg",
    "/decos/christmas-candle-clipart.svg",
    "/decos/christmas-candle.svg",
    "/decos/christmas-stocking.svg",
    "/decos/christmas-stocking2.svg",
    "/decos/christmas-stocking3.svg",
    "/decos/christmas-wreath.svg",
    "/decos/Picture1.png",
    "/decos/red-stocking.png",
]


class RxObject(rx.Base, Object):
    ...


class RxEvent(rx.Base, Event):
    ...


class RxUser(rx.Base, User):
    ...


controller = ChannelController()


class CanvasState(rx.State, BaseUserConnection):
    objects: list[RxObject]
    events: list[str]
    _channel: Channel
    _user: RxUser | None
    nickname: str = ""
    new_object: RxObject | None = None
    last_apppended: datetime = datetime(2000, 1, 1, 1, 0, 0)
    modal: bool = False
    selected_src: str = "/decos/candy-cane.svg"
    input_comment: str = ""

    last_event: datetime = datetime(2000, 1, 1, 1, 0, 0)
    last_event_text: str = "Haha"
    show_lateset_event: bool = False
    show_event_history: bool = False

    def toggle_modal(self):
        self.modal = not self.modal

    def toggle_event_history(self):
        self.show_event_history = not self.show_event_history

    async def send(self, event: Event):
        async with self:
            self.events.append(event.as_message())
            self.last_event = datetime.now()
            if event.type == "push-object":
                self.objects = [
                    RxObject(**o.dict()) for o in self._channel.objects.values()
                ]
            elif event.type == "error":
                rx.window_alert("Error!")

    async def recieve(self) -> Event:
        ...

    @rx.background
    async def event_alert(self):
        while True:
            if datetime.now() > self.last_event + timedelta(seconds=5):
                v = False
            else:
                v = True

            async with self:
                self.show_lateset_event = v

            # print(self.events)
            await aio.sleep(0.2)
            yield

    @rx.background
    async def enter_page(self):
        channel_id = self.router.page.path
        async with self:
            # get channel
            self._channel = controller.get_channel(channel_id)
            if self._channel is None:
                self._channel = controller.create_channel(channel_id)

            # Load already pushed objects
            self.objects = [
                RxObject(**o.dict()) for o in self._channel.objects.values()
            ]

            # Join channel
            self._user = RxUser(
                id=self.router.session.client_token,
                nickname=rd.choice(NICKNAMES),
                session=self.router.session.client_token,
                connection=self,
            )
            self.nickname = self._user.nickname
            await self._channel.join(
                User(
                    id=self._user.id,
                    nickname=self._user.nickname,
                    session=self._user.session,
                    connection=self._user.connection,
                )
            )

            return CanvasState.event_alert

    async def push_object(self):
        until = self.last_apppended + timedelta(
            seconds=float(self._channel.policy.cooltime)
        )
        if datetime.now() < until:
            self.modal = False
            self.input_comment = ""
            return rx.window_alert(
                f"{until.strftime('%H:%M:%S')} 이후에 다시 장식을 추가할 수 있어요!"
            )

        pos = rd.choice(TREE_POSITION)
        self.new_object = RxObject(
            id=str(uuid4()),
            url=rd.choice(IMAGES),
            comment=f'"{self.input_comment}" by "{self.nickname}"',
            created_at=datetime.now(),
            position=Position(x=pos[0], y=pos[1]),
        )
        await self._channel.push_object(
            Object(**self.new_object.dict()),
            appender=User(
                id=self._user.id,
                nickname=self._user.nickname,
                session=self._user.session,
                connection=self._user.connection,
            ),
        )
        self.objects.append(self.new_object)
        self.last_apppended = datetime.now()
        self.modal = False
        self.input_comment = ""


def render_object(o: RxObject):
    return rx.tooltip(
        rx.image(
            src=o.url,
            top=o.position.y,
            left=o.position.x,
            position="absolute",
            height=50,
        ),
        label=o.comment,
    )


def render_event(e: str):
    return rx.fragment(rx.box(e), rx.divider())


def latest_event():
    return rx.cond(
        CanvasState.show_lateset_event,
        rx.box(CanvasState.last_event_text, position="fixed", top=10, right=10),
    )


def events_list():
    return rx.fragment(
        rx.drawer(
            rx.drawer_overlay(
                rx.drawer_content(
                    rx.drawer_header(
                        rx.hstack(
                            "Events",
                            rx.spacer(),
                            rx.button(
                                "Events", on_click=CanvasState.toggle_event_history
                            ),
                        )
                    ),
                    rx.drawer_body(rx.foreach(CanvasState.events, render_event)),
                ),
                bg="rgba(0, 0, 0, 0)",
            ),
            is_open=CanvasState.show_event_history,
        ),
        rx.button(
            "Events",
            position="fixed",
            right=10,
            top=10,
            z_index=99,
            on_click=CanvasState.toggle_event_history,
        ),
    )


def deco(src: str):
    return rx.image(
        src=src, height=50, on_click=lambda: CanvasState.set_selected_src(src)
    )


def tree_canvas():
    return rx.fragment(
        rx.container(
            rx.box(
                rx.image(
                    src="/harmonic_Tree.svg", width=400, height=800, position="relative"
                ),
                rx.foreach(CanvasState.objects, render_object),
                # background_image='/harmonic_Tree.svg',
                position="relative",
            ),
        ),
        rx.button(
            "장식하기",
            on_click=CanvasState.toggle_modal,
            position="fixed",
            right=10,
            bottom=10,
        ),
        rx.modal(
            rx.modal_overlay(
                rx.modal_content(
                    rx.modal_header("장식 추가하기"),
                    rx.modal_body(
                        rx.hstack(rx.image(src="/decos/candy-cane.svg", height=50)),
                        rx.divider(),
                        rx.text("다른 사람들과 공유할 코멘트를 작성해주세요."),
                        rx.divider(),
                        rx.input(
                            value=CanvasState.input_comment,
                            on_change=CanvasState.set_input_comment,
                        ),
                    ),
                    rx.modal_footer(
                        rx.button(
                            "장식하기",
                            on_click=CanvasState.push_object,
                        ),
                        rx.button(
                            "닫기", on_click=CanvasState.toggle_modal, margin_left=5
                        ),
                    ),
                )
            ),
            is_open=CanvasState.modal,
        ),
    )


@rx.page(route="/", title="Canvas", on_load=CanvasState.enter_page)
def canvas():
    return rx.fragment(
        events_list(),
        tree_canvas(),
        latest_event(),
        rx.heading(CanvasState.nickname, position="fixed", left=10, top=10),
    )


"/decos/bauble.png",
"/decos/bauble3.png",
"/decos/bauble4.png",
"/decos/buable2.png",
"/decos/candy-cane.svg",
"/decos/candy-cane2.svg",
"/decos/christmas-bell.svg",
"/decos/christmas-bell2.svg",
"/decos/christmas-candle-clipart.svg",
"/decos/christmas-candle.svg",
"/decos/christmas-stocking.svg",
"/decos/christmas-stocking2.svg",
"/decos/christmas-stocking3.svg",
"/decos/christmas-wreath.svg",
"/decos/Picture1.png",
"/decos/red-stocking.png",
