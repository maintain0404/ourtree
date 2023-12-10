"""The dashboard page."""
from __future__ import annotations

from random import randint

import reflex as rx

from server.templates import template


def randcol():
    return "%x" % randint(0, 255)


def randombox(top,  background):
    return rx.box(
        rx.text("hi"),
        position="relative",
        height=50,
        width=50,
        top=top,
        left=top,
        bg=background,
    )


@template(route="/dashboard", title="Dashboard")
def dashboard() -> rx.Component:
    """The dashboard page.

    Returns:
        The UI for the dashboard page.
    """
    return rx.vstack(
        rx.heading("Dashboard", font_size="3em"),
        rx.text("Welcome to Reflex!"),
        rx.text(
            "You can edit this page in ",
            rx.code("{your_app}/pages/dashboard.py"),
        ),
        rx.divider(),
        rx.box(
            rx.foreach(
                [
                    (
                        randint(0, 1000),
                        # randint(0, 1000),
                        f"#{randcol()}{randcol()}{randcol()}",
                    )
                    for _ in range(30)
                ],
                randombox,
            )
        ),
    )
