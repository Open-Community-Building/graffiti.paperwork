from graffiti.testing.testing import GraffitiTestingLayer

from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.testing.zope import WSGI_SERVER_FIXTURE


class GraffitiPaperWorkLayer(GraffitiTestingLayer):
    additional_products_to_import = []
    additional_products_to_install = ["graffiti.paperwork"]


GRAFFITI_PAPERWORK_FIXTURE = GraffitiPaperWorkLayer()
GRAFFITI_PAPERWORK_INTEGRATION_TESTING = IntegrationTesting(
    bases=(GRAFFITI_PAPERWORK_FIXTURE,), name="GraffitiPaperWorkLayer:Integration"
)
GRAFFITI_PAPERWORK_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(GRAFFITI_PAPERWORK_FIXTURE, WSGI_SERVER_FIXTURE),
    name="GraffitiPaperWorkLayer:Functional",
)
