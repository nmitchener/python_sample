# -*- coding: utf-8 -*-
"""
Test login

to run this test in ipython:
navigate to this directory
open ipython and type the following 3 commands:
    import utils
    import test_login
    b = utils.run_numbered_tests(test_login)
"""

from time import sleep
from utils import *


class TestClass:

    # open login

    @autobrowser
    def test_00_setup(b, cls):
        b.go('/login')

    # empty username

    @autobrowser
    def test_01_badlogin(b, cls):
        b.login('justa_badusername')
        b.find_elements_by_css_selector('button.button-submit')[0].click()
        assert b.contains('Your email or username doesn’t match your password.')

    # close-banner

        sleep(2)
        b.find_elements_by_css_selector('div.banner-close')[0].click()

    # empty password

        assert True

    
    # bad username

        b.login('justa_badusername')
        b.find_elements_by_css_selector('button.button-submit')[0].click()
        assert b.contains('Your email or username doesn’t match your password.')

    # close-banner

        sleep(2)
        b.find_elements_by_css_selector('div.banner-close')[0].click()


    # forgot password

        # bad username

    @autobrowser
    def test_02_forgotpassword(b, cls):
        b.find_elements_by_css_selector('span.forgotpassword-link')[0].click()
        sleep(2)
        b.find_element(by='id', value='identifier').send_keys('bad$username$')
        b.find_elements_by_css_selector("button.submitbutton")[0].click()
        assert b.contains('That username does not exist. Please check your username, or enter your email address.')
        b.find_element(by='id', value='identifier').clear()

        # empty username 

        b.find_element(by='id', value='identifier').send_keys('') 
        b.find_elements_by_css_selector("button.submitbutton")[0].click()
        sleep(2)
        assert b.contains('This field is required.')
        b.find_element(by='id', value='identifier').clear()
 
        # bad email 

        b.find_element(by='id', value='identifier').send_keys('@bad.email') 
        b.find_elements_by_css_selector("button.submitbutton")[0].click()
        sleep(2)
        assert b.contains('The username portion of the email address is invalid')
        b.find_element(by='id', value='identifier').clear()

        # good username

        b.find_element(by='id', value='identifier').send_keys('justa_tester')
        b.find_elements_by_css_selector("button.submitbutton")[0].click()
        sleep(2)
        assert b.contains('We have emailed you a link to change your password.')

        # cancel button 

        assert True


        # valid email - don't have an email for justa_tester

        assert True


    # login with good username

    @autobrowser
    def test_03_goodlogin(b, cls):
        b.login('justa_tester')
        assert b.find_elements_by_css_selector('span.viewer-display-name')[0].text == 'Justa'
        sleep(2)

    # remember_me checkbox - test if the cookie times out as it supposed to
    @autobrowser
    def test_04_rememberMe(b, cls):
        b.go('/logout')
        assert True 

    # test other links on the login page
    @autobrowser
    def test_05_testLinks(b, cls):

        # Sign Up
        sleep(2)
        b.find_elements_by_css_selector("span.signuptoggle")[0].click()
        assert b.contains('New?') 

        # About.me
        assert True

        # Discover
        assert True

        # Facebook Login - experimented with switching control to a new window, but didn't get it to work.
        assert True

        # Twitter Login
        assert True


    @classmethod
    @autobrowser
    def teardown_class(b, cls):
        b.quit()
