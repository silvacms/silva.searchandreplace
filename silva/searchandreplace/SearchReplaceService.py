import re

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zope.interface import implements

from Products.Silva.helpers import add_and_edit
from Products.Silva.interfaces import IContainer, IContent, IVersionedContent

from ZTUtils import Batch

class FindRootError(Exception):
    """ raised on invalid traversal to the root
    """

class ServiceSearchReplace(SimpleItem):
    security = ClassSecurityInfo()
    #implements(IServicePolls)
    meta_type = 'Silva Search and Replace Service'

    manage_options = (
        {'label': 'Edit', 'action':'manage_editForm'},
        ) + SimpleItem.manage_options

    security.declareProtected('View management screens', 'manage_editForm')
    manage_editForm = PageTemplateFile(
        'www/serviceSearchReplaceEdit', globals(),
        __name__='manage_editForm')

    security.declareProtected('View management screens', 'manage_main')
    manage_main = manage_editForm

    def __init__(self, id, title):
        self.id = id
        self.title = title

    security.declareProtected(
        'View management screens', 'manage_performSearch')
    def manage_performSearch(self, REQUEST):
        """ zope sux 
        """
        query = REQUEST['query']
        search_targets = REQUEST.get('search_targets')
        if not query or not search_targets:
            return self.manage_main(
                manage_tabs_message='Please fill in the required fields')
        ignore_case = not not REQUEST.get('ignore_case')
        batch_size = int(REQUEST.get('batch_size', 200))
        try:
            processed, occurrences, results = self.search_results(
                query, REQUEST.get('root') or None, ignore_case,
                search_targets)
        except FindRootError:
            return self.manage_main(
                manage_tabs_message='Invalid search root')
        REQUEST.SESSION['search_replace_data'] = {
            'query': query,
            'ignore_case': ignore_case,
            'batch_size': batch_size,
            'search_targets': search_targets,
            'results': results,
            'processed': processed,
            'occurrences': occurrences,
            'paths': [result['path'] for result in results],
        }
        batch = Batch(results, batch_size)
        return self.manage_main(
            search_performed=True, processed=processed,
            occurrences=occurrences, results=results, batch=batch)

    security.declareProtected(
        'View management screens', 'manage_performSearchBatch')
    def manage_performSearchBatch(self, REQUEST):
        """ zope sux
        """
        sessdata = REQUEST.SESSION['search_replace_data']
        batch = Batch(
            sessdata['results'], sessdata['batch_size'],
            start=int(REQUEST.get('batch_start', 0)))
        return self.manage_main(
            search_performed=True, processed=sessdata['processed'],
            occurrences=sessdata['occurrences'], results=sessdata['results'],
            batch=batch)

    security.declareProtected(
        'View management screens', 'manage_performReplaceSelected')
    def manage_performReplaceSelected(self, REQUEST):
        """ zope sux 
        """
        paths = REQUEST.get('paths', [])
        sessdata = REQUEST.SESSION['search_replace_data']
        occurrences = self.replace_paths(
            paths, sessdata['query'], REQUEST.get('replacement', ''),
            sessdata['ignore_case'], sessdata['search_targets'])
        return self.manage_main(
            manage_tabs_message='Replaced %s occurrences' % (occurrences,))

    security.declareProtected(
        'View management screens', 'manage_performReplaceAll')
    def manage_performReplaceAll(self, REQUEST):
        """ zope sux 
        """
        sessdata = REQUEST.SESSION['search_replace_data']
        occurrences = self.replace_paths(
            sessdata['paths'], sessdata['query'], REQUEST['replacement'],
            sessdata['ignore_case'], sessdata['search_targets'])
        return self.manage_main(
            manage_tabs_message='Replaced %s occurrences' % (occurrences,))

    def search_results(
            self, query, root=None, ignore_case=False,
            search_targets=None):
        """ return search results for 'query'

            this is the first in a two-step process of searching for a string
            and replacing all, or some, of the occurrences
        """
        # perform the search globally, retrieve the paths of matching objects
        # store all found paths in the session in case 'replace all' is
        # clicked, and create a batch form for the paths as well to allow
        # replacing in a selected set of items (note that we keep it relatively
        # simple - either everything or the currently displayed batch is
        # processed, we don't allow selecting items in different pages)
        if root is None:
            root = self.get_root()
        else:
            orgvalue = root
            path = root.split('/')
            if path[0] == '':
                try:
                    root = self.restrictedTraverse(path)
                except (KeyError, AttributeError):
                    raise FindRootError(orgvalue)
            else:
                root = self.get_root()
                while path:
                    try:
                        root = getattr(root, path.pop())
                    except AttributeError:
                        raise FindRootError(orgvalue)
        return self._perform_search(
            query, root, ignore_case, search_targets)

    def replace_paths(
            self, paths, query, replacement, ignore_case=False,
            search_targets=None):
        occurrences = 0
        for path in paths:
            occurrences += self._perform_replace(
                path, query, replacement, ignore_case, search_targets)
        return occurrences
            
    def _perform_replace(
            self, path, query, replacement, ignore_case, search_targets):
        obj = self.restrictedTraverse(path.split('/'))
        return self._count_or_replace(
            obj.content, query, replacement, ignore_case, search_targets)

    def _perform_search(self, query, root, ignore_case, search_targets):
        """ walk through (part of) the site in search of query matches

            returns a list of dicts with keys 'path', 'occurrences',
            'title' and 'state'
        """
        ret = []
        buffer = [root]
        processed = 0
        occurrences = 0
        while buffer:
            current = buffer.pop(0) # XXX or do we want depth first?
            if IContainer.providedBy(current):
                buffer += current.objectValues()
            elif IContent.providedBy(current):
                content_objects = self._get_content_objects(current)
                processed += len(content_objects)
                for state, url, obj in content_objects:
                    content = self._get_silvaxml_content(obj)
                    if content is None:
                        continue
                    num = self._count_or_replace(
                        content, query, None, ignore_case, search_targets)
                    occurrences += num
                    if num > 0:
                        ret.append({
                            'url': url,
                            'path': '/'.join(obj.getPhysicalPath()),
                            'title': obj.get_title(),
                            'occurrences': num,
                            'state': state,
                        })
        return processed, occurrences, ret

    def _get_content_objects(self, object):
        objs = []
        if IVersionedContent.providedBy(object):
            editable = object.get_editable()
            if editable is not None:
                objs.append(
                    ('editable', editable.aq_parent.absolute_url(), editable))
            public_id = object.get_public_version()
            if public_id is not None:
                version = getattr(object, public_id)
                objs.append(
                    ('public', version.aq_parent.absolute_url(), version))
        else:
            objs = [('non-versioned', object.absolute_url(), object)]
        return objs

    def _get_silvaxml_content(self, object):
        content = getattr(object, 'content', None)
        # XXX a bit scary: Silva XML doesn't have a proper namespace we can
        # check for, so we assume that if the document element is called 'doc'
        # we have matching XML... :|
        if (content is not None and content.meta_type == 'Parsed XML' and
                content.documentElement.nodeName == 'doc'):
            return content

    _reg_absurls = re.compile(r'^(http|https)://.*')
    _reg_urls = re.compile(r'.*:.*')
    def _count_or_replace(
            self, content, query, replacement, ignore_case, search_targets):
        """ counts and (optionally) replaces occurrences of query in content

            this finds occurrences of query in content, ignoring case if
            'ignore_case' is true, and in parts of content as determined by
            'search_targets', and returns the amount of occurrences found,
            optionally after replacing them with 'replacement', though if
            that is set to None, it doesn't replace anything
        """
        occurrences = 0
        flags = re.U
        if ignore_case:
            flags = flags | re.I
        if not isinstance(query, unicode):
            query = unicode(query, 'utf-8')
        if replacement and not isinstance(replacement, unicode):
            replacement = unicode(replacement, 'utf-8')
        reg = re.compile(re.escape(query), flags)
        # find all text nodes and text attributes
        current = content.documentElement
        replaced = False
        while current:
            if 'text' in search_targets:
                if current.nodeType == 3:
                    # text node
                    toscan = current.nodeValue
                    num = len(reg.findall(toscan))
                    occurrences += num
                    if num and replacement is not None:
                        toscan = reg.sub(replacement, toscan)
                        current.nodeValue = toscan
                        replaced = True
                elif current.nodeName in (
                        'image', 'link', 'index', 'abbr', 'acronym'):
                    attrs = ('title',)
                    for attr in attrs:
                        toscan = current.getAttribute(attr)
                        if toscan:
                            num = len(reg.findall(toscan))
                            occurrences += num
                            if num and replacement is not None:
                                current.setAttribute(
                                    attr, reg.sub(replacement, toscan))
                                replaced = True
            if 'paths' in search_targets or 'urls' in search_targets:
                for name, attr in (
                        ('image', 'link'),
                        ('image', 'path'),
                        ('link', 'url')):
                    if current.nodeName == name:
                        toscan = current.getAttribute(attr)
                        if (toscan and
                                ('paths' in search_targets and not
                                 self._reg_urls.match(toscan)) or
                                ('urls' in search_targets and
                                 self._reg_absurls.match(toscan))):
                            num = len(reg.findall(toscan))
                            occurrences += num
                            if num and replacement is not None:
                                current.setAttribute(
                                    attr, reg.sub(replacement, toscan))
                                replaced = True
            if current.childNodes.length:
                current = current.firstChild
            elif current.nextSibling:
                current = current.nextSibling
            else:
                while current.parentNode:
                    current = current.parentNode
                    if current.nextSibling:
                        current = current.nextSibling
                        break
                else:
                    current = None
        if replaced:
            content._p_changed = True
            # XXX I assume this should always be done?
            if hasattr(content.aq_base, 'reindex_object'):
                content.reindex_object()
        return occurrences


InitializeClass(ServiceSearchReplace)

manage_addServiceSearchReplaceForm = PageTemplateFile(
    'www/serviceSearchReplaceAdd', globals(),
    __name__='manage_addServiceSearchReplaceForm')

def manage_addServiceSearchReplace(
        self, id='service_search_replace', title='', REQUEST=None):
    """add service to the ZODB"""
    id = self._setObject(id, ServiceSearchReplace(id, unicode(title, 'UTF-8')))
    service = getattr(self, id)
    add_and_edit(self, id, REQUEST)
    return ''
