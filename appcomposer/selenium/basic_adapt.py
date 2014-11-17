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

class BasicAdapt(unittest.TestCase):
    def setUp(self):
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
    
    def test_basic_adapt(self):
        driver = self.driver
        try:
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
            driver.find_element_by_id("sendurlbtn").click()
            self.assertEqual("App adaptation", driver.find_element_by_css_selector("h3").text)
            self.assertEqual("", driver.find_element_by_css_selector("input.btn.btn-primary").text)
            driver.find_element_by_css_selector("input.btn.btn-primary").click()
            self.assertEqual("App Composer :: Create/edit an app", driver.title)
            self.assertEqual("Details of the jsconfig", driver.find_element_by_css_selector("h5.panel-title").text)
            time.sleep(0.5)
            driver.find_element_by_css_selector("input.btn.btn-success").click()
            self.assertEqual("App Composer :: Edit the app content", driver.title)
            self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "iframe"))
            self.assertEqual("Note: Changes will be saved automatically", driver.find_element_by_css_selector("h4.alert.alert-info").text)
            self.assertEqual("is a,is part of,has,leads to,influences,increases,decreases", driver.find_element_by_name("relations").get_attribute("value"))
            self.assertEqual("Preview", driver.find_element_by_id("preview-tab").text)
            driver.find_element_by_id("preview-tab").click()
            driver.find_element_by_link_text("Edit").click()

            # In PhantomJS we have to wait for this element to be visible.

            autoload = driver.find_element_by_name("auto_load")
            for i in range(60):
                try:
                    if autoload.is_displayed():  break
                except:  pass
                time.sleep(1)
            else: self.fail("time out")

            autoload.click()

            driver.save_screenshot("seleniumscreenstep.png")
            driver.find_element_by_name("relations").click()
            driver.find_element_by_name("relations").clear()
            driver.find_element_by_name("relations").send_keys("relation1, relation2, relation3")

            driver.find_element_by_name("combobox_concepts").click()
            for i in range(60):
                try:
                    if "All changes saved" == driver.find_element_by_xpath("//body/div[3]").text: break
                except: pass
                time.sleep(1)
            else: self.fail("time out")
            time.sleep(2)

            driver.find_element_by_link_text("Apps").click()
            driver.find_element_by_link_text("Open").click()
            for i in range(60):
                try:
                    elem = driver.find_element_by_name("auto_load")
                    checked = elem.get_attribute("checked")
                    if checked is None:  break
                except: pass
                time.sleep(1)
            else: self.fail("time out")

            time.sleep(2)
            self.assertEqual("relation1, relation2, relation3", driver.find_element_by_name("relations").get_attribute("value"))
            self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "iframe"))
            driver.find_element_by_link_text("Apps").click()
            driver.find_element_by_link_text("Delete").click()
            driver.find_element_by_name("delete").click()
            driver.find_element_by_link_text("Log out").click()
        except:
            driver.save_screenshot("seleniumscreen.png")
            raise
    
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
