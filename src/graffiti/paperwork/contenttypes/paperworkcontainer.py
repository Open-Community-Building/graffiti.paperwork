from plone.dexterity.content import Container
from plone.supermodel import model
from zope.interface import implementer


class INopePaperWorkContainer(model.Schema):
    """Schema for NopePaperWork content type"""

    pass


@implementer(INopePaperWork)
class NopePaperWork(Container):
    """NopePaperWork content type for storing files"""

    pass
