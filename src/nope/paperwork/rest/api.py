"""
The nope.paperwork tool provides a service to create storage spaces via REST API.
"""

from typing import Dict

from Products.Five.browser import BrowserView
from interaktiv.framework.api.api import json_api_call
from plone.restapi.interfaces import IJsonCompatible
from zope.publisher.interfaces import IPublishTraverse
from zope.interface import implementer
from plone.restapi.deserializer import json_body
from zExceptions import BadRequest
from plone.dexterity.utils import createContentInContainer
from interaktiv.framework import sudo
from plone.app.uuid.utils import uuidToObject
from Products.CMFCore.utils import getToolByName
from interaktiv.workingcopy.utilities.workingcopy import get_working_copy
import interaktiv.framework as framework
import plone.api as api
from Products.Five.browser import BrowserView
from interaktiv.workingcopy.events.after_checkout import AfterCheckoutEvent
from plone.app.iterate.dexterity import ITERATE_RELATION_NAME
from plone.app.iterate.interfaces import IObjectCopier
from plone.locking.interfaces import STEALABLE_LOCK
from zope import component
from zope.event import notify
from interaktiv.workingcopy.utilities.workingcopy import get_workflow_id
import base64
import transaction
import Levenshtein


@implementer(IPublishTraverse)
class PaperWorkApi(BrowserView):
    """
    Provides a service to create storage spaces for paper work via REST API.
    """

    def publishTraverse(self, request, name):
        """
        Routing of the url to the right methods.
        """
        if len(self.params) == 0:
            if name != "paperwork":
                raise BadRequest("API calls must start with /paperwork")
            portal = api.portal.get()
            if name not in portal.objectIds():
                raise BadRequest("Folder /paperwork does not exist")
            self.paperwork_container_id = name
        elif len(self.params) == 1:
            portal = api.portal.get()
            if not portal["paperwork"][name].portal_type == "NopePaperWork":
                raise BadRequest(
                    "No NopePaperWork content type with id %s in Folder /paperwork"
                    % name
                )
            self.paperwork_uid = name
        elif name == "transition":
            self.params.append(name)
        elif name == "publish":
            self.params.append(name)
        elif name == "metadata":
            self.params.append(name)
        elif name == "files":
            self.params.append(name)
        elif name == "file":
            self.params.append(name)
        elif name == "existing":
            self.params.append(name)
        elif name == "similar":
            self.params.append(name)
        elif name.isnumeric():
            self.file_number = name
        else:
            self.paperwork_uid = name
            portal = api.portal.get()
            with sudo.role_context("Manager", portal):
                obj = uuidToObject(self.paperwork_uid)
                if "/copy_of_" in obj.absolute_url():
                    raise BadRequest(
                        "This UUID is from a working copy, but the UUID of the working copy is needed."
                    )
            self.params.append(name)
        return self

    def __init__(self, context, request):
        """Once we get to __call__, the path is lost,
        so we capture it here on initialization.
        """
        self.params = []
        self.paperwork_container_id = None
        self.paperwork_uid = None
        self.file_number = None
        super(PaperWorkApi, self).__init__(context, request)

    @json_api_call
    def __call__(self, *kw, **kwargs) -> Dict:
        """
        GET /@@paperwork/aiconferenceheidelberg/31a402a1499ea33dc0278351f64b89aa
        POST /@@paperwork/aiconferenceheidelberg
        POST /@@paperwork/aiconferenceheidelberg/31a402a1499ea33dc0278351f64b89aa
        POST /@@paperwork/aiconferenceheidelberg/31a402a1499ea33dc0278351f64b89aa
        GET /@@paperwork/aiconferenceheidelberg/file/1/31a402a1499ea33dc0278351f64b89aa
        POST /@@paperwork/aiconferenceheidelberg/31a402a1499ea33dc0278351f64b89aa/transition/publish
        GET /@@paperwork/aiconferenceheidelberg/existing
        GET /@@paperwork/aiconferenceheidelberg/similar
        """
        response = None
        if self.request.method == "GET":
            if "file" in self.params:
                response = self.get_paperwork_file()
            elif "existing" in self.params:
                response = self.existing()
            elif "similar" in self.params:
                response = self.similar()
            else:
                response = self.get_paperwork()
        elif self.request.method == "POST":
            if not self.paperwork_uid:
                response = self.add_paperwork()
            else:
                if "files" in self.params:
                    response = self.set_paperwork_files()
                elif "metadata" in self.params:
                    response = self.set_paperwork_metadata()
                elif "transition" in self.params:
                    response = self.publish_paperwork()
        self.request.response.setHeader("Content-type", "application/json")
        return response

    def get_paperwork(self):
        """
        Get paperwork content by UID

        GET /@@paperwork/aiconferenceheidelberg/31a402a1499ea33dc0278351f64b89aa
        """
        if not self.paperwork_uid:
            raise BadRequest("No uuid found in path")

        portal = api.portal.get()

        with sudo.role_context("Manager", portal):
            obj = uuidToObject(self.paperwork_uid)
            if obj is None:
                raise BadRequest("JSON payload contains unidentifiable uuid")
            wftool = getToolByName(self.context, "portal_workflow")
            return IJsonCompatible(
                {
                    "uuid": self.paperwork_uid,
                    "url": obj.absolute_url(),
                    "title": obj.Title(),
                    "workflow_state": wftool.getInfoFor(
                        ob=obj, name="review_state", default=None
                    ),
                    "has_working_copy": bool(get_working_copy(obj)),
                }
            )

    def add_paperwork(self):
        """
        Add paperwork content

        POST /@@paperwork/aiconferenceheidelberg
        """
        data = json_body(self.request)
        if len(data) != 3:
            raise BadRequest(
                "JSON payload needs to contain exactly three keys: title and author"
            )
        if "title" not in data:
            raise BadRequest("JSON payload needs to contain a title")
        if "author" not in data:
            raise BadRequest("JSON payload needs to contain an author")

        uuid = framework.helper.generate_uuid()

        portal_type = "NopePaperWork"
        portal = api.portal.get()

        with sudo.role_context("Manager", portal):
            docbook = createContentInContainer(
                portal["paperwork"][self.paperwork_container_id],
                portal_type,
                id=uuid,
                title=data["title"],
                document_type="NopePaperWork",
            )
            transaction.commit()

        return IJsonCompatible({"uuid": docbook.UID(), "url": docbook.absolute_url()})

    def set_paperwork_metadata(self):
        """
        Change meta data.

        POST /@@paperwork/aiconferenceheidelberg/metadata/a6e701e06fff42928cb2515db89e0b7c
        """
        if not self.paperwork_uid:
            raise BadRequest("No uuid found in path")

        data = json_body(self.request)
        if len(data) != 3:
            raise BadRequest(
                "JSON payload needs to contain exactly three keys: title and author"
            )
        if "title" not in data:
            raise BadRequest("JSON payload needs to contain a title")
        if "author" not in data:
            raise BadRequest("JSON payload needs to contain an author")

        portal = api.portal.get()

        with sudo.role_context("Manager", portal):

            obj = uuidToObject(self.paperwork_uid)
            if obj is None:
                raise BadRequest("JSON payload contains unidentifiable uuid")

            working_copy = get_working_copy(obj)
            if bool(working_copy):
                obj = working_copy
                if obj is None:
                    raise BadRequest("Could not get working copy.")
            else:
                wftool = getToolByName(self.context, "portal_workflow")
                review_state = wftool.getInfoFor(
                    ob=obj, name="review_state", default=None
                )
                if review_state == "archived":
                    raise BadRequest("Working paper is archived. Can not edit!")
                elif review_state == "draft":
                    pass  # Just edit
                elif review_state == "published":
                    obj = self._checkout(
                        original=obj,
                        container=portal["paperwork"][self.paperwork_container_id],
                    )
                    if obj is None:
                        raise BadRequest("Adding a working copy failed.")
                elif review_state == "review":
                    raise BadRequest(
                        "Working paper is in review state 'review'. Can not edit!"
                    )

            if obj.Creator() != data["author"]:
                obj.setCreators(data["author"])

            if obj.title != data["title"]:
                obj.title = data["title"]

            if obj.org_consultant != data["author"]:
                obj.org_consultant = data["author"]

            obj.reindexObject()

            original = uuidToObject(self.paperwork_uid)
            url = original.absolute_url()
            original.reindexObject()

            transaction.commit()

            result = {"uuid": self.paperwork_uid, "url": url}

        return IJsonCompatible(result)

    def _checkout(self, original, container):
        version_notice = "Create working copy"
        # copy original recursively and set relation
        copier = component.queryAdapter(original, IObjectCopier)
        working_copy, relation = copier.copyTo(container)
        setattr(original, ITERATE_RELATION_NAME, relation)
        original.reindexObject("review_state")
        framework.locking.lock(context=original, lock_type=STEALABLE_LOCK)
        # set version notice
        working_copy.working_copy_version_notice = version_notice

        # set local_roles
        local_role_map = {}
        for entry in original.get_local_roles():
            if entry[0] in local_role_map:
                local_role_map[entry[0]].extend(list(entry[1]))
            else:
                local_role_map[entry[0]] = list(entry[1])
        for user_id in local_role_map:
            working_copy.manage_setLocalRoles(user_id, local_role_map[user_id])

        # fire event
        notify(AfterCheckoutEvent(original, working_copy, relation))
        return working_copy

    def _checkin_document(self, workingcopy):
        workingcopy.REQUEST.form["form.button.Checkin"] = ""
        workingcopy.REQUEST.form["checkin_message"] = (
            "Arbeitskopie mit Original ausgetauscht."
        )
        view = api.content.get_view(
            name="arbeitskopie-mit-original-austauschen",
            context=workingcopy,
            request=workingcopy.REQUEST,
        )
        workflow_id = get_workflow_id(workingcopy)
        view.original_workflow_id = workflow_id
        view.workingcopy_workflow_name = workflow_id
        # noinspection PyProtectedMember
        merged_original = view._checkin(workingcopy=workingcopy)
        return merged_original

    def set_paperwork_files(self):
        """
        Change files on the content

        POST /@paperwork/aiconferenceheidelberg/files/a6e701e06fff42928cb2515db89e0b7c
        """
        if not self.paperwork_uid:
            raise BadRequest("No uuid found in path")

        portal = api.portal.get()

        with sudo.role_context("Manager", portal):

            obj = uuidToObject(self.paperwork_uid)

            if obj is None:
                raise BadRequest("JSON payload contains unidentifiable uuid")

            working_copy = get_working_copy(obj)
            if bool(working_copy):
                obj = working_copy
                if obj is None:
                    raise BadRequest("Could not get working copy.")
            else:
                wftool = getToolByName(self.context, "portal_workflow")
                review_state = wftool.getInfoFor(
                    ob=obj, name="review_state", default=None
                )
                if review_state == "archived":
                    raise BadRequest("Working paper is archived. Can change files!")
                elif review_state == "draft":
                    pass  # Just edit
                elif review_state == "published":
                    obj = self._checkout(
                        original=obj,
                        container=portal["paperwork"][self.paperwork_container_id],
                    )
                    if obj is None:
                        raise BadRequest("Adding a working copy failed.")
                elif review_state == "review":
                    raise BadRequest(
                        "Working paper is in review state 'review'. Can not change files!"
                    )

            index = 1
            while hasattr(self.context, "file%s" % index):
                try:
                    delattr(self.context, "file%s" % index)
                except:
                    pass
                try:
                    delattr(self.context, "file%sname" % index)
                except:
                    pass
                try:
                    delattr(self.context, "file%scontent_type" % index)
                except:
                    pass
                index = index + 1

            index = 0
            for _, file_upload in self.request.form.items():
                index = index + 1
                setattr(self.context, "file" + str(index), file_upload.read())
                setattr(
                    self.context, "file" + str(index) + "name", file_upload.filename
                )
                setattr(
                    self.context,
                    "file" + str(index) + "content_type",
                    file_upload.headers["Content-Type"],
                )

            transaction.commit()

        return IJsonCompatible(
            {
                "uuid": self.paperwork_uid,
                "url": obj.absolute_url(),
                "title": obj.Title(),
            }
        )

    def get_paperwork_file(self):
        """
        Get file on the content

        GET /@@paperwork/aiconferenceheidelberg/file/1/a6e701e06fff42928cb2515db89e0b7c
        """
        if not self.paperwork_uid:
            raise BadRequest("No uuid found in path")

        portal = api.portal.get()

        with sudo.role_context("Manager", portal):

            obj = uuidToObject(self.paperwork_uid)

            if obj is None:
                raise BadRequest("JSON payload contains unidentifiable uuid")

            working_copy = get_working_copy(obj)
            if bool(working_copy):
                obj = working_copy
                if obj is None:
                    raise BadRequest("Could not get working copy.")
            else:
                wftool = getToolByName(self.context, "portal_workflow")
                review_state = wftool.getInfoFor(
                    ob=obj, name="review_state", default=None
                )

            if review_state == "archived":
                raise BadRequest("Working paper is archived. Can change files!")
            elif review_state == "draft":
                pass  # Just edit
            elif review_state == "published":
                obj = self._checkout(
                    original=obj,
                    container=portal["paperwork"][self.paperwork_container_id],
                )
                if obj is None:
                    raise BadRequest("Adding a working copy failed.")
            elif review_state == "review":
                raise BadRequest(
                    "Working paper is in review state 'review'. Can not change files!"
                )

            return IJsonCompatible(
                {
                    "file_number": str(self.file_number),
                    "file_name": getattr(obj, "file" + str(self.file_number) + "name"),
                    "file_content": base64.b64encode(
                        getattr(obj, "file" + str(self.file_number))
                    ),
                    "file_content_type": getattr(
                        obj, "file" + str(self.file_number) + "content_type"
                    ),
                }
            )

    def publish_paperwork(self):
        """
        Publish the content

        POST /@@paperwork/aiconferenceheidelberg/a6e701e06fff42928cb2515db89e0b7c/transition/publish
        """
        if not self.paperwork_uid:
            raise BadRequest("No uuid found in path")

        portal = api.portal.get()

        with sudo.role_context("Manager", portal):

            obj = uuidToObject(self.paperwork_uid)

            if obj is None:
                raise BadRequest("JSON payload contains unidentifiable uuid")

            wftool = getToolByName(self.context, "portal_workflow")

            review_state = wftool.getInfoFor(ob=obj, name="review_state", default=None)

            transitions = wftool.getTransitionsFor(obj)
            transition_ids = [transition["id"] for transition in transitions]

            if review_state == "review":
                if "publish_without_voting" in transition_ids:
                    wftool.doActionFor(obj, action="publish_without_voting")
                else:
                    raise BadRequest(
                        "Working copy in state 'review' can not be published"
                    )
            elif review_state == "draft":
                if "submit" in transition_ids:
                    wftool.doActionFor(obj, action="submit")
                else:
                    raise BadRequest(
                        "Working paper in state 'draft' can not be submitted."
                    )
                transitions = wftool.getTransitionsFor(obj)
                transition_ids = [transition["id"] for transition in transitions]
                if "publish_without_voting" in transition_ids:
                    wftool.doActionFor(obj, action="publish_without_voting")
                else:
                    raise BadRequest(
                        "Working paper in state 'review' can not be published."
                    )
            elif review_state == "published":
                working_copy = get_working_copy(obj)
                if bool(working_copy):
                    self._checkin_document(working_copy)
                else:
                    raise BadRequest(
                        "The working paper is already published, and there is no working copy."
                    )

            elif review_state == "archived":
                raise BadRequest(
                    "The working paper is archived an publishing it though the API is not supported"
                )

            new_review_state = framework.workflow.get_review_state(obj)

            if new_review_state != "published":
                raise BadRequest(
                    "The working paper could not be published. It is in review state '%s'"
                    % new_review_state
                )

            transaction.commit()

            return IJsonCompatible(
                {
                    "uuid": self.paperwork_uid,
                    "url": obj.absolute_url(),
                    "title": obj.Title(),
                    "workflow_state": new_review_state,
                    "has_working_copy": bool(get_working_copy(obj)),
                }
            )

    def existing(self):
        """
        Top matches of existing working papers by title

        GET /@@paperwork/aiconferenceheidelberg/existing
        """
        data = json_body(self.request)
        if len(data) != 1:
            raise BadRequest("JSON payload needs to contain exactly one key: title")
        if "title" not in data:
            raise BadRequest("JSON payload needs to contain a title")
        brains = []
        for brain in self.catalog.searchResults({"document_type": "NopePaperWork"}):
            if data["title"] == brain.Title:
                brains.append(brain)
        wftool = getToolByName(self.context, "portal_workflow")
        results = []
        for brain in brains:
            obj = brain.getObject()
            doc = {
                "uuid": obj.UID(),
                "url": obj.absolute_url(),
                "title": obj.Title(),
                "workflow_state": wftool.getInfoFor(
                    ob=obj, name="review_state", default=None
                ),
                "has_working_copy": bool(get_working_copy(obj)),
            }
            results.append(doc)

        return IJsonCompatible(results)

    def similar(self):
        """
        Top matches of existing paperwork by title

            POST /paperwork/aiconferenceheidelberg/similar
        """
        data = json_body(self.request)
        if len(data) != 1:
            raise BadRequest("JSON payload needs to contain exactly one key: title")
        if "title" not in data:
            raise BadRequest("JSON payload needs to contain a title")

        matches = []
        for brain in self.catalog.searchResults({"document_type": "NopePaperWork"}):
            jaro_winkler = Levenshtein.jaro_winkler(data["title"], brain.Title)
            matches.append((jaro_winkler, brain))
        matches.sort(reverse=True)

        wftool = getToolByName(self.context, "portal_workflow")

        results = []
        for jaro_winkler, brain in matches:
            obj = brain.getObject()
            doc = {
                "uuid": obj.UID(),
                "url": obj.absolute_url(),
                "title": obj.Title(),
                "workflow_state": wftool.getInfoFor(
                    ob=obj, name="review_state", default=None
                ),
                "has_working_copy": bool(get_working_copy(obj)),
                "similarity": jaro_winkler,
            }
            results.append(doc)

        return IJsonCompatible(results)
