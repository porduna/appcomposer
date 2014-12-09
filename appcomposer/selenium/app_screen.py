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


class AppScreen(unittest.TestCase):
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
    
    def test_app_screen(self):
        driver = self.driver
        try:
            driver.get(self.base_url + "/")
            driver.find_element_by_link_text("Use it!").click()
            driver.find_element_by_id("login").clear()
            driver.find_element_by_id("login").send_keys("admin")
            driver.find_element_by_id("password").clear()
            driver.find_element_by_id("password").send_keys("password")
            driver.find_element_by_xpath("//button[@type='submit']").click()
            driver.find_element_by_link_text(u"Start composing »").click()
            driver.find_element_by_name("name").clear()
            driver.find_element_by_name("name").send_keys("dummy1")
            driver.find_element_by_css_selector("input.btn.btn-primary").click()
            driver.find_element_by_name("saveexit").click()
            self.assertEqual("Apps - User Profile", driver.title)
            driver.find_element_by_link_text("Home").click()
            driver.find_element_by_link_text(u"Start composing »").click()
            driver.find_element_by_name("name").clear()
            driver.find_element_by_name("name").send_keys("dummy2")
            driver.find_element_by_css_selector("input.btn.btn-primary").click()
            driver.find_element_by_name("saveexit").click()
            self.assertEqual("Apps - User Profile", driver.title)

            self.assertEqual("dummy1", driver.find_elements_by_css_selector(".app-title")[1].text)
            self.assertEqual("dummy2", driver.find_elements_by_css_selector(".app-title")[0].text)
            driver.find_element_by_link_text("Translate").click()
            for i in range(60):
                try:
                    if self.is_element_present(By.CSS_SELECTOR, "p.p1"): break
                except: pass
                time.sleep(1)
            else: self.fail("time out")
            time.sleep(2)
            driver.find_element_by_css_selector("p.p1").click()
            driver.find_element_by_id("sendurlbtn").click()
            driver.find_element_by_link_text("Apps").click()
            self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-success > div > h3").text)
            self.assertEqual("dummy2", driver.find_elements_by_css_selector(".app-title")[1].text)
            self.assertEqual("dummy1", driver.find_elements_by_css_selector(".app-title")[2].text)
            self.assertEqual("Composer: translate", driver.find_element_by_css_selector(".app-composer-type").text)
            self.assertEqual("Open", driver.find_element_by_link_text("Open").text)
            self.assertEqual("Open", driver.find_element_by_xpath("(//a[contains(text(),'Open')])[2]").text)
            self.assertEqual("Open", driver.find_element_by_xpath("(//a[contains(text(),'Open')])[3]").text)
            driver.find_element_by_id("search_box").send_keys("map")
            self.assertEqual("Open", driver.find_element_by_link_text("Open").text)
            self.assertFalse(driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-info > div > h3").is_displayed())
            driver.find_element_by_id("search_box").clear()

            # MODIFICATION/FIX: In Python empty send_keys does not raise a javascript event. So I put a space and delete
            # it.
            driver.find_element_by_id("search_box").send_keys(" ")
            driver.find_element_by_id("search_box").send_keys(Keys.BACKSPACE)


            self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-success > div > h3").text)
            self.assertEqual("dummy2", driver.find_elements_by_css_selector(".app-title")[1].text)
            self.assertEqual("dummy1", driver.find_elements_by_css_selector(".app-title")[2].text)

            self.assertEqual("Translate", driver.find_element_by_css_selector("h3").text)
            self.assertEqual("Adapt", driver.find_element_by_css_selector("div.alert.alert-info > div > h3").text)
            driver.find_element_by_link_text("TRANSLATE").click()
            self.assertEqual("App Composer :: Translation tool", driver.title)
            driver.find_element_by_link_text("Apps").click()
            driver.find_element_by_link_text("ADAPT").click()
            self.assertEqual("App Composer :: Choose an App to adapt", driver.title)
            driver.find_element_by_link_text("Home").click()
            driver.find_element_by_link_text("Apps").click()
            self.assertEqual("Apps - User Profile", driver.title)
            self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-success > div > h3").text)
            driver.find_element_by_id("search_box").clear()
            driver.find_element_by_id("search_box").send_keys("translate")
            self.assertEqual("Concept Mapper", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-success > div > h3").text)
            driver.find_element_by_link_text("Apps").click()
            driver.find_element_by_link_text("Delete").click()
            driver.find_element_by_name("delete").click()
            driver.find_element_by_xpath("(//a[contains(text(),'Delete')])[2]").click()
            driver.find_element_by_name("delete").click()
            driver.find_element_by_link_text("Delete").click()
            driver.find_element_by_name("delete").click()
            driver.find_element_by_link_text("ADAPT").click()
            driver.find_element_by_css_selector("td.sorting_1").click()
            driver.find_element_by_id("sendurlbtn").click()
            driver.find_element_by_css_selector("input.btn.btn-primary").click()
            driver.find_element_by_css_selector("input.btn.btn-success").click()
            driver.find_element_by_link_text("Apps").click()
            driver.find_element_by_link_text("Duplicate").click()
            self.assertEqual("Duplication of an application", driver.find_element_by_css_selector("h2").text)
            self.assertEqual("Concept Mapper (2)", driver.find_element_by_id("name").get_attribute("value"))
            driver.find_element_by_css_selector("button.btn").click()
            driver.find_element_by_link_text("Apps").click()
            self.assertEqual("Concept Mapper (2)", driver.find_element_by_css_selector("div.row > div.row > div.app > div.alert.alert-info > div > h3").text)
            self.assertEqual("Concept Mapper", driver.find_element_by_xpath("//div[2]/div[2]/div/div/h3").text)
            driver.find_element_by_link_text("Delete").click()
            driver.find_element_by_name("delete").click()
            driver.find_element_by_link_text("Delete").click()
            driver.find_element_by_name("delete").click()
            self.assertEqual("No application.", driver.find_element_by_css_selector("h2").text)
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
