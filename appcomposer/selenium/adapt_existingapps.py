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

class AdaptExistingapps(unittest.TestCase):
    def setUp(self):

        if os.environ.get("SELENIUM_HEADLESS"):
            self.driver = webdriver.PhantomJS()
        else:
            self.profile = FirefoxProfile()
            self.profile.set_preference("intl.accept_languages", "en")
            self.driver = webdriver.Firefox(self.profile)

        self.driver.set_window_size(1300, 1000)
        self.driver.implicitly_wait(30)
        self.base_url = "http://localhost:5000/"
        self.verificationErrors = []
        self.accept_next_alert = True
    
    def test_adapt_existingapps(self):
        driver = self.driver
        driver.get(self.base_url + "/")
        driver.find_element_by_link_text("Use it!").click()
        driver.find_element_by_id("login").clear()
        driver.find_element_by_id("login").send_keys("testuser")
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
        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_id("sendurlbtn").click()
        self.assertEqual("App Composer :: Adaptation tool", driver.title)

        # TODO: Added replace to fix python-only diff.
        self.assertEqual("Existing Adaptations: View or Duplicate an existing Adaptation instead of creating your own", driver.find_element_by_css_selector("div.container > h3").text.replace("\n", " "))

        driver.find_element_by_css_selector("td.dataTables_empty").click()
        self.assertEqual("Nothing found", driver.find_element_by_css_selector("td.dataTables_empty").text)
        self.assertEqual("View", driver.find_element_by_id("view-btn").text)
        self.assertEqual("Duplicate", driver.find_element_by_id("duplicate-btn").text)
        driver.find_element_by_css_selector("input.btn.btn-primary").click()
        driver.find_element_by_name("app_description").clear()
        driver.find_element_by_name("app_description").send_keys("A concept mapper adaptation")
        driver.find_element_by_css_selector("input.btn.btn-success").click()
        driver.find_element_by_link_text("Log out").click()
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
        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_id("sendurlbtn").click()
        self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("td.sorting_1").text)
        self.assertEqual("", driver.find_element_by_css_selector("input.btn.btn-primary").text)

        # Fails under Python, not under Firefox IDE.
        # self.assertEqual("App adaptation Create adaptations of customizable Go-Lab applications.\n \n Read more \n \n \n \n \n \n Existing Adaptations: View or Duplicate an existing Adaptation instead of creating your own \n Display 102550100 records per page\nSearch:\n TitleDescriptionOwnerType TitleDescriptionOwnerType Concept MapperTest Useradapt Showing page 1 of 1\nPrevious1Next\n\n View Duplicate", driver.find_element_by_xpath("//body/div[2]").text.replace("\n", " "))

        self.assertEqual("Test User", driver.find_element_by_xpath("//table[@id='appsearch-table']/tbody/tr/td[3]").text)
        self.assertEqual("A concept mapper adaptation", driver.find_element_by_xpath("//table[@id='appsearch-table']/tbody/tr/td[2]").text)
        driver.find_element_by_css_selector("td.sorting_1").click()
        self.assertEqual("Duplicate", driver.find_element_by_id("duplicate-btn").text)
        driver.find_element_by_id("duplicate-btn").click()
        driver.find_element_by_css_selector("button.btn").click()
        driver.find_element_by_link_text("Apps").click()
        self.assertEqual("Concept Mapper (2)", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-info > div > h3").text)
        driver.find_element_by_link_text("Delete").click()
        driver.find_element_by_name("delete").click()
        driver.find_element_by_xpath(u"(//a[contains(text(),'Start composing »')])[2]").click()
        for i in range(60):
            try:
                if self.is_element_present(By.CSS_SELECTOR, "td.sorting_1"): break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_id("sendurlbtn").click()
        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_id("view-btn").click()
        self.assertEqual("App Composer :: Preview the app", driver.title)
        self.assertEqual("Preview", driver.find_element_by_id("preview-tab").text)
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "iframe"))
        driver.find_element_by_link_text("Apps").click()
        driver.find_element_by_link_text("Log out").click()
        driver.find_element_by_link_text("Use it!").click()
        driver.find_element_by_id("login").clear()
        driver.find_element_by_id("login").send_keys("testuser")
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys("password")
        driver.find_element_by_xpath("//button[@type='submit']").click()
        driver.find_element_by_link_text("Apps").click()
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
