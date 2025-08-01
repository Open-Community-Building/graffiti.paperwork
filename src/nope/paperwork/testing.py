from nope.testing.testing import NopeTestingLayer

from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.testing.zope import WSGI_SERVER_FIXTURE


class NopePaperWorkLayer(NopeTestingLayer):
    additional_products_to_import = []
    additional_products_to_install = ["nope.paperwork"]


NOPE_PAPERWORK_FIXTURE = NopePaperWorkLayer()
NOPE_PAPERWORK_INTEGRATION_TESTING = IntegrationTesting(
    bases=(NOPE_PAPERWORK_FIXTURE,), name="NopePaperWorkLayer:Integration"
)
NOPE_PAPERWORK_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(NOPE_PAPERWORK_FIXTURE, WSGI_SERVER_FIXTURE),
    name="NopePaperWorkLayer:Functional",
)
