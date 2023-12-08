from __future__ import annotations

import gc

import pytest

from server.services.channel import (
    BaseUserConnection,
    Channel,
    ChannelController,
    ChannelPolicy,
    ErrorEvent,
    Event,
    Object,
    Position,
    PushObjectEvent,
    User,
)


@pytest.fixture
def channel_controller():
    return ChannelController(
        channels={},
    )


@pytest.fixture
def channel(channel_controller: ChannelController):
    chan = Channel(id="test")
    channel_controller.channels["test"] = chan
    chan.channel_controller = channel_controller
    chan.policy = ChannelPolicy(max_objects=1, max_ccu=1, timeout=0.1)
    return chan


@pytest.fixture
def user():
    return User(
        id="1", nickname="one", connection=BaseUserConnection(), session="session"
    )


def test_create_channel(channel_controller: ChannelController):
    channel_controller.create_channel("test")

    assert "test" in channel_controller.channels.keys()


async def test_join_channel_success(channel: Channel, user: User):
    await channel.join(user=user)

    assert user.id in channel.users.keys()
    assert len(channel.users) == 1


async def test_join_channel_fail_when_full(channel: Channel, user: User):
    await channel.join(user=user)
    error = None

    class TempConn(BaseUserConnection):
        async def send(self, data: Event):
            nonlocal error
            error = data

    conn = TempConn()
    await channel.join(user=User(id="2", nickname="two", session="ss", connection=conn))

    assert isinstance(error, ErrorEvent)
    assert error.code == "full"


async def test_join_channel_fail_with_timeout(
    channel: Channel, user: User, monkeypatch: pytest.MonkeyPatch
):
    error = None

    async def fail():
        raise TimeoutError

    monkeypatch.setattr(channel.event_lock, "acquire", fail)

    class TempConn(BaseUserConnection):
        async def send(self, data: Event):
            nonlocal error
            error = data

    conn = TempConn()
    await channel.join(user=User(id="2", nickname="two", session="ss", connection=conn))

    assert isinstance(error, ErrorEvent)
    assert error.code == "timeout"


async def test_push_object_success(channel: Channel, user: User):
    ev = None
    channel.users[user.id] = user

    class TempConn(BaseUserConnection):
        async def send(self, data: Event):
            nonlocal ev
            ev = data

    conn = TempConn()
    new_user = User(id="2", nickname="two", session="ss", connection=conn)
    channel.users["2"] = new_user

    await channel.push_object(
        Object(id="obj", url="url", comment="hello", position=Position(x=1, y=1)), user
    )

    assert len(channel.objects) == 1
    assert isinstance(ev, PushObjectEvent)
    assert ev.object.id == "obj"


async def test_push_object_success_when_full(channel: Channel, user: User):
    ev = None
    channel.users[user.id] = user

    class TempConn(BaseUserConnection):
        async def send(self, data: Event):
            nonlocal ev
            ev = data

    conn = TempConn()
    new_user = User(id="2", nickname="two", session="ss", connection=conn)
    channel.users["2"] = new_user

    channel.objects["old"] = (
        Object(id="old", url="url", comment="hello", position=Position(x=1, y=1)),
        user,
    )

    await channel.push_object(
        Object(id="obj", url="url", comment="hello", position=Position(x=1, y=1)), user
    )

    assert len(channel.objects) == 1
    assert isinstance(ev, PushObjectEvent)
    assert ev.object.id == "obj"


async def test_join_channel_fail_with_timeout(
    channel: Channel, monkeypatch: pytest.MonkeyPatch
):
    send = None
    recv = None

    async def fail():
        raise TimeoutError

    monkeypatch.setattr(channel.event_lock, "acquire", fail)

    class TempConnSender(BaseUserConnection):
        async def send(self, data: Event):
            nonlocal send
            send = data

    class TempConnReceiver(BaseUserConnection):
        async def send(self, data: Event):
            nonlocal recv
            recv = data

    sender = User(
        id="sender", nickname="sender", session="session", connection=TempConnSender()
    )
    reciever = User(
        id="reciever",
        nickname="reciever",
        session="session",
        connection=TempConnReceiver(),
    )
    channel.users["sender"], channel.users["reciever"] = sender, reciever

    await channel.push_object(
        Object(id="obj", url="url", comment="hello", position=Position(x=1, y=1)),
        sender,
    )

    assert isinstance(send, ErrorEvent)
    assert send.code == "timeout"

    assert recv is None


async def test_leave_channel_solo_success(
    channel_controller: ChannelController, channel: Channel, user: User
):
    channel.users[user.id] = user

    await channel.leave(user)

    assert len(channel.users) == 0
    assert channel.id not in channel_controller.channels.keys()


async def test_leave_channel_2ormore_success(
    channel_controller: ChannelController, channel: Channel, user: User
):
    channel.users[user.id] = user
    channel.users["temp"] = User(
        id="temp", nickname="temp", session="ss", connection=BaseUserConnection()
    )

    await channel.leave(user)

    assert len(channel.users) == 1
    assert channel.id in channel_controller.channels.keys()


def test_close_channel(channel_controller: ChannelController):
    channel = Channel(id="test")
    channel_controller.channels["test"] = channel

    pre_gc_ref = gc.get_referrers(channel)
    assert channel in channel_controller.channels.values()
    assert channel_controller.channels in pre_gc_ref

    channel_controller.close_channel("test")

    assert channel_controller.channels not in gc.get_referrers(channel)
    assert channel not in gc.get_referrers(channel_controller)
