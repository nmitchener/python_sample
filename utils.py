"""
The :class:`Browser` wrapper extends the Selenium ``WebDriver`` that drives
the different browsers. All the methods present on the ``WebDriver`` are also
present on the :class:`Browser` wrapper, but are not documented here.

The documentation for the Selenium **WebDriver** interface can be found here:
http://goldb.org/sst/selenium2_api_docs/html/selenium.webdriver.remote.webdriver.WebDriver-class.html

The documentation for the Selenium **WebElement** interface can be found here:
http://goldb.org/sst/selenium2_api_docs/html/selenium.webdriver.remote.webelement.WebElement-class.html

Basic Usage
-----------
There are several helpers, but the main thing is the :class:`Browser` class
which wraps Selenim 2's driver classes to help create shorthand for the driver
methods and common tasks::

    >>> from pumpkinhead.tests.selenium.utils import *
    >>> browser = utils.get_browser()
    >>> browser.register()
    >>> browser.contains('tester', 'h1')
    <WebElement(<h1 class="name typekit">tester...</h1>)>
    >>> browser.logout()
    >>> browser.quit()


The @autobrowser Pattern
------------------------
The above examples use the :func:`autobrowser` decorator to ensure that the tests
always have a browser instance to work with. This is a shared instance that,
in the above example, is created when ``setup()`` is called, and destroyed when
``teardown()`` is called.

The :func:`autobrowser` decorator allows for a browser to be passed in to
the test function for instances where you want to run a tests against an
existing browser instance so you can control and inspect its state, for
example::

    >>> from pumpkinhead.tests.selenium import utils

    # Manually instantiate browser
    >>> browser = utils.get_browser()
    >>> browser.home()

    # Pass the browser instance to a test
    >>> example.test_01_basic_registration(browser)

    # Do more things with the browser instance
    >>> browser.contains('tester', 'h1')
    <WebEelement(<div class="name">tester001</div>)>

Naming Conventions
------------------
You may have noticed that all the tests in the above example are named with a
``test_##_some_test`` pattern. This is to ensure that tests which share
browser state are always run in the same order, and so that the
:func:`run_numbered_tests` helper can run tests in order, through a certain
test number for development and debugging.

Shortcut Examples
-----------------
Here's some examples of shortcuts built into the :class:`Browser` wrapper::

    >>> from pumpkinhead.tests.selenium import utils
    >>> browser = utils.get_browser()

    # Go to the homepage (http://test.about.me:8080, for example)
    >>> browser.home()

    # Browse to a local path
    >>> browser.go('/about')

    # Find an element (using jQuery selectors)
    >>> browser.find('#content')
    <WebElement(<div class="about clearfix" id="content">About Us...</div>)>
    >>> browser.find('.about .head')
    <WebElement(<div class="head">About Us...</div>)>

    # Shorthand for browser.find()
    >>> browser('#content')
    <WebElement(<div class="about clearfix" id="content">About Us...</div>)>

    # Find an element (using xpath selectors)
    >>> browser.xpath('//a[@href="#team"]')
    <WebElement(<a class="tab button">Team</a>)>
    >>> browser.find('//a[@href="#team"]', browser.xpath)
    <WebElement(<a class="tab button">Team</a>)>

    # Check for existence of a string anywhere on the page
    >>> browser.contains("About Us")
    <WebElement(<title >About.me / About Us</title>)>

    # Wait until an element is present, or time out
    >>> browser.wait(10, lambda b: b('#content'))
    <WebElement(<div class="about clearfix" id="content">About Us...</div>)>
    >>> browser.wait(0, lambda b: b('#content'))
    ------------------------------------------------------------
    Traceback (most recent call last):
        ...
    TimeoutException: Message: None

    # Shorter version of waiting (with default 10 second timeout)
    >>> browser.wait(lambda b: b('#content'))
    <WebElement(<div class="about clearfix" id="content">About Us...</div>)>

    # Change the default selector from jQuery to xpath
    >>> browser.shortcut_method = browser.xpath
    >>> browser('//input')
    <WebElement(<input class="text" id="findpeople" name="findpeople"></input>)>

    # Change it back
    >>> browser.shortcut_method = browser.jQuery

"""
import os
import time
import logging
import traceback
import urllib
import urlparse
from functools import wraps
from datetime import timedelta
import selenium
import selenium.webdriver
from selenium.webdriver import DesiredCapabilities, Firefox, Chrome, Ie, Remote
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import (WebDriverException,
        NoSuchElementException, TimeoutException, ElementNotVisibleException,
        StaleElementReferenceException)

