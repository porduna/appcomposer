# -*- coding: utf-8 -*-
import os
from selenium import webdriver
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re
from _utils import reset_database

class DynModals(unittest.TestCase):
    def setUp(self):

        reset_database()

        if os.environ.get("SELENIUM_HEADLESS"):
            self.driver = webdriver.PhantomJS()
        else:
            self.profile = FirefoxProfile();
            self.profile.set_preference("intl.accept_languages", "en")
            self.driver = webdriver.Firefox(self.profile)

        self.driver.set_window_size(1600, 1200)

        self.driver.implicitly_wait(30)
        self.base_url = "http://localhost:5000/"
        self.verificationErrors = []
        self.accept_next_alert = True

    def wait_until_equals(self, value, func, *args, **kwargs):
        seconds = 5
        step = 0.05

        while seconds >= 0 and value != func(*args, **kwargs):
            time.sleep(step)
            seconds -= step

        self.assertEqual(value, func(*args, **kwargs))

    def test_dyn_modals(self):
        driver = self.driver
        driver.get(self.base_url + "/")
        driver.find_element_by_link_text("Use it!").click()
        driver.find_element_by_id("login").clear()
        driver.find_element_by_id("login").send_keys("admin")
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys("password")
        driver.find_element_by_xpath("//button[@type='submit']").click()


        driver.find_element_by_xpath(u"(//a[contains(text(),'Start composing »')])[2]").click()
        for i in range(60):
            try:
                if self.is_element_present(By.CSS_SELECTOR, "td.sorting_1"): break
            except: pass
            time.sleep(1)
        else: self.fail("time out")

        time.sleep(0.5)

        driver.find_element_by_css_selector("td.sorting_1").click()

        time.sleep(0.5)

        driver.find_element_by_id("sendurlbtn").click()
        driver.find_element_by_css_selector("input.btn.btn-primary").click()
        driver.find_element_by_css_selector("input.btn.btn-success").click()
        driver.find_element_by_link_text("Apps").click()
        self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("h3.app-title.dyn-changeable").text)
        driver.find_element_by_css_selector("h3.app-title.dyn-changeable").click()

        time.sleep(0.2)

        driver.find_element_by_id("appname-field").clear()
        driver.find_element_by_id("appname-field").send_keys("The Best Concept Mapper")
        driver.find_element_by_css_selector("button.btn.btn-primary").click()

        time.sleep(1)

        self.assertEqual("Apps - User Profile", driver.title)
        self.assertEqual("The Best Concept Mapper", driver.find_element_by_css_selector("h3.app-title.dyn-changeable").text)
        driver.find_element_by_id("desclabel").click()

        time.sleep(0.2)

        driver.find_element_by_id("appdesc-field").clear()
        driver.find_element_by_id("appdesc-field").send_keys("The description for the app")
        driver.find_element_by_css_selector("#appdesc-modal > div.modal-dialog > div.modal-content > form > div.modal-footer > button.btn.btn-primary").click()

        time.sleep(0.2)

        self.wait_until_equals("The description for the app", lambda: driver.find_element_by_id("descfield").text)

        driver.find_element_by_link_text("Open").click()

        time.sleep(0.2)

        self.assertEqual("App Composer :: Edit the app content", driver.title)
        self.assertEqual("Adapt - The Best Concept Mapper", driver.find_element_by_id("apptitle").text)
        driver.find_element_by_id("apptitle").click()

        time.sleep(0.2)

        driver.find_element_by_id("appname-field").clear()
        driver.find_element_by_id("appname-field").send_keys("The new name for Concept Mapper")
        driver.find_element_by_css_selector("button.btn.btn-primary").click()

        time.sleep(1)

        self.assertEqual("App Composer :: Edit the app content", driver.title)
        self.assertEqual("Adapt - The new name for Concept Mapper", driver.find_element_by_id("apptitle").text)
        driver.find_element_by_link_text("Apps").click()
        driver.find_element_by_link_text("Delete").click()
        driver.find_element_by_name("delete").click()
        driver.find_element_by_xpath(u"(//a[contains(text(),'Start composing »')])[3]").click()
        for i in range(60):
            try:
                if "The Concept Mapper tool lets you cre..." == driver.find_element_by_css_selector("p.p1").text: break
            except: pass
            time.sleep(1)
        else: self.fail("time out")

        time.sleep(1)

        driver.find_element_by_css_selector("p.p1").click()
        driver.find_element_by_id("sendurlbtn").click()
        driver.find_element_by_link_text("Apps").click()
        driver.find_element_by_link_text("Open").click()
        driver.find_element_by_id("appfullname").click()

        time.sleep(0.2)

        driver.find_element_by_id("appname-field").clear()
        driver.find_element_by_id("appname-field").send_keys("My Concept Mapper")
        driver.find_element_by_css_selector("button.btn.btn-primary").click()

        time.sleep(0.2)

        self.wait_until_equals("My Concept Mapper", lambda : driver.find_element_by_id("appfullname").text)
        driver.find_element_by_link_text("Apps").click()
        self.assertEqual("My Concept Mapper", driver.find_element_by_css_selector("h3.app-title.dyn-changeable").text)
        driver.find_element_by_css_selector("h3.app-title.dyn-changeable").click()

        time.sleep(0.2)

        driver.find_element_by_id("appname-field").clear()
        driver.find_element_by_id("appname-field").send_keys("My Concept Mapper Name")
        driver.find_element_by_css_selector("button.btn.btn-primary").click()

        time.sleep(0.2)
        self.wait_until_equals("My Concept Mapper Name", lambda : driver.find_element_by_css_selector("h3.app-title.dyn-changeable").text)
        driver.find_element_by_id("descfield").click()

        time.sleep(0.2)

        driver.find_element_by_id("appdesc-field").clear()
        driver.find_element_by_id("appdesc-field").send_keys("This is quite a great Concept Mapper")
        driver.find_element_by_css_selector("#appdesc-modal > div.modal-dialog > div.modal-content > form > div.modal-footer > button.btn.btn-primary").click()

        time.sleep(0.2)

        self.wait_until_equals("This is quite a great Concept Mapper", lambda : driver.find_element_by_id("descfield").text)
        driver.find_element_by_link_text("Delete").click()
        driver.find_element_by_name("delete").click()
        driver.find_element_by_link_text("Log out").click()
    
    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException, e: return False
        return True
    
    def is_alert_present(self):
        try: self.driver.switch_to_alert()
        except NoAlertPresentException, e: return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
