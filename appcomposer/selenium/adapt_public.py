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


class AdaptPublic(unittest.TestCase):
    def setUp(self):

        reset_database()

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
    
    def test_adapt_public(self):
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
                if self.is_element_present(By.CSS_SELECTOR, "td[title=\"<p>This app allows to create hypotheses</p>\"]"): break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
        driver.find_element_by_css_selector("td[title=\"<p>This app allows to create hypotheses</p>\"]").click()
        driver.find_element_by_css_selector("p.p1").click()
        # ERROR: Caught exception [ERROR: Unsupported command [selectWindow | null | ]]
        driver.find_element_by_id("sendurlbtn").click()
        driver.find_element_by_css_selector("input.btn.btn-primary").click()
        driver.find_element_by_css_selector("input.btn.btn-success").click()
        driver.find_element_by_link_text("Log out").click()
        driver.get("http://localhost:5000/composers/adapt/type_selection?appurl=http%3A%2F%2Fgo-lab.gw.utwente.nl%2Fproduction%2Fconceptmapper_v1%2Ftools%2Fconceptmap%2Fsrc%2Fmain%2Fwebapp%2Fconceptmapper.xml&appname=Concept+Mapper&sendurl=")
        self.assertEqual("App Composer :: Adaptation tool (public)", driver.title)
        self.assertEqual("View", driver.find_element_by_id("view-btn").text)
        self.assertEqual("Duplicate", driver.find_element_by_id("duplicate-btn").text)
        self.assertEqual("", driver.find_element_by_css_selector("input.btn.btn-primary").text)
        self.assertEqual("Read more", driver.find_element_by_link_text("Read more").text)
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "td.sorting_1"))
        self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("td.sorting_1").text)
        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_link_text("Read more").click()
        self.assertEqual("App Composer :: About", driver.title)


        # Go to previous page.
        driver.back()


        driver.find_element_by_css_selector("td.sorting_1").click()
        driver.find_element_by_id("view-btn").click()
        self.assertEqual("App Composer :: Preview the app", driver.title)
        self.assertEqual("Adapt - Concept Mapper", driver.find_element_by_id("apptitle").text)
        self.assertEqual("Adaptation URL", driver.find_element_by_css_selector("h4").text)
        self.assertTrue(self.is_element_present(By.CSS_SELECTOR, "iframe"))
        # NOW REMOVE THE APP AND LOGOUT AGAIN
        driver.get(self.base_url + "/")
        driver.find_element_by_link_text("Use it!").click()
        driver.find_element_by_id("login").clear()
        driver.find_element_by_id("login").send_keys("admin")
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
