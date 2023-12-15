# ruff: noqa: I002
# Relfex conflicts with annotations

from typing import Any

import reflex as rx


class NativeEvent(rx.Base):
    offsetX: int
    offsetY: int


class DOMClickEvent(rx.Base):
    nativeEvent: NativeEvent


def click_coordinate_signature(e: DOMClickEvent):
    return [e.nativeEvent.offsetX, e.nativeEvent.offsetY]


class Canvas(rx.Box):
    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            rx.constants.EventTriggers.ON_CLICK: click_coordinate_signature,
        }
