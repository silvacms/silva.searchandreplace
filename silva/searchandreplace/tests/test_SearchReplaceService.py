# -*- coding: utf-8 -*-
# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from lxml import etree
from xml.dom.minidom import parseString
import StringIO
import unittest

from Products.Five import zcml
from Products.Silva.tests import SilvaTestCase
from Testing.ZopeTestCase.layer import onsetup as ZopeLiteLayerSetup
from Testing.ZopeTestCase import installPackage


class ServiceSearchReplaceTestCase(SilvaTestCase.SilvaTestCase):

    def afterSetUp(self):
        factory = self.root.manage_addProduct['silva.searchandreplace']
        factory.manage_addServiceSearchReplace('service_search_replace')
        self.service = getattr(self.root, 'service_search_replace')

        for id, title, content in (
                ('foo', 'Foo',
                 '<doc><p type="normal">foo, bar and baz!</p></doc>'),
                ('spam', 'Spam',
                 '<doc><p type="normal">spam and eggs</p></doc>'),
                ('spam_eggs', 'Spam and eggs',
                 '<doc><p type="normal">Spam and eggs</p></doc>')):
            doc = self.addObject(
                self.root, 'Document', id, 'SilvaDocument', title=title)
            doc.get_editable().content.manage_edit(content)

    def test_setup(self):
        self.assert_(self.service)

    def assertOccurrenceMatches(
            self, xml, query, ignore_case, targets, expected):
        dom = parseString(xml)
        self.assertEquals(self.service._count_or_replace(
            dom, query, None, ignore_case, targets), expected)

    def assertOccurrenceReplaced(
            self, xml, query, replacement, ignore_case, targets,
            expected_occurrences, expected_result):
        dom = parseString(xml)
        occurrences = self.service._count_or_replace(
            dom, query, replacement, ignore_case, targets)
        self.assertEquals(occurrences, expected_occurrences)
        self.assertEquals(
            self._normalize_xml(dom.documentElement.toxml()),
            self._normalize_xml(expected_result))

    def _normalize_xml(self, xml):
        if isinstance(xml, unicode):
            xml = xml.encode('utf-8')
        s = StringIO.StringIO()
        tree = etree.fromstring(xml)
        tree.getroottree().write_c14n(s)
        return s.getvalue()

    def test__perform_search_no_results(self):
        results = self.service._perform_search(
            'thisisnotinthetext', self.getRoot(), False, ['text'])[-1]
        self.assertEquals(len(results), 0)

    def test__perform_search_case_sensitive(self):
        results = self.service._perform_search(
            'spam', self.getRoot(), False, ['text'])[-1]
        self.assertEquals(len(results), 1)

    def test__count_occurrences_text_single(self):
        self.assertOccurrenceMatches(
            '<doc>foo</doc>', 'foo', False, ['text'], 1)

    def test__count_occurrences_text_single_nested(self):
        self.assertOccurrenceMatches(
            '<doc><p>foo</p></doc>', 'foo', False, ['text'], 1)

    def test__count_occurrences_text_double_two_nodes(self):
        self.assertOccurrenceMatches(
            '<doc><p>foo</p><p>foo</p></doc>', 'foo', False, ['text'], 2)

    def test__count_occurrences_text_double_one_node(self):
        self.assertOccurrenceMatches(
            '<doc><p>foo foo</p></doc>', 'foo', False, ['text'], 2)

    def test__count_occurrences_text_no_ignore_case(self):
        self.assertOccurrenceMatches(
            '<doc><p>Foo foo fOO</p></doc>', 'foo', False, ['text'], 1)

    def test__count_occurrences_text_ignore_case(self):
        self.assertOccurrenceMatches(
            '<doc><p>Foo foo fOO</p></doc>', 'foo', True, ['text'], 3)

    def test__count_occurrences_text_ignore_case_upper_query(self):
        self.assertOccurrenceMatches(
            '<doc><p>Foo foo fOO</p></doc>', 'FOO', True, ['text'], 3)

    def test__count_occurrences_text_ignore_attributes(self):
        self.assertOccurrenceMatches(
            '<doc><p name="foo">foo</p></doc>', 'foo', False, ['text'], 1)

    def test__count_occurrences_text_deeply_nested(self):
        self.assertOccurrenceMatches(
            '<doc><p><strong>foo</strong></p></doc>', 'foo', False,
            ['text'], 1)

    def test__count_occurrences_text_parent_up(self):
        self.assertOccurrenceMatches(
            '<doc><p><strong>foo</strong></p>foo</doc>', 'foo', False,
            ['text'], 2)

    def test__count_occurrences_text_in_title(self):
        self.assertOccurrenceMatches(
            '<doc><image title="spam foo bar" /></doc>', 'foo', False,
            ['text'], 1)

    def test__count_or_replace_text_basic(self):
        self.assertOccurrenceReplaced(
            '<doc><p>foo</p></doc>', 'foo', 'bar', False,
            ['text'], 1, '<doc><p>bar</p></doc>')

    def test__count_or_replace_text_two_strings(self):
        self.assertOccurrenceReplaced(
            '<doc><p>foo bar foo</p></doc>', 'foo', 'spam', False,
            ['text'], 2, '<doc><p>spam bar spam</p></doc>')

    def test__count_or_replace_text_multiple_nodes(self):
        self.assertOccurrenceReplaced(
            '<doc><p>foo</p><p>foo</p></doc>', 'foo', 'bar', False,
            ['text'], 2, '<doc><p>bar</p><p>bar</p></doc>')

    def test__count_or_replace_text_case_sensitive(self):
        self.assertOccurrenceReplaced(
            '<doc><p>foo Foo fOO</p></doc>', 'foo', 'bar', False,
            ['text'], 1, '<doc><p>bar Foo fOO</p></doc>')

    def test__count_or_replace_text_case_insensitive(self):
        self.assertOccurrenceReplaced(
            '<doc><p>foo Foo fOO</p></doc>', 'foo', 'bar', True,
            ['text'], 3, '<doc><p>bar bar bar</p></doc>')

    def test__count_or_replace_text_attributes(self):
        self.assertOccurrenceReplaced(
            '<doc><image title="bar foo baz" path="/bar/foo/baz"/></doc>',
            'foo', 'bar', False, ['text'],
            1, '<doc><image title="bar bar baz" path="/bar/foo/baz"/></doc>')

    def test__count_or_replace_paths_attributes(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="/foo/bar"/></doc>', 'foo', 'bar', False,
            ['paths'], 1, '<doc><image path="/bar/bar"/></doc>')

    def test__count_or_replace_text_and_paths_attributes(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="/foo/bar"/><p>foo</p></doc>', 'foo', 'bar', False,
            ['text', 'paths'], 2, '<doc><image path="/bar/bar"/><p>bar</p></doc>')

    def test__count_or_replace_paths_no_urls(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="http://foo/bar"/></doc>', 'foo', 'bar', False,
            ['paths'], 0, '<doc><image path="http://foo/bar"/></doc>')

    def test__count_or_replace_paths_no_mailto_urls(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="mailto:foo@bar.com"/></doc>', 'foo', 'bar', False,
            ['paths'], 0, '<doc><image path="mailto:foo@bar.com"/></doc>')

    def test__count_or_replace_urls_basic_http(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="http://foo.com/bar/foo"/></doc>', 'foo', 'bar',
            False, ['urls'], 2,
            '<doc><image path="http://bar.com/bar/bar"/></doc>')

    def test__count_or_replace_urls_basic_https_case_insensitive(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="https://foo.com/bar/Foo"/></doc>', 'foo', 'bar',
            True, ['urls'], 2,
            '<doc><image path="https://bar.com/bar/bar"/></doc>')

    def test__count_or_replace_urls_basic_https_case_sensitive(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="https://foo.com/bar/Foo"/></doc>', 'foo', 'bar',
            False, ['urls'], 1,
            '<doc><image path="https://bar.com/bar/Foo"/></doc>')

    def test__count_or_replace_urls_no_ftp(self):
        self.assertOccurrenceReplaced(
            '<doc><image path="ftp://foo.com"/></doc>', 'foo', 'bar', False,
            ['urls'], 0, '<doc><image path="ftp://foo.com"/></doc>')


@ZopeLiteLayerSetup
def installService():
    # Load our ZCML, which add the extension as a Product
    from silva import searchandreplace
    zcml.load_config('configure.zcml', searchandreplace)

    installPackage('silva.searchandreplace')

installService()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ServiceSearchReplaceTestCase))
    return suite
