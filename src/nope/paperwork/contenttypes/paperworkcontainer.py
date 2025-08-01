from plone.dexterity.content import Container
from plone.supermodel import model
from zope.interface import implementer


class INopePaperWorkContainer(model.Schema):
    """Schema for NopePaperWorkContainer content type"""

    pass


@implementer(INopePaperWorkContainer)
class NopePaperWorkContainer(Container):
    """NopePaperWorkContainer content type for storing files"""

    pass
