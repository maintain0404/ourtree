# ruff: noqa: I002
# Relfex conflicts with annotations

from typing import Any

import reflex as rx


class Target(rx.Base):
    src: str


class DOMClickEvent(rx.Base):
    target: Target


def click_coordinate_signature(e: DOMClickEvent):
    return [e.target.src]


class ImageSrcOnClick(rx.Image):
    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            rx.constants.EventTriggers.ON_CLICK: click_coordinate_signature
        }
