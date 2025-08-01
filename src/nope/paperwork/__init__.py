import logging

from zope.i18nmessageid import MessageFactory

_ = MessageFactory("nope.paperwork")
logger = logging.getLogger("nope.paperwork")


# noinspection PyUnusedLocal
def initialize(context):
    """Initializer called when used as a Zope 2 product."""
