import logging
import pprint

log = logging.getLogger('cord.objects')


def listof(method, field='id'):
    """Make a list of an iterable using a method."""
    def make_list_of(iterable):
        if field is None:
            return [method(el) for el in iterable]

        return [method(el[field]) for el in iterable]

    return make_list_of


def _use_method(method, field):
    def use_method(obj):
        return method(obj[field])
    
    return use_method


def _timestamp(string):
    """Return a `datetime.datetime` object from a discord timestamp string"""
    return string


class Identifiable:
    def __init__(self, client, payload):
        self.id = int(payload['id'])
        self._raw = payload
        self._fields = []
        self.client = client

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f'Identifiable<id={self.id}>'

    def has_fields(self, *fields):
        """If an object has all the fields defined"""
        return all([hasattr(self, field) for field in fields])

    @property
    def full(self):
        """If the object has all attributes
        described in :attr:`Identifiable._fields`"""
        return self.has_fields(self._fields)

    def fill(self, raw_object, in_update=False):
        """Fill an object with data.

        The object needs to have a _fields attribute,
        it is a list of strings or tuples.
        """
        for field in self._fields:
            if isinstance(field, tuple):
                val = raw_object[field[1]]

                try:
                    self_field = field[2]
                except Exception:
                    self_field = field[1]

                if val is None:
                    setattr(self, self_field, None)
                else:
                    setattr(self, self_field, field[0](val))
            else:
                try:
                    val = raw_object[field]
                except KeyError as err:
                    if in_update:
                        continue
                    else:
                        raise err

                setattr(self, field, val)

    def update(self, raw_object):
        """Update an object with new data."""
        try:
            self.fill(raw_object, True)
        except KeyError:
            pass


class UnavailableGuild(Identifiable):
    """Unavailable Guild object.

    Unavailable Guilds are sent by discord
    when it sends the READY packet, then it
    dispatches GUILD_CREATE events for each
    guild the client is in.

    Attributes
    ----------
    id: int
        Unavailable guild's ID.
    """
    def __init__(self, client, raw_guild):
        super().__init__(client, raw_guild)
        self._fields = [(int, 'id')]
        self.fill(raw_guild)

    def __repr__(self):
        return f'UnavailableGuild<id={self.id}>'


class Guild(Identifiable):
    """Guild object.

    Attributes
    ----------
    name: str
        Guild name.
    region: str
        Guild's voice region.
    owner_id: int
        Guild's owner, as a snowflake ID.
    verification_level: int
        Guild's verification level.
    features: List[str]
        Guild features.
    large: bool
        True if the guild is large.
    unavailable: bool
        If the guilds is unavailable to the client.
    members: List[Member]
        Guild members.
    channels: List[Channel]
        Guild channels.
    """
    def __init__(self, client, raw_guild):
        super().__init__(client, raw_guild)

        self._fields = ['name', 'region', (int, 'owner_id'),
                        'verification_level', 'features', 'large',
                        'unavailable', 'members',
                        (listof(client.state.get_channel), 'channels')]

        self.fill(raw_guild)

    def __repr__(self):
        return f'Guild<id={self.id} name={self.name}>'


class TextChannel(Identifiable):
    """A text channel."""
    def __init__(self, client, raw_channel):
        super().__init__(client, raw_channel)

        self._fields = [
            (int, 'guild_id'), 'name', 'type', 'position',
            'topic', (int, 'last_message_id')
        ]

        # We update instead of filling initially becaue of voice channels
        # that don't have topic or last_message_id
        self.fill(raw_channel)

        self.guild = client.state.get_guild(raw_channel['guild_id'])

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'TextChannel<id={self.id} name={self.name}>'


class VoiceChannel(Identifiable):
    """A text channel."""
    def __init__(self, client, raw_channel):
        super().__init__(client, raw_channel)

        self._fields = [
            (int, 'guild_id'), 'name', 'type', 'position'
        ]

        self.fill(raw_channel)

        self.guild = client.state.get_guild(raw_channel['guild_id'])

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'VoiceChannel<id={self.id} name={self.name}>'


class User(Identifiable):
    def __init__(self, client, raw_user):
        super().__init__(client, raw_user)

        self._fields = ['username', 'discriminator', 'avatar', 'bot']

        self.update(raw_user)

    def __str__(self):
        return f'{self.username}#{self.discriminator}'

    def __repr__(self):
        return f'User<username={self.username} discriminator={self.discriminator}>'


class ClientUser(Identifiable):
    def __init__(self, client, raw_client_user):
        super().__init__(client, raw_client_user)

        self._fields = ['username', 'discriminator', 'avatar', 'bot']

        self.fill(raw_client_user)

    def __repr__(self):
        return f'ClientUser<username={self.username} discriminator={self.discriminator}>'


class Member(Identifiable):
    """General member object."""
    def __init__(self, client, raw_member):
        super().__init__(client, raw_member)

        self._fields = ['nick', 'joined_at']

        self.fill(raw_member)


class Message(Identifiable):
    """General message object.

    Attributes
    ----------
    id: int
        Message ID.
    channel_id: str
        Channel ID of the message.
    channel: :class:`Channel`
        Channel that the message came from.
    author: :class:`User`
        Author of the message.
    content: str
        Message content.
    timestamp: meme
        TODO: timestamp function
    tts: bool
        If the message was a TTS message.
    mention_everyone: bool
        If the message mentioned everyone.
    mensions: list[:class:`User`]
        Users that were mentioned in the message.
    pinned: bool
        If the message is pinned.
    """
    def __init__(self, client, raw_message):
        super().__init__(client, raw_message)

        self._fields = ['channel_id', (client.state.get_channel, 'channel_id', 'channel'), 
            (client.state.get_user, 'author'), 'content', (_timestamp, 'timestamp'),
            'tts', 'mention_everyone', (listof(client.state.get_user), 'mentions'),
            'pinned']

        self.fill(raw_message)
    
    def __repr__(self):
        return f'Message<author={self.author}>'

    async def reply(self, content):
        content = str(content)

        raw_msg = await self.client.http.post(
            f'/channels/{self.channel_id}/messages',
            {'content': content}
        )

        return Message(self.client, raw_msg)

    async def edit(self, content: str):
        raw_msg = await self.client.http.patch(
            f'/channels/{self.channel_id}/messages/{self.id}',
            {'content': content}
        )

        self = Message(self.client, raw_msg)
