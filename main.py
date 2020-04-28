#!/usr/bin/env python3
#
# Name: gAnswers - v1.2
# Author: Nick L (c64-dev@github)
# 
# A voice controlled desktop assistant providing answers to
# various queries, by scraping Google's webpage results and 
# reformatting it as a notification snippet for the user.


import os
import sys
import requests
import base64
import psutil
import speech_recognition as sr
from bs4 import BeautifulSoup
from plyer import notification
from psutil import NoSuchProcess
from pynput.keyboard import GlobalHotKeys
from subprocess import call
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as cond
from selenium.common.exceptions import TimeoutException


# Define basic program parameters
actKey = "<f9>"  # Action hotkey
escKey = "<shift>+<esc>"  # Exit hotkey
searchEngine = "https://www.google.com/search?hl=en&q="  # Search url
defIcon = os.path.realpath("./") + "/images/status.png"  # Default image
resIcon = os.path.realpath("./") + "/images/decoded_image.jpg"  # Decoded image


def gAnswers():
    cl = Helpers()
    global soup, text

    response = cl.listen()
    try:
        notification.notify(
            title="How can I help you?",
            message=response,
            app_icon=defIcon,
            timeout=5,
        )
        cl.browser.get(searchEngine + response)
    except TypeError:
        # Tidy up (Notify user, mute input, kill leftover processes and exit)
        print("Exiting program.")
        cl.mic("off")
        cl.kill_proc()
        sys.exit(0)

    try:
        WebDriverWait(cl.browser, 5).until(
            cond.presence_of_element_located((By.ID, "search"))
        )
        page_source = cl.browser.page_source
        soup = BeautifulSoup(page_source, "lxml")

        # Soup recipes
        recipe0 = soup.find("div", id="main").find(
            attrs={"data-tts": "answers"}
        )
        recipe1 = soup.find("div", id="main").find(
            attrs={"data-attrid": "wa:/description"}
        )
        recipe2 = soup.find("div", id="main").find("div", class_="kp-rgc")
        recipe3 = soup.find("div", class_="kno-rdesc")
        recipe4 = soup.find("div", class_="kp-header")
        recipe5 = soup.find("div", id="main").find(attrs={"data-md": "83"})

        if recipe0 and recipe1:
            text = (
                recipe0.get_text().strip()
                + ". "
                + recipe1.span.get_text().strip()
            )
        elif recipe0:
            text = recipe0.get_text().strip()
        elif recipe1:
            text = recipe1.span.get_text().strip()
        elif recipe2:
            text = recipe2.get_text().strip()
        elif recipe3:
            text = recipe3.get_text().replace("Description", "", 1)
        elif recipe4:
            text = recipe4.get_text().strip()
        elif recipe5:
            text = recipe5.get_text().strip()
        else:
            text = "I can't find anything relevant. Can you be more specific?"
    except TimeoutException:
        # Tidy up (Notify user, mute input, kill leftover processes and exit)
        notification.notify(
            title="Program error.",
            message="<i>Unable to parse webpage. Exiting program.</i>",
            app_icon=defIcon,
            timeout=4,
        )
        cl.mic("off")
        cl.kill_proc()
        sys.exit(0)

    cl.browser.quit()
    cl.results()


