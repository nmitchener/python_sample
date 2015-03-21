# -*- coding: utf-8 -*-
"""
Test spotlights

to run this test in ipython:
navigate to this directory
open ipython and type the following 3 commands:
    import utils
    import test_spotlight_hireme
    b = utils.run_numbered_tests(test_spotlight_hireme)
"""

from time import sleep
from utils import *


class TestClass:

    @autobrowser
    def test_00_setup(b, cls):
        b.login('justa_tester')

    @autobrowser
    def test_01_create(b, cls):
        # create
        b.go('/spotlight')
        sleep(1)
        b.contains('Hire me').click()

        # locations
        sleep(.5)
        b.find_elements_by_css_selector('input.location')[0].send_keys('austin')
        b.contains('Texas').click()
        b.contains('Add location').click()
        b.find_elements_by_css_selector('input.location')[1].send_keys('anchorage')
        b.contains('Alaska').click()
        b('.locations .delete').click()

        # skills
        b.find_elements_by_css_selector('input.skills')[0].send_keys('deleted skill')
        b.find_elements_by_css_selector('input.skills')[1].send_keys('skill two')
        b.find_elements_by_css_selector('input.skills')[2].send_keys('skill three')
        b.contains('Add more skills').click()
        b.find_elements_by_css_selector('input.skills')[3].send_keys('skill four')
        b('.skills .delete').click()

        # work history
        b.find_elements_by_css_selector('input.workhistory')[0].send_keys('microsoft')
        b.contains('Microsoft').click()
        b.contains('Add more companies').click()
        b.find_elements_by_css_selector('input.workhistory')[1].send_keys('cisco')
        b.contains('Cisco').click()

        # education
        b.find_elements_by_css_selector('input.education')[0].send_keys('uni')
        b.contains('Southern California').click()
        b.contains('Add more education').click()
        b.find_elements_by_css_selector('input.education')[1].send_keys('devry')
        b.contains('Devry').click()

        # links
        b.contains('Add more links').click()
        b.find_elements_by_css_selector('.links input.link')[0].send_keys('error')
        b.find_elements_by_css_selector('.links input.link')[1].send_keys('google.com')
        b.find_elements_by_css_selector('.links input.link')[2].send_keys('yahoo.com')

        # test missing required stuff
        b.contains('Next').click()
        assert b.contains('This field is required')
        assert b.contains('Please enter a valid URL')

        b('.links .delete').click()

        b('input.role').send_keys('initial role')

        b('#headline').send_keys('initial headline')

        b.contains('Next').click()

        b('#btn').clear()
        b('#btn').send_keys('hiremenow')
        b('#msg').send_keys('cuz I said so')

        # wait for page change
        orig_url = b.current_url
        b.contains('Publish').click()
        b.wait(lambda b: b.current_url != orig_url)

    @autobrowser
    def test_02_bar_display(b, cls):
        b.breakpoint(1000)
        assert b('.spotlight-banner').is_displayed()
        b.breakpoint(320)
        assert b.not_find('.spotlight-banner')
        b.maximize()

    @autobrowser
    def test_03_view(b, cls):
        # test link
        b.contains('hiremenow').click()

        assert b.contains('initial role')
        # skills
        assert b.contains('skill two')
        assert b.contains('skill three')
        assert b.contains('skill four')
        # locations
        assert b.contains('Anchorage')
        # work history
        assert b.contains('Microsoft')
        assert b.contains('Cisco')
        # education
        assert b.contains('University of Southern California')
        assert b.contains('Devry')

        assert b.not_contains('deleted')
        assert b.not_contains('Texas')

        assert 'http://google.com' in b.contains('http://google.com').get_attribute('href')
        assert 'http://yahoo.com' in b.contains('http://yahoo.com').get_attribute('href')

    @autobrowser
    def test_07_delete(b, cls):
        b.go('/spotlight')
        sleep(1)
        b.contains('Delete this Spotlight').click()

        # wait for page change
        orig_url = b.current_url
        b('.ui-dialog').contains('Delete').click()
        b.wait(lambda b: b.current_url != orig_url)

        assert b.not_contains('hiremenow')

    @classmethod
    @autobrowser
    def teardown_class(b, cls):
        b.quit()
