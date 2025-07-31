from plone.dexterity.content import Container
from plone.supermodel import model
from zope.interface import implementer


class IGraffitiPaperWorkContainer(model.Schema):
    """Schema for GraffitiPaperWork content type"""
    pass

@implementer(IGraffitiPaperWork)
class GraffitiPaperWork(Container):
    """GraffitiPaperWork content type for storing files"""
    pass
