from __future__ import annotations

import asyncio as aio
from datetime import datetime
from typing import ClassVar
from urllib.parse import urlparse
from uuid import uuid4

import reflex as rx

from server.common.nickname import generate_random_nickname
from server.components.canvas import Canvas
from server.components.image import ImageSrcOnClick
from server.services.channel import (
    BaseUserConnection,
    Channel,
    ChannelController,
    Event,
    Object,
    Position,
    User,
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
    # Channel
    _channel: Channel
    _user: RxUser | None
    nickname: str

    # For rendering canvas
    objects: list[RxObject]
    events: list[str]

    # for batch image
    SELECTED_BORDER: ClassVar[str] = "1px solid purple"
    comment: str = ""
    selected_image_uri: str = ""
    batch_mode: bool = False

    def set_selected_image_uri(self, s: str):
        self.selected_image_uri = urlparse(s).path

    def go_batch_mode(self):
        self.batch_mode = True

    async def batch_object(self, x, y):
        if not self.batch_mode:
            return

        self.new_object = RxObject(
            id=str(uuid4()),
            url=self.selected_image_uri,
            comment=self.comment,
            created_at=datetime.now(),
            position=Position(x=x, y=y),
        )
        await self._channel.push_object(
            Object(**self.new_object.dict()),
            appender=User(
                id=self._user.id,
                nickname=self._user.nickname,
                session=self._user.id,
                connection=self._user.connection,
            ),
        )
        self.objects.append(self.new_object)
        self.last_push = datetime.now()
        self.batch_mode = False

    async def send(self, event: Event):
        async with self:
            self.events = self.events + [event.as_message()]
            self.last_event = datetime.now()
            self.notice(self.events[-1])
            if event.type == "push-object":
                self.objects = [
                    RxObject(**o.dict()) for o in self._channel.objects.values()
                ]
            elif event.type == "error":
                rx.window_alert("Error!")

    async def recieve(self) -> Event:
        ...

    show_event_history: bool = False
    has_notice: bool = False
    notice_message: str = ""

    def toggle_event_history(self):
        self.show_event_history = not self.show_event_history

    def notice(self, message: str):
        # Picking 불가능해서 꼼수로 router_data를 사용함
        prev_task: aio.Task | None = self.router_data.get("task", None)

        if prev_task is not None and not prev_task.done():
            prev_task.cancel()
        self.router_data["task"] = aio.create_task(self.hide_notice(), name="notice")
        self.notice_message = message
        self.has_notice = True

    @rx.var
    def show_notice(self) -> bool:
        return self.has_notice and not self.show_event_history

    async def hide_notice(self):
        await aio.sleep(3)
        async with self:
            self.has_notice = False

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
                nickname=generate_random_nickname(),
                session=self.router.session.client_token,
                connection=self,
            )
            self.nickname = self._user.nickname
            await self._channel.join(
                User(
                    id=self._user.id,
                    nickname=self._user.nickname,
                    session=self._user.id,
                    connection=self._user.connection,
                )
            )


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
        z_index=-2,
    )


def render_event(e: str):
    return rx.fragment(rx.box(rx.text(e)), rx.divider())


def notice():
    return rx.cond(
        CanvasState.show_notice,
        rx.box(
            CanvasState.notice_message,
            text_overflow='ellipsis',
            width='20em',
            height='5em',
            position="fixed",
            padding='1em',
            top=10,
            right=10,
            z_index=999,
            bg="white",
            border_radius=5,
            box_shadow="5px 5px 5px 5px gray",
        ),
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
                    rx.drawer_body(
                        rx.vstack(rx.foreach(CanvasState.events, render_event))
                    ),
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


class AddingDecoModal(CanvasState):
    SELECTED_BORDER: ClassVar[str] = "1px solid purple"
    show_modal: bool = False
    prompt: str = ""
    images: list[str] = IMAGES
    borders: dict[str, str] = {k: "1px solid rgba(0,0,0,0)" for k in IMAGES}

    def toggle_modal(self):
        self.show_modal = not self.show_modal

    def go_batch_mode(self):
        self.show_modal = False
        return CanvasState.go_batch_mode

    def select_image(self, s: str):
        self.borders = {k: "1px solid rgba(0,0,0,0)" for k in IMAGES}
        self.borders[urlparse(s).path] = self.SELECTED_BORDER
        return super().set_selected_image_uri(s)


def deco_adding_modal():
    comment_asking_text = '장식과 함께할 댓글을 작성해주세요.'

    def comment_input():
        return rx.fragment(
            rx.divider(),
            rx.text(
                comment_asking_text,
                padding_top="1em",
                padding_bottom="1em",
            ),
            rx.divider(),
            rx.input(value=CanvasState.comment, on_change=CanvasState.set_comment),
        )

    def render_image(o):
        return rx.box(
            rx.center(
                ImageSrcOnClick.create(
                    src=o[0],
                    width=50,
                    object_fit="contain",
                    on_click=AddingDecoModal.select_image,
                ),
                border=o[1],
                padding="5px",
                border_radius="3px",
            )
        )

    prepared_tab_panel = rx.tab_panel(
        rx.responsive_grid(
            rx.foreach(
                AddingDecoModal.borders,
                render_image,  # 원래 비율에 맞추게
            ),
            columns=[3, 4, 5, 6],
            spacing="4",
            height="20em",
            max_height="20em",
            overflow="auto",
        ),
        comment_input(),
    )

    upload_tab_panel = rx.tab_panel(
        rx.upload(
            rx.flex(
                rx.box("사진을 드래그하거나 여기를 클릭해서 사진을 선택해주세요."),
            ),
            height="20em",
            justify_content="center",
            align_items="center",
        ),
        rx.selected_files(),
        comment_input(),
    )

    return rx.modal(
        rx.modal_overlay(
            rx.modal_content(
                rx.modal_header("장식 추가하기"),
                rx.modal_body(
                    rx.tabs(
                        rx.tab_list(rx.tab("프리셋"), rx.tab("직접 업로드")),
                        rx.tab_panels(prepared_tab_panel, upload_tab_panel),
                    ),
                ),
                rx.modal_footer(
                    rx.button(
                        "장식하기",
                        on_click=AddingDecoModal.go_batch_mode,
                    ),
                    rx.button(
                        "닫기", on_click=AddingDecoModal.toggle_modal, margin_left=5
                    ),
                ),
            )
        ),
        is_open=AddingDecoModal.show_modal,
    )


def tree_canvas():
    return rx.fragment(
        rx.container(
            rx.image(
                src="/harmonic_Tree.svg", width=400, height=800, position="absolute"
            ),
            Canvas.create(
                width=400,
                height=800,
                z_index=1,
                position="relative",
                on_click=CanvasState.batch_object,
            ),
            rx.foreach(CanvasState.objects, render_object),
            position="relative",
        ),
        deco_adding_modal(),
        rx.button(
            "장식하기",
            on_click=AddingDecoModal.toggle_modal,
            position="fixed",
            right=10,
            bottom=10,
        ),
    )


@rx.page(route="/", title="Canvas", on_load=CanvasState.enter_page)
def canvas():
    return rx.fragment(
        events_list(),
        tree_canvas(),
        notice(),
        rx.heading(CanvasState.nickname, position="fixed", left=10, top=10),
    )