class Helpers:
    # Initialize browser
    def __init__(self):
        self.opts = webdriver.ChromeOptions()
        self.opts.add_argument("--headless")
        self.browser = webdriver.Chrome(chrome_options=self.opts)

    # Set up hotkey listener events
    def hotkeyInit(self):
        cl = Helpers()
        notification.notify(
            title="Assistant ready.",
            message="<i>Press hotkey to activate voice recognition.</i>",
            app_icon=defIcon,
            timeout=3,
        )

        try:
            with GlobalHotKeys(
                {actKey: cl.on_activate_act, escKey: cl.on_activate_esc}
            ) as h:
                h.join()
        except TypeError:
            # Tidy up (kill leftover procs, exit)
            cl.kill_proc()
            sys.exit(0)

    def on_activate_act(self):
        gAnswers()

    def on_activate_esc(self):
        notification.notify(
            title="Assistant deactivated.",
            message="<i>Terminating processes and exiting program.</i>",
            app_icon=defIcon,
            timeout=3,
        )
        cl = Helpers()
        cl.kill_proc()
        sys.exit(0)

    # Check for old processes and clean up
    def kill_proc(self):
        for proc in psutil.process_iter():
            try:

                if any(procstr in proc.name() for procstr in [
                    "chromium-browse", "chromium-browser", "google-chrome"
                ]):
                    # print(f"Cleaning up {proc.name()}") # For debug only
                    proc.kill()
            except NoSuchProcess:
                return False

    # Toggle input source on/off (only for Linux at the moment)
    def mic(self, toggle):
        activate = ["amixer", "set", "Capture", "cap"]
        deactivate = ["amixer", "set", "Capture", "nocap"]
        return call(activate) if toggle == "on" else call(deactivate)

    # Voice recognition routine
    def listen(self):
        cl.mic("on")  # Turn on input source

        rec = sr.Recognizer()
        microphone = sr.Microphone()

        with microphone as source:
            rec.pause_threshold = 0.6
            rec.energy_threshold = 4000
            rec.dynamic_energy_threshold = True
            rec.adjust_for_ambient_noise(source, duration=1)

            try:
                notification.notify(
                    title="How can I help you?",
                    message="<i>Listening...</i>",
                    app_icon=defIcon,
                    timeout=4,
                )
                voice = rec.listen(source, timeout=10)  # Recording audio
                parsedText = rec.recognize_google(voice)  # Recognizing audio
                cl.mic("off")  # Done with listening. Turn off input source.
                return parsedText.capitalize()
            except sr.WaitTimeoutError:
                notification.notify(
                    title="Response timeout.",
                    message="<i>Check that microphone source is active.</i>",
                    app_icon=defIcon,
                    timeout=4,
                )
                cl.browser.quit()
                cl.mic("off")
                cl.hotkeyInit()
            except sr.UnknownValueError:
                notification.notify(
                    title="Response unclear.",
                    message="<i>Could not understand audio. "
                    + "Please try again.</i>",
                    app_icon=defIcon,
                    timeout=4,
                )
                cl.browser.quit()
                cl.mic("off")
                cl.hotkeyInit()
            except sr.RequestError:
                # Tidy up (Notify user, mute input, kill leftovers and exit)
                notification.notify(
                    title="Program error.",
                    message="<i>Could not contact Speech Services. "
                    + "Exiting program.</i>",
                    app_icon=defIcon,
                    timeout=4,
                )
                cl.mic("off")
                cl.kill_proc()
                sys.exit(0)

    # Decode image and serve results.
    def results(self):
        try:
            image = str(soup.find("div", class_="birrg").find("g-img")).split(
                "base64,"
            )
        except AttributeError:
            image = ""

        if image != "":
            try:
                image = image[1].split('"')
                base64_img = image[0]
                base64_img_bytes = base64_img.encode("utf-8")
                with open(resIcon, "wb") as file_to_save:
                    decoded_image_data = base64.decodebytes(base64_img_bytes)
                    file_to_save.write(decoded_image_data)
                notification.notify(
                    title="Here is what I found.",
                    message=text[:254] + text[254:],
                    app_icon=resIcon,
                )
            except IndexError:
                altUrl = image[0].split("src=")
                altUrl = altUrl[1].split('"')
                altUrl = altUrl[1]
                r = requests.get(altUrl, allow_redirects=True)
                open(resIcon, "wb").write(r.content)
                notification.notify(
                    title="Here is what I found.",
                    message=text[:254] + text[254:],
                    app_icon=resIcon,
                )
        else:
            notification.notify(
                title="Here is what I found.",
                message=text[:254] + text[254:],
                app_icon=defIcon,
            )


# ENTRY POINT #
if __name__ == "__main__":
    cl = Helpers()
    cl.hotkeyInit()