import selenium_cfg


__all__ = [
        'TestFailure',
        'autobrowser',
        'get_browser'
        ]

# Default browser to launch with get_browser
SELENIUM_BROWSER = (os.getenv('SELENIUM_BROWSER')
        or getattr(selenium_cfg, 'SELENIUM_BROWSER', None)
        or 'firefox')

def get_domain_name():
    return (os.getenv('DOMAIN_NAME')
        or getattr(selenium_cfg, 'DOMAIN_NAME', None)
        or '127.0.0.1:8080')
# Default domain
DOMAIN_NAME = get_domain_name()

# @autobrowser instance
CURRENT_BROWSER = None


class TestFailure(WebDriverException):
    """ Exception to be raised when appropriate. Subclasses WebDriverException
        for easy exception handling. """


class Browser(object):
    """
    Helper class for :class:`selenium.webdriver.remote.WebDriver`.

    :param driver: WebDriver instance or callable which returns a WebDriver \
            instance

    This should be used to wrap a Selenium 2 WebDriver instance::

        import selenium.webdriver

        driver = selenium.webdriver.Firefox() # Or Chrome, Ie
        browser = Browser(driver)
        browser.home()

    """
    # This keeps track of whether the browser is the main autobrowser one
    SECONDARY = None

    shortcut_method = None
    """ Method used in the browser("selector") syntax. """

    """ Default number of seconds used in browser.wait(). """
    _default_wait = 10
    @property
    def default_wait(self):
        return self._default_wait
    @default_wait.setter
    def default_wait(self, value):
        # setter so that I can edit this in a shell
        self._default_wait = value
        self._driver.implicitly_wait(value)


    # These have to be available when __init__ runs since they are used in
    # __getattribute__
    _proxy_attrs = set()

    def __init__(self, driver):
        self.DOMAIN_NAME = DOMAIN_NAME

        self.username = None
        self.password = None
        self.email = None

        self._schema = 'http'
        if 'staging'.lower() in self.DOMAIN_NAME.lower():
            self._api_schema = 'https'
        else:
            self._api_schema = 'http'
        self._chrome_resized = False
        self._proxy_attrs = set()

        if callable(driver) and not isinstance(driver, Browser):
            self._driver = driver()
        elif isinstance(driver, Browser):
            self._driver = driver._driver
        else:
            self._driver = driver

        # shortcut method
        #self.shortcut_method = self.jQuery
        self.shortcut_method = self.css_selector

        # wait time to find an element
        self._driver.implicitly_wait(self.default_wait)

        # set timeouts so tests don't hang forever
        self._driver.set_page_load_timeout(120)
        self._driver.set_script_timeout(60)

        # The oritentation attribute causes an exception loading Firefox
        ignore_attrs = set()
        if driver.name == 'firefox':
            ignore_attrs.add('orientation')

        # Configure proxy attributes for the driver
        attrs = set(dir(driver)) - ignore_attrs
        for attr in attrs:
            if not attr.startswith('_') and not getattr(self, attr, None):
                self._proxy_attrs.add(attr)

    def __getattribute__(self, attr):
        """ Proxy self._driver attributes onto the Browser instance. """
        _get = lambda o,a: object.__getattribute__(o, a)
        if attr in _get(self, '_proxy_attrs'):
            return _get(_get(self, '_driver'), attr)
        else:
            return _get(self, attr)

    ### Shortcut methods ###
    def home(self, maximize=False):
        """ Goes to the homepage and maximizes the browser window. On Chrome,
            this causes the page to be reloaded in a popup, since it cannot
            be resized.

            :param bool maximize: Maximize the window after loading

        """
        if maximize:
            self.maximize()
        self._driver.get(self._schema + '://' + self.DOMAIN_NAME)


    def login(self, username, password="testing1", came_from=None):
        """ Log a test user in.

            :param testing_user: TestingUser instance containing a username,
                password and email to use
            :param str password: The user's password (default: testing1)
        """
        if came_from:
            self.go('/login?came_from=' + came_from)
        else:
            self.go('/login')
        self('#login').send_keys(username)
        self('#password').send_keys(password)
        self('button[value="submit"]').click()
        self.username = username
        self.password = password
        self.email = None

    def logout(self):
        """ Logs out the current user. """
        self.go('/logout_handler')
        assert self('h1').contains('Please Log In')

    def go(self, url):
        """ Goes to an About.me based URL.

            :param str url: URL path to load

            The url is prepended with ``http://`` and `DOMAIN_NAME`.

        """
        if not url.startswith('/'):
            url = '/' + url
        return self._driver.get(self._schema + '://' + self.DOMAIN_NAME + url)

    def wait(self, *args):
        """ Shortcut for waiting for an element's presence.

            :param int secs: Seconds to wait (default: 10)
            :param callable until: Callable to wait on (optional)
            :returns: WebElement if found
            :raises: NoSuchElementException

            **Example**::

                # All of these are roughly equivalent
                browser.wait(10).until(lambda b: b.find_element_by_id('id'))
                browser.wait(10, lambda b: b.find('#id'))
                browser.wait(lambda b: b.find('#id'))
                browser('#id')


        """
        if len(args) > 2:
            raise TypeError("Too many arguments")

        secs = self.default_wait
        until = None

        for arg in args:
            if isinstance(arg, (int, long, float)):
                secs = arg
            if callable(arg):
                until = arg

        if until:
            # until = lambda b: until(Browser(b))
            return WebDriverWait(self, secs).until(until)

        return WebDriverWait(self._driver, secs)



    def retry_loop(self,counter,retry_hook=None):
        """ Try generic loop trying function.  Will only catch and retry after
            exceptions of type WebDriverException, TimeoutException or AssertionError
            :param counter: Number of times to retry
            :param function retry_hook: A hook to be called after each attempt.
                This will be called at least once.
        """
        while counter > 1:
            try:
                return retry_hook()
            except (WebDriverException, TimeoutException, StaleElementReferenceException, AssertionError):
                time.sleep(0.5)
                counter-=1

        return retry_hook()

    def find(self, val, method=None):
        """ Shortcut for finding elements.

            :param str val: Selector value
            :param callable method: Selector callable (default: :meth:`jQuery`)
            :returns: WebElement if found
            :raises: NoSuchElementException

        """
        method = method or self.shortcut_method
        return method(val)

    def assert_banner_text(self, text):
        def _banner_check(b):
            element = b.css_selector('.notification.banner')
            return text in element.text

        self.wait(lambda b: _banner_check(b))

    def wait_for_save(self):
        time.sleep(selenium_cfg.AJAX_SAVE_DELAY)
        def ajax_inactive(b):
            val = b.execute_script('return jQuery.active')
            return val == 0
        self.wait(ajax_inactive)

    def dismiss_welcome_modal(self):
        """ Get rid of the welcome modal so other things can be clicked
        """
        self.wait(lambda self: self.css_selector('.ui-dialog.welcome a.ui-dialog-titlebar-close').is_displayed())
        self.css_selector_wait('.ui-dialog.welcome a.ui-dialog-titlebar-close').click()
        self.wait(lambda self: self.css_selector('#profile_box .tooltip-close').is_displayed())
        self.css_selector_wait('#profile_box .tooltip-close').click()


    def contains(self, text, tag='*'):
        """ Find and return an element containing the specified text.

            :param str text: Text to look for
            :param str tag: Tag type to look for (default: \*)
            :returns: WebElement if found, otherwise None

        """
        def _do_it():
            try:
                return self.xpath("""//%s[contains(text(),"%s")]""" % (tag, text))
            except NoSuchElementException:
                # maybe the text is in a child tag
                if (tag != '*'):
                    return self.xpath("""//%s//*[contains(text(),"%s")]""" % (tag, text))
                raise

        return self.retry_loop(2, _do_it)

    def not_contains(self, text, tag='*', wait=1):
        """ Returns True if the element is not on the page
            Note: This doesn't wait for the element to not be there.

            :param str text: Text to look for
            :param str tag: Tag type to look for (default: \*)
            :returns: WebElement if found, otherwise None

        """
        absent = False
        default_wait = self.default_wait
        self.default_wait = wait
        try:
            absent = not self.xpath("""//%s[text()[contains(.,"%s")]]""" % (tag, text)).is_displayed()
        except NoSuchElementException:
            absent = True
        finally:
            self.default_wait = default_wait

        return absent


    def not_find(self, selector, wait=1):
        """ Returns True if the selector doesn't match any element on the page
            Note: This doesn't wait for the element to not be there.

            :param str selector: Text to look for
            :returns: True if element is absent, else False

        """
        absent = False
        default_wait = self.default_wait
        self.default_wait = wait
        try:
            absent = not self.find_element_by_css_selector(selector).is_displayed()
        except NoSuchElementException:
            absent = True
        finally:
            self.default_wait = default_wait

        return absent


    def maximize(self):
        """ Maximize the browser's window """
        #self._driver.set_window_size(2650, 1900)
        self._driver.set_window_size(1000, 800)
        if getattr(selenium_cfg, 'SELENIUM_WINDOW_POSITION_X', False):
            x = getattr(selenium_cfg, 'SELENIUM_WINDOW_POSITION_X', 0)
            y = getattr(selenium_cfg, 'SELENIUM_WINDOW_POSITION_Y', 0)
            print x
            print y
            self._driver.set_window_position(x, y)

    def breakpoint(self, width):
        """ Set window size to any width breakpoint """
        self._driver.set_window_size(width, 800)
        if getattr(selenium_cfg, 'SELENIUM_WINDOW_POSITION_X', False):
            x = getattr(selenium_cfg, 'SELENIUM_WINDOW_POSITION_X', 0)
            y = getattr(selenium_cfg, 'SELENIUM_WINDOW_POSITION_Y', 0)
            self._driver.set_window_position(x, y)

    def force_visible(self, element):
        """ Force something to be visible so Selenium doesn't bitch about
            interacting with it

            :param element: the WebElement object
        """
        self._driver.execute_script("""
            function force_visible(el) {
                el.style.visibility = 'visible';
                el.style.display = 'block';
            }
            el = arguments[0];

            force_visible(el);
            while (el = el.parent) {
                force_visible(el);
            }
            """,
            element)



    def quit(self):
        """ Wraps the driver's quit method to work with the :func:`autobrowser`
            decorator.
        """
        global CURRENT_BROWSER
        if (not self.SECONDARY):
            CURRENT_BROWSER = None
        self._driver.quit()

    def __call__(self, val=None):
        """ Super shortcut for finding an element or getting an ActionChains
            instance.

            :param str val: Selector value (optional)
            :param callable method: Selector callable (default: :meth:`jQuery`)

            This is a smarter version of :meth:`find` that waits first for the
            desired element to be present on the page, and second for the
            element to be displayed, in order to better accomodate rendering
            and javascript quirks.

            If ``val`` is not supplied, returns an ActionChains instance.
            Otherwise attempts to :meth:`find` an element.

        """
        if not val:
            return selenium.webdriver.common.action_chains.ActionChains(self)

        self.wait(lambda b: b.find(val))
        self.wait(lambda b: b.find(val).is_displayed())
        return self.find(val)


    def wait_until_ready(self):
        # only wait if it's our stuff, not 3rd party sites but not in production
        u = urlparse.urlparse(self.current_url)
        if ( ('.about.me' or '127.0.0.1') in u.hostname 
            and not u.path.startswith('/content/')):
            #time.sleep(getattr(selenium_cfg, 'SELENIUM_DELAY', 0))
            counter = 30
            result = False
            while (counter > 0):
                # print 'checking for page readiness'
                result = self._driver.execute_script('return window.selenium_ready')
                if (result):
                    break
                # print 'page not ready yet'
                counter = counter - 1
                time.sleep(.1)
            assert result, "window.selenium_ready wasn't true"


    def _wait_until_ready_wrapper(self, func):
        """ Wrapper for browser methods to make the browser wait until our
            pages are loaded
            TODO: turn this into a wrapper you can use as a decorator

        """
        def inner(*args, **kwargs):
            self.wait_until_ready()
            return func(*args, **kwargs)
        return inner


    ### Selector shortcut properties ###
    @property
    def class_name(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_class_name)

    @property
    def css_selector(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_css_selector)

    @property
    def id(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_id)

    @property
    def link_text(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_link_text)

    @property
    def name(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_name)

    @property
    def partial_link_text(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_partial_link_text)

    @property
    def tag_name(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_tag_name)

    @property
    def xpath(self):
        return self._wait_until_ready_wrapper(self._driver.find_element_by_xpath)


