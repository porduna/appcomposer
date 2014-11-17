# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re

import os

class BasicTranslate(unittest.TestCase):
    def setUp(self):

        if os.environ.get("SELENIUM_HEADLESS"):
            self.driver = webdriver.PhantomJS()
        else:
            self.profile = FirefoxProfile();
            self.profile.set_preference("intl.accept_languages", "en")
            self.driver = webdriver.Firefox(self.profile)

        self.driver.set_window_size(1400, 1000)

        self.driver.implicitly_wait(30)
        self.base_url = "http://localhost:5000/"
        self.verificationErrors = []
        self.accept_next_alert = True
    
    def test_basic_translate(self):
        driver = self.driver
        driver.get(self.base_url + "/")
        driver.find_element_by_link_text("Use it!").click()
        driver.find_element_by_id("login").clear()
        driver.find_element_by_id("login").send_keys("admin")
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys("password")
        driver.find_element_by_xpath("//button[@type='submit']").click()
        try: self.assertEqual("Welcome Administrator!", driver.find_element_by_css_selector("h1").text)
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_xpath(u"(//a[contains(text(),'Start composing »')])[3]").click()
        self.assertEqual("Translate", driver.find_element_by_id("apptitle").text)
        for i in range(60):
            try:
                if self.is_element_present(By.CSS_SELECTOR, "td.sorting_1"): break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
        for i in range(60):
            try:
                elem = self.driver.find_element_by_css_selector("#loading-msg")
                if not elem.is_displayed():  break
                # MODIFICATION: The following line is commented out because it is throwing an
                # exception under PhantomJS. Replaced by the find_element and is_displayed.
                # if not self.is_element_present(By.CSS_SELECTOR, "#loading-msg:visible"): break
            except:
                pass
            time.sleep(1)
        else: self.fail("time out")
        driver.find_element_by_css_selector("input[type=\"search\"]").send_keys("Concept Mapper")
        for i in range(60):
            try:
                if "Concept Mapper" == driver.find_element_by_css_selector("td.sorting_1").text: break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_id("sendurlbtn").click()
        try: self.assertEqual("Concept Mapper", driver.find_element_by_id("appfullname").text)
        except AssertionError as e: self.verificationErrors.append(str(e))
        self.assertEqual("You are the owner of this App's default translation.", driver.find_element_by_css_selector("p").text)
        self.assertEqual("on", driver.find_element_by_id("accept-proposals").get_attribute("value"))
        try: self.assertEqual("View Proposed Translations 0", driver.find_element_by_css_selector("button.btn.btn-warning").text)
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_css_selector("span.select2-chosen").click()
        driver.find_element_by_css_selector("span.select2-chosen").click()
        driver.find_element_by_id("localisebtn").click()
        self.assertEqual("standard", driver.find_element_by_css_selector("b").text)
        self.assertEqual("Transfer Ownership", driver.find_element_by_xpath("//a/button").text)
        self.assertEqual("Publish Translation", driver.find_element_by_css_selector("button.btn.btn-primary").text)
        try: self.assertEqual("Name", driver.find_element_by_css_selector("div[title=\"ut_tools_conceptmapper_name\"]").text)
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("field_1").clear()
        driver.find_element_by_id("field_1").send_keys("Concept Map Modified")
        driver.find_element_by_name("save_exit").click()
        self.assertEqual("TRANSLATE", driver.find_element_by_link_text("TRANSLATE").text)
        self.assertEqual("ADAPT", driver.find_element_by_link_text("ADAPT").text)
        self.assertEqual("Your Applications", driver.find_element_by_css_selector("h1").text)
        self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-success > div > h3").text)
        driver.find_element_by_link_text("Open").click()
        driver.find_element_by_id("localisebtn").click()
        self.assertEqual("Concept Map Modified", driver.find_element_by_id("field_1").get_attribute("value"))
        driver.find_element_by_id("sendurlbtn").click()
        driver.find_element_by_id("backtoindexbtn").click()
        driver.find_element_by_id("localisebtn").click()
        self.assertEqual("", driver.find_element_by_id("field_3").text)
        self.assertEqual("", driver.find_element_by_id("field_1").text)
        driver.find_element_by_name("save_exit").click()
        driver.find_element_by_link_text("Delete").click()
        driver.find_element_by_name("delete").click()
        self.assertEqual("No application.", driver.find_element_by_css_selector("h2").text)
        self.assertEqual(u"Start composing »", driver.find_element_by_xpath(u"(//a[contains(text(),'Start composing »')])[3]").text)
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
