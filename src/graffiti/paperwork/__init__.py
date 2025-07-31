import logging

from zope.i18nmessageid import MessageFactory

_ = MessageFactory("graffiti.paperwork")
logger = logging.getLogger("graffiti.paperwork")


# noinspection PyUnusedLocal
def initialize(context):
    """Initializer called when used as a Zope 2 product."""
