# coding: utf-8

# ## Nicehash Profitability Calculator Scripting
# 
# This notebook scrapes nicehash profitability calculator

from bs4 import BeautifulSoup
from selenium import webdriver
import re
import time
import pandas as pd
import datetime
import sys
import os
import errno


def get_profitability(devices=[], electricity="0.1", web_browser_driver=None):
    from selenium.webdriver.common.action_chains import ActionChains
    ndevices = len(devices)

    profit_list = []

    if not web_browser_driver:
        web_browser_driver = webdriver.Chrome()
        time.sleep(10)
        web_browser_driver.get("https://www.nicehash.com/profitability-calculator")
        time.sleep(5)

    if electricity != "0.1":
        from selenium.webdriver.common.keys import Keys

        electricity_costs = web_browser_driver.find_element_by_id("electricity")
        # change ELECTRICITY COSTS field
        (ActionChains(web_browser_driver)
         .move_to_element(electricity_costs)
         .click()
         .send_keys(Keys.BACKSPACE)
         .send_keys(Keys.BACKSPACE)
         .send_keys(Keys.BACKSPACE)
         .send_keys(electricity)
         .perform())
        # wait refresh
        time.sleep(10)

    i = 1
    # for print
    pre_status_length = 0
    for device in devices:
        # print status
        narrows = int(20 * i / ndevices)
        ndots = 20 - narrows
        progress_bars = "[" + ">" * narrows + "*" * ndots + str(i) + "/" + str(ndevices) + "]"
        status = "Retrieving " + device + progress_bars
        current_status_length = len(status)
        padding = str(pre_status_length) if pre_status_length > current_status_length else "0"
        status = ("{0:<" + padding + "}").format(status)
        print(status, end='\r')
        pre_status_length = len(status)

        # each time refresh website, elements need to be reselected
        # get select device menu element
        menu = web_browser_driver.find_element_by_css_selector("select")
        # get calculate button element
        calculate_button = web_browser_driver.find_element_by_css_selector("button")

        # select a device
        (ActionChains(web_browser_driver)
         .move_to_element(menu)
         .click(menu)
         .send_keys(device)
         .click()
         .perform())

        time.sleep(1)

        assert (web_browser_driver.current_url == "https://www.nicehash.com/profitability-calculator#" or
                web_browser_driver.current_url == "https://www.nicehash.com/profitability-calculator")

        # click Calculate button
        (ActionChains(web_browser_driver)
         .move_to_element(calculate_button)
         .click()
         .perform())

        # wait refresh
        time.sleep(10)
        current_url = web_browser_driver.current_url

        # parse current webpage to get profits
        bs = BeautifulSoup(web_browser_driver.page_source, 'html.parser')
        # get profit table data (the three rows except the header row)
        table_data_list = [re.sub("BTC|USD", "", tableData.get_text()).split() for tableData in
                           bs.select("table.light td")]
        profit = pd.DataFrame({"date": datetime.date.today(),
                               "device": device,
                               "electricity": electricity,
                               "time_range": ['day', "week", "month"],
                               "income_btc": [float(x[0]) for x in table_data_list[1:4]],
                               "income_usd": [float(x[1]) for x in table_data_list[1:4]],
                               "ei.costs_btc": [float(x[0]) for x in table_data_list[5:8]],
                               "ei.costs_usd": [float(x[1]) for x in table_data_list[5:8]],
                               "profit_btc": [float(x[0]) for x in table_data_list[9:]],
                               "profit_usd": [float(x[1]) for x in table_data_list[9:]],
                               "url": current_url})
        profit_list.append(profit)
        # print stats
        status = ("Retrieved " + str(device) + " data successfully, profit/day: "
                  + "[" + table_data_list[9][0] + ", " + table_data_list[9][1] + "] "
                  + progress_bars)
        # current status length
        current_status_length = len(status)
        # compute padding
        padding = str(pre_status_length) if pre_status_length > current_status_length else "0"
        # update status
        status = ("{0:<" + padding + "}").format(status)
        print(status, end='\r')
        pre_status_length = len(status)

        i = i + 1
        time.sleep(10)
    print(datetime.date.today(), ": ", ndevices, "tasks finished successfully")
    return pd.concat(profit_list, ignore_index=True)


if __name__ == "__main__":

    # Create the folder
    if not os.path.exists(os.path.abspath("./nicehash_profits/")):
        try:
            os.makedirs("./nicehash_profits/")
            print(os.path.dirname("./nicehash_profits/"), "folder created successfully")
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    date_last_update = datetime.date.today() - datetime.timedelta(1)
    while True:
        date_today = datetime.date.today()
        day_delta = (date_today - date_last_update).days

        if day_delta >= 1:

            # Scripting the select dropdown menu and get all supported devices
            chrome_driver = webdriver.Chrome()

            # wait chrome open
            time.sleep(10)

            chrome_driver.get("https://www.nicehash.com/profitability-calculator")
            # chrome_driver.refresh()
            # wait webpage refresh
            time.sleep(10)

            soup = BeautifulSoup(chrome_driver.page_source, 'html.parser')

            # beautifulsoup finds `select` div (the device dropdown list)
            # discard first item which is `select hardware`
            supported_device_strings = [d.get_text() for d in soup.find("select")][1:]

            data_retrieved_list = []
            if len(sys.argv) >= 2:
                for electricity_rate in sys.argv[1:]:
                    profits = get_profitability(supported_device_strings, electricity_rate, chrome_driver)
                    data_retrieved_list.append(profits)
            else:
                profits = get_profitability(supported_device_strings, web_browser_driver=chrome_driver)
                data_retrieved_list.append(profits)

            fileName = "./nicehash_profits/nicehash-profitabilities-" + str(date_today) + ".csv"
            data_retrieved = pd.concat(data_retrieved_list, ignore_index=True)
            data_retrieved.to_csv(fileName, index=False)
            date_last_update = date_today

            # Close Chrome
            chrome_driver.quit()