def get_browser(name=None, resize=True, secondary=False, remote_address='localhost'):
    """ Returns a :class:`Browser` instance using the driver for the given
        browser name.

        :param str name: Name of the browser (default: ``firebug``)

        Browser name should be one of: ``firefox``, ``chrome``, ``ie``,
        ``firebug``, ``remote``, or ``phantomjs``.

        Checks the environment variable ``SELENIUM_BROWSER`` for the browser
        name if none is supplied.

        :param str remote_address: Network name or IP of remote machine running
        remote selenium server.  The default is localhost, which is what you'd
        use for controlling a browser running under a different user on the
        same machine (default: ``localhost``)

    """
    if not name:
        name = SELENIUM_BROWSER

    drivers = {
            'firefox': Firefox,
            'ie': Ie,
            'chrome': lambda: Chrome(
                executable_path=selenium_cfg.HERE + '/bin/chromedriver'),
            'remote': lambda: Remote(
                command_executor='http://' + remote_address + ':4444/wd/hub',
                desired_capabilities=DesiredCapabilities.FIREFOX),
            'phantomjs': selenium.webdriver.PhantomJS
            }
    browser = Browser(driver=drivers[name]())
    browser.SECONDARY = secondary
    return browser


def autobrowser(func):
    """ Decorator to ensure that we can pass in a :class:`Browser` instance to
        test methods if we want, and otherwise one is provided.

    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Is there a browser being passed in?
        has_browser = False
        for arg in args:
            if isinstance(arg, Browser):
                has_browser = True

        # Browser already exists, don't add it to args
        if has_browser:
            return func(*args, **kwargs)

        # No browser, let's get one and pass it on
        global CURRENT_BROWSER
        if not CURRENT_BROWSER:
            CURRENT_BROWSER = get_browser()
            CURRENT_BROWSER.maximize()

        # catch exceptions to grab screenshots
        try:
            return func(CURRENT_BROWSER, *args, **kwargs)
        except (Exception, AssertionError) as e:
            if getattr(selenium_cfg, 'SELENIUM_SCREENSHOTS', False) and os.getenv('SELENIUM_SCREENSHOTS') == 'true':
                if not getattr(e, 'msg', False):
                    e.msg = ''
                try:
                    image_path = selenium_cfg.HERE + '/selenium_test_results/images/'

                    if (not os.path.exists(selenium_cfg.HERE + os.path.sep + 'selenium_test_results')):
                        os.mkdir(selenium_cfg.HERE + os.path.sep + 'selenium_test_results')

                    if (not os.path.exists(image_path)):
                        os.mkdir(image_path)

                    filename = str(time.time()) + '.jpg'
                    CURRENT_BROWSER._driver.save_screenshot(image_path + filename)
                    e.msg += ' [SCREENSHOT: {}]'.format('images/' + filename)
                except:
                    e.msg += ' (screenshot failed)'
            raise

    return wrapper


def run_numbered_tests(module, initial=0, through=99, td=True, reload_module=True, domain=None):
    """ Helper that runs a subset of tests in a module. Useful for debugging.
        Tests can also be contained in a class named ``TestClass``.
        Only works on tests with the ``test_NN_sometest`` naming convention.
        Automatically runs the module.Test.setup() and module.Test.teardown() methods.

        :param module: Module to run tests from
        :param int initial: Number of the test to start with (optional)
        :param int through: Number of tests to run last (optional)
        :param bool td: Run module.Test.teardown() before running tests
            (optional)
        :param bool reload_module: Reload the module before running tests
            (optional)

    """
    # reset domain name in case it was changed in a previous test
    global DOMAIN_NAME
    if not domain:
        DOMAIN_NAME = get_domain_name()
    else:
        DOMAIN_NAME = domain

    if reload_module:
        reload(module)

    try:
        test_entity = module.TestClass()
        if getattr(test_entity, 'setup_class', False):
            test_entity.setup = module.TestClass.setup_class
        if getattr(test_entity, 'teardown_class', False):
            test_entity.teardown = module.TestClass.teardown_class
    except:
        test_entity = module

    if td:
        try:
            test_entity.teardown()
        except:
            pass

    if initial == 0 and getattr(test_entity, 'setup', False):
        test_entity.setup()

    test_range = range(initial, through + 1)

    start = time.time()
    try:
        for test in (getattr(test_entity, name, lambda b: None)
                for name in sorted(dir(test_entity))
                if name[5:7] in ['%02d' % i for i in test_range]):
            print "Running", test.func_name
            test()

        if td and getattr(test_entity, 'teardown', False):
            test_entity.teardown()
    except:
        traceback.print_exc()
    finally:
        print '\a' * 5
        print "Tests run in %s" % timedelta(seconds=time.time() - start)
        return CURRENT_BROWSER


def patch_WebElement():
    """ Changes the :class:`~selenium.webdriver.remote.webelement.WebElement`'s
        __repr__ method to be more useful.

    """

    cls = selenium.webdriver.remote.webelement.WebElement
    def _repr(self):
        vals = []
        attrs = ('class', 'id', 'name', 'href')
        for attr in attrs:
            val = self.get_attribute(attr)
            if val:
                vals.append(u'%s="%s"' % (attr, val))
        vals = u' '.join(vals)
        text = self.text[:20] + u' [...]' if len(self.text) > 20 else self.text
        text = u'<WebElement(%s)>' % (u"<%s %s>%s</%s>" %
                    (self.tag_name, vals, text, self.tag_name))
        text = text.encode('ascii', 'ignore')
        text = text.replace('\n', r'\n')
        return text

    def _contains(self, text, tag='*'):
        """ Find and return an element containing the specified text.

            :param str text: Text to look for
            :param str tag: Tag type to look for (default: \*)
            :returns: WebElement if found, otherwise None

        """
        time.sleep(getattr(selenium_cfg, 'SELENIUM_DELAY', 0))
        
        if (tag == '*' or self.tag_name == tag):
            # search this element too
            add_here = '|../%s[contains(text(),"%s")]' % (self.tag_name, text)
        else:
            add_here = ''
        return self.find_element_by_xpath(""".//%s[contains(text(),"%s")]%s""" % (tag, text, add_here))


    cls.__repr__ = _repr
    cls.contains = _contains


def suppress_logging():
    """ Suppress Selenium log output. """
    log = logging.getLogger('selenium')
    log.setLevel(logging.INFO)



# Monkeypatching!
if True:
    patch_WebElement()
    suppress_logging()


