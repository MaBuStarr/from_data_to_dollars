
def main():
    # import selenium so i can use a browser to access my seller central account
    from selenium import webdriver
    import credentials
    from tkinter import messagebox
    import bs4
    import pprint
    from dateutil.parser import parse
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    import time
    import pandas as pd
    import os
    import re

    def initialize_web_browswer(destop_path):
        from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
        # ***consider checking the system for any kind of browser that is available and installed, and then running that one***
        # start by opening up a chrome browser
        firefox_profile_without_download_box = webdriver. FirefoxProfile()
        firefox_profile_without_download_box.set_preference("browser.download.folderList", 2)
        firefox_profile_without_download_box.set_preference("browser.download.manager.showWhenStarting", False)
        firefox_profile_without_download_box.set_preference("browser.download.dir", destop_path)
        firefox_profile_without_download_box.set_preference("browser.helperApps.neverAsk.saveToDisk",
                               "text/plain,text/x-csv,text/csv,application/vnd.ms-excel,application/csv,application/x-csv,text/csv,text/comma-separated-values,text/x-comma-separated-values,text/tab-separated-values,application/pdf")

        browser = webdriver.Firefox(firefox_profile=firefox_profile_without_download_box)
        return browser
    def open_amazon_seller_site (browser):
        browser.get('https://sellercentral.amazon.com/')
        browser.find_element_by_id("sign-in-button").click()
    def amazon_seller_login (username, password):
        # *** consider just prompting the user with a tinker message box to click ok after they have entered their name and apssword ***
        # from tkinter import messagebox
        # messagebox.showinfo(title='username and password', message='Enter your username and password, then click OK.')
        time.sleep(2)
        username_field = browser.find_element_by_id("ap_email") # identify username field
        username_field.send_keys(username) # insert username into username field

        password_field = browser.find_element_by_id("ap_password") #identify password field
        password_field.send_keys(password) # insert password into password field

        browser.find_element_by_id("signInSubmit").click() #Click the sign-in button
    def check_for_2_step_verification():
        # ***2-step verification process here....***
        # several solutions possible here, but let's put up a diologue box to ask if the user has finished the 2 step varification
        # *** possible for webdriver to ask user for the 2-factor authenticion information and enter it itself *** #
        # *** consider using waitForElementPresent in the future to check if the webpage has been changed to what we need ***#
        messagebox.showinfo(title='2-step verification', message='Finish on screen 2-step verification, and then click OK.')
    def go_to_payment_screen():
        browser.get('https://sellercentral.amazon.com/payments/reports/statement/details?_encoding=UTF8&ref_=xx_payments_dnav_xx')
    def create_payment_history_dict():
        #look at code on payment screen
        html = browser.page_source
        example_soup = bs4.BeautifulSoup(html, 'html.parser')
        payment_reports_section = example_soup.find(id="groups")
        payment_dictionary = {}
        for statement_string in payment_reports_section:
            statement_open = False
            try:
                statement_date = statement_string.text.strip()
                if statement_date.endswith('(Open)'):
                    statement_open = True
                    # print('statement is Open')
                    statement_date = statement_date[:-7]
                # print('Statement date:', statement_date)


                statement_URL_extension = statement_string.attrs['value'].strip()
                # print('Statement URL Extension:', statement_URL_extension)

                statement_URL_full = "https://sellercentral.amazon.com/payments/reports/statement/details?_encoding=UTF8&ref_=myp_lsv_act_dropdown&groupId=" + statement_URL_extension
                # print('Statement URL statementURLFull:', statement_URL_full)

                if statement_open:
                    payment_dictionary[statement_date] = ['Open', statement_URL_extension, statement_URL_full]
                else:
                    payment_dictionary[statement_date] = ['Closed', statement_URL_extension, statement_URL_full]

            except:
                pass
        return payment_dictionary
    def _extract_payment_summary_from_payment_block(p_payment_block, payment_summary_dict):

        #loop through the payment blocks and split them apart by class names to find what we need
        for payment_block in p_payment_block:

            p_detail_blocks = payment_block.findAll(class_="pDetailBlock")

            #climbing down through the html to find the right detail_label (e.g. Beginning Balance, or Orders)
            for detail_block in p_detail_blocks:
                p_detail_label = detail_block.findAll(class_="pDetailLabel")
                p_detail_label = detail_block.find('a', class_="scui-inline-def-trigger")
                detail_label = p_detail_label.text.strip()
                # this label is important to keep track of.
                # multiple fields (pDetailLineKey)s have the same name, so need to designate which detail_label they are within
                # print('p_detail_label: ', detail_label)

                # all sub charges and payments are listed within class_="pDetailBreakdown"
                p_detail_breakdown = detail_block.findAll(class_="pDetailBreakdown")
                # print('length of detail breakdown:', len(p_detail_breakdown))

                # all sub charges and payments are listed on their own class_="pDetailLine" line
                p_detail_line = p_detail_breakdown[0].findAll(class_="pDetailLine")
                # print('length of detail line:', len(p_detail_line))
                dict_list = []

                #within p_detail_line, the name of the charge/payments are p_detail_key, the sum of the charge/payment is p_detail_value
                for detail_line in p_detail_line:
                    p_detail_key = detail_line.findAll(class_="a-declarative")
                    p_detail_value = detail_line.findAll(class_="pDetailLineValue")

                    if p_detail_key != []:
                        dict = {}
                        p_Summary_Label = p_detail_key[0].text.strip()
                        # print(key)
                        total_transfer_amount = p_detail_value[0].text.strip()
                        # print(value)

                        dict[p_Summary_Label] = total_transfer_amount
                        dict_list.append(dict)

                # print('payment_summary_dict', payment_summary_dict)
                payment_summary_dict[detail_label] = dict_list

            #for some reason the bottom block on the table is the only p_payment_block without <a class_="pDetailBlock"> section, so use this fact to identify it and extact the info
            if len(p_detail_blocks) == 0:
                p_detail_line_key = payment_block.findAll(class_="scui-inline-def-trigger")
                p_detail_line_value = payment_block.findAll(class_="pDetailLineValue")
                total_transfer_amount_html = p_detail_line_value
                # print('total_transfer_amount: ', total_transfer_amount_html)
                p_Summary_Label = p_detail_line_key[
                    0].text.strip()  # p_Summary_Label example includes: "Transfer amount initiated on May 5, 2020*"
                total_transfer_amount = total_transfer_amount_html[0].text.strip()  # e.g. $2,201.81
                # print('vparsealue: ', total_transfer_amount)

                # it may be best to break this key into 2 different keys: 1) Transfer amount initiated, and 2) Date Transfer initiated
                detail_label = "Transfer amount initiated"

                payment_summary_dict[detail_label] = total_transfer_amount

                # print('p_Summary_Label:')
                # print(p_Summary_Label)
                # print(p_Summary_Label[:-1]) #there is a '*' at the end of the date so let's remove that for parsing date

                transfer_date = parse(p_Summary_Label[:-1], fuzzy=True)  # extracts datetime object from p_Summary_Label
                payment_summary_dict[detail_label] = [{str(
                    transfer_date): total_transfer_amount}]  # putting this in brackets so it has the same format as the other entries. This simplifies subsequent loops.
        return payment_summary_dict
    def _send_payment_summary_to_df(payment_summary_dict):
        payment_report_df = pd.DataFrame()
        for detail_label in payment_summary_dict:
            if detail_label == "fund transfer number":
                column_name = 'fund_transfer_number'
                fund_transfer_number = str(payment_summary_dict[detail_label][0])
                # print(column_name + ': ' + fund_transfer_number)
                payment_report_df[column_name] = [fund_transfer_number]

            elif detail_label == "Transfer amount initiated":
                column_name = 'fund_transfer_datetime'
                fund_transfer_datetime = list(payment_summary_dict[detail_label][0].keys())[0]
                # print(column_name + ': ' + fund_transfer_datetime)
                payment_report_df[column_name] = [fund_transfer_datetime]

            else:
                # print('detail_label: ', detail_label)
                for thing in payment_summary_dict[detail_label]:
                    for detail_line_key, detail_line_value in thing.items():
                        detail_line_key = detail_line_key.lower().replace(' ', '_')
                        detail_label = detail_label.lower().replace(' ', '_')

                        column_name = str(detail_label) + '__' + str(detail_line_key)
                        # print(column_name + ':  ' + detail_line_value)
                        payment_report_df[column_name] = [detail_line_value]

        # print(payment_report_df.head(10))
        return payment_report_df
    def fill_master_payment_report_df(master_payment_report_df, payment_history_dict):
        # print('payment_history_dict', payment_history_dict)
        for payment in payment_history_dict:
            # check the log of payment histories and check for 'Closed' payments
            # 1) go to the closed payment pages and
            # 2) read their 'fund transfer number' and
            # 3) all other data that are contained within table
            if payment_history_dict[payment][0] == 'Closed':
                # 1) go to the closed payment pages
                browser.get(payment_history_dict[payment][2])
                html = browser.page_source
                example_soup = bs4.BeautifulSoup(html, 'html.parser')
                payment_reports_section = example_soup.find_all(class_="a-alert-content")

                # 2) read their 'fund transfer number'
                try:
                    fund_transfer_number = re.search('fund transfer: (\d+)', str(payment_reports_section), re.IGNORECASE)
                    # print("For date range:", payment + ", fund transfer number:", fund_transfer_number.group(1))
                except:
                    # print("For date range:", payment + ", No Transfer number found!")
                    fund_transfer_number = 'NaN'

                # 3) all other data that are contained within table
                # There is a lot of information to sort through on the  payment detail page******************

                # create a dictionary to store all of the payment summary information in
                payment_summary_dict = {}

                # read all html on closed payment page, store in example_soup
                html = browser.page_source
                example_soup = bs4.BeautifulSoup(html, 'html.parser')

                # All data is contained within <class = pPaymentBlock>, store that html in p_payment_block
                p_payment_block = example_soup.findAll(class_="pPaymentBlock")

                # create dictionary payment_summary_dict which contains relevent information extracted from p_payment_block
                payment_summary_dict = _extract_payment_summary_from_payment_block(p_payment_block, payment_summary_dict)

                # print('fund_transfer_number', fund_transfer_number)

                if fund_transfer_number == None:
                    payment_summary_dict['fund transfer number'] = [
                        fund_transfer_number]  # putting this in brackets so it has the same format as the other entries. This simplifies subsequent loops.
                else:
                    payment_summary_dict['fund transfer number'] = [fund_transfer_number.group(
                        1)]  # putting this in brackets so it has the same format as the other entries. This simplifies subsequent loops.

                # print(payment_summary_dict)

                #
                payment_report_df = _send_payment_summary_to_df(payment_summary_dict) # cleans data in payment_summary_dict and turns returns it for df formation
                master_payment_report_df = pd.concat([master_payment_report_df, payment_report_df], axis=0) # add data in payment_report_df to a new row in master_payment_report_df
                # print(master_payment_report_df.head(90))
        return (master_payment_report_df)
    def _get_earlist_closed_report_date(payment_history_dict):
        oldest_closed_date = datetime.now()  # initialize 'oldest date' as today. Oldest date will certainly come before today.
        print('this is the oldest date: ', oldest_closed_date)
        for list_range in payment_history_dict:
            for date in list_range.split(' - '):
                if (str(parse(date)) < str(oldest_closed_date)):
                    oldest_closed_date = str(parse(date))
        print('this is the new oldest date: ', oldest_closed_date)
        return oldest_closed_date
    def _get_most_recent_closed_report_date(payment_history_dict, oldest_closed_date):
        youngest_closed_date = oldest_closed_date # initialize 'youngest date' as the oldest. youngest date will certainly come before oldest.
        for list_range in payment_history_dict:
            if payment_history_dict[list_range][0] == 'Closed':
                for date in list_range.split(' - '):
                    if (str(parse(date)) > str(youngest_closed_date)):
                        youngest_closed_date = str(parse(date))
        print('this is the new youngest date: ', youngest_closed_date)
        return youngest_closed_date
    def get_report_date_ranges(payment_history_dict):
        oldest_closed_date = _get_earlist_closed_report_date(payment_history_dict)
        most_recent_report_date = _get_most_recent_closed_report_date(payment_history_dict, oldest_closed_date)
        # A list of all dates for which we have reports are contained in the key's of payment_history_dict
        # to find the total report range we need to find the earliest and latest dates contained in payment_history_dict

        return oldest_closed_date, most_recent_report_date
        pass
    def go_to_date_range_reports():
        browser.get('https://sellercentral.amazon.com/payments/reports/custom/request?tbla_daterangereportstable=sort:%7B%22sortOrder%22%3A%22DESCENDING%22%7D;search:undefined;pagination:1;')
    def _click_generate_report():
        browser.find_element_by_id("drrGenerateReportButton").click()  # Click the sign-in button
    def _month_day_year_parser(report_date):
        month = str(parse(report_date).month)
        day = str(parse(report_date).day)
        year = str(parse(report_date).year)

        return month, day, year
    def _generate_one_date_rage_report(from_report_date, to_report_date ):
        time.sleep(2)
        _click_generate_report()
        time.sleep(2)

        browser.find_element_by_id("drrReportRangeTypeRadioCustom").click()

        # insert a 'from' (starting) date for the custom report
        from_date_field = browser.find_element_by_id("drrFromDate")  # identify username field
        browser.find_element_by_id('drrFromDate').clear()
        # report format is MM/DD/YY
        from_report_date_month, from_report_date_day, from_report_date_year = _month_day_year_parser(from_report_date)
        from_date_field.send_keys(from_report_date_month + '/' + from_report_date_day + '/' + from_report_date_year)

        # insert a 'to' (ending) date for the custom report
        to_report_date_month, to_report_date_day, to_report_date_year = _month_day_year_parser(to_report_date)
        to_date_field = browser.find_element_by_id("drrToDate")  # identify username field
        browser.find_element_by_id('drrToDate').clear()
        to_date_field.send_keys(to_report_date_month + '/' + to_report_date_day + '/' + to_report_date_year)

        # Click the generate report button
        browser.find_element_by_id("drrGenerateReportsGenerateButton").click()  # Click the generate report button
    def _generate_YYYYMMMDD_date_label(from_report_date, to_report_date):
        just_from_date_YYYY_MM_DD = from_report_date.split()[0]
        print('just_to_date_YYYY-MM-DD:', just_from_date_YYYY_MM_DD)
        from_date_object = datetime.strptime(just_from_date_YYYY_MM_DD, '%Y-%m-%d')
        from_date_object = from_date_object.strftime('%Y%b%#d')
        print(from_date_object)

        just_to_date_YYYY_MM_DD = to_report_date.split()[0]
        print('just_to_date_YYYY-MM-DD:', just_to_date_YYYY_MM_DD)
        to_date_object = datetime.strptime(just_to_date_YYYY_MM_DD, '%Y-%m-%d')
        to_date_object = to_date_object.strftime('%Y%b%#d')
        print(to_date_object)

        report_date_span = str(from_date_object) + '-' + str(to_date_object)
        print('report_date_span: ', report_date_span)
        print('putting this date in the dictionary: ', report_date_span)
        return report_date_span
        pass
    def generate_all_reports(oldest_closed_date, most_recent_report_date):
        print('oldest_closed_date:', oldest_closed_date)
        print('most_recent_report_date:', most_recent_report_date)

        # to indentify all reports generated, we will eventually need to identify the reports by YYYYM-YYYYM ('2020Apr8-2020Apr9')
        # date_range_report_dict_YYYYM will be used to store those date ranges
        date_range_report_dict_YYYYMD = {'report_not_yet_downloaded':[], 'report_downloaded':[]}

        # Amazon custom report generator uses the terminology "from date" to mean the start date of the report, and "to date" to mean the ending date.
        from_report_date = oldest_closed_date
        from_report_date_plus_1_year = str(parse(from_report_date) + relativedelta(years=1))

        while (from_report_date_plus_1_year < most_recent_report_date):
            to_report_date = from_report_date_plus_1_year

            print('this is the from_report_date:', from_report_date)
            print('this is the to_report_date1:', to_report_date)

            report_date_span = _generate_YYYYMMMDD_date_label(from_report_date, to_report_date)
            date_range_report_dict_YYYYMD['report_not_yet_downloaded'].append(report_date_span)

            _generate_one_date_rage_report(from_report_date, to_report_date)
            time.sleep(2)

            #while ending date is < last report date, run loop: take first date, add a year, get final report date, generate report.
            from_report_date = str(parse(to_report_date) + relativedelta(days=1))
            from_report_date_plus_1_year = str(parse(from_report_date) + relativedelta(years=1))

        to_report_date = most_recent_report_date
        _generate_one_date_rage_report(from_report_date, to_report_date)
        report_date_span = _generate_YYYYMMMDD_date_label(from_report_date, to_report_date)
        date_range_report_dict_YYYYMD['report_not_yet_downloaded'].append(report_date_span)
        # print('this is what is in dictionary now:', date_range_report_dict_YYYYMD)

        return date_range_report_dict_YYYYMD
    def _click_all_date_rage_report_refresh_buttons():
        # check to see if any 'refresh' report buttons are present
        # click these 'refresh' buttons until there are none left
        while True:
            try:
                print('waiting 5 seconds for reports to become available, then clicking "refresh"')
                time.sleep(5)
                get_refresh = browser.find_element_by_xpath("//a[@class='drrRefreshTable'][contains(@href, 'javascript:void(0)')]")
                get_refresh.click()
            except:
                break
    def _click_all_date_rage_report_download_buttons(date_range_report_dict_YYYYMD):
        # download every date range report with date ranges contained in date_range_report_dict_YYYYMD
        for report_date_range in date_range_report_dict_YYYYMD['report_not_yet_downloaded']:
            # now that all reports are loaded, loop through a list of report-date ranges and click 'download' on those reports
            get_div = browser.find_element_by_xpath("//a[@class='a-button-text'][contains(@href, '"+report_date_range+"')]")
            # print(get_div)
            print('going to press this button in 1 seconds')
            time.sleep(1)
            get_div.click()
            print('downloaded date_rage_report:', report_date_range)
    def download_custom_transaction_reports(date_range_report_dict_YYYYMD):
        # check to see if any 'refresh' report buttons are present
        # click these 'refresh' buttons until there are none left
        _click_all_date_rage_report_refresh_buttons()
        # download every date range report with date ranges contained in date_range_report_dict_YYYYMD
        _click_all_date_rage_report_download_buttons(date_range_report_dict_YYYYMD)
    def list_of_custom_transaction_report_file_paths(destop_path):
        # return a list of files in directory desktop_path
        directory = destop_path # directory name originally provided for dumping Amazon CSV files into
        list_of_custom_transaction_report_file_names = os.scandir(directory) # list of file names in directory
        list_of_custom_transaction_report_file_paths = [] #intialize an empty list for collecting file path names

        for file_name in list_of_custom_transaction_report_file_names:
            # print('file_name: ', file_name.name)
            if file_name.name != file_name_for_aggregated_dfs:
                path_name = destop_path + '\\' + file_name.name
                list_of_custom_transaction_report_file_paths.append(path_name)
        return list_of_custom_transaction_report_file_paths
    def assemble_master_dataframe(list_of_custom_transaction_report_file_paths):
        df_list = []
        for file_path in list_of_custom_transaction_report_file_paths:
            # print('file_path: ', file_path)
            df = pd.read_csv(file_path, header=7)
            df = df.set_index('date/time')
            # print(df.head(10))
            df_list.append(df)
        master_df = pd.concat(df_list, axis=0)
        # master_df = master_df.set_index('date/time')  # set index to 'date/time' as this likely will be the thing we reference from other reports
        master_df.to_csv(desktop_folder_path + file_name_for_aggregated_date_range_reports)

        return master_df


    desktop_folder_name = 'Amazon_Seller_Reports'
    desktop_folder_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop', desktop_folder_name)
    # desktop_folder_path = "C:\\Users\\mbsta\\Desktop\\Amazon_Seller_Reports"
    file_name_for_aggregated_date_range_reports = '\\all_closed_date_range_reports_data.csv'
    file_name_for_aggregated_dfs = 'master_payment_report_df.csv'

    # we will be downloading amazon sales files to destop_path from the web,
    browser = initialize_web_browswer(desktop_folder_path)
    open_amazon_seller_site(browser)
    username = str(credentials.username) # pull username from credentials file
    password = str(credentials.password) # pull password from credentials file
    amazon_seller_login(username, password) # enter login information
    check_for_2_step_verification() # user confirmation that they have entered their 2-step verification
    go_to_payment_screen() # go to payment reports page
    payment_history_dict  = create_payment_history_dict() # extract information (urls) from payment reports page about what payment reports exist that are open (present) and closed (past).

    # we will be extracting all aggreggated payment report information present on the webpage so we can compare it to sales data we gather later.
    master_payment_report_df = pd.DataFrame() # create a dataframe 'master_payment_report_df' to organize payment information
    master_payment_report_df = fill_master_payment_report_df(master_payment_report_df, payment_history_dict) # fill 'master_payment_report_df' with payment info extracted from each payment report page

    master_payment_report_df = master_payment_report_df.set_index('fund_transfer_datetime') #set index to fund_transfer_datetime as this will always appear and be unique on a payment statement
    master_payment_report_df.to_csv(desktop_folder_path + file_name_for_aggregated_dfs)
    print('created ' + file_name_for_aggregated_dfs + '  in folder')

    pp.pprint(payment_history_dict)
    oldest_closed_date, most_recent_report_date = get_report_date_ranges(payment_history_dict)
    go_to_date_range_reports()
    date_range_report_dict_YYYYMD = generate_all_reports(oldest_closed_date, most_recent_report_date)
    download_custom_transaction_reports(date_range_report_dict_YYYYMD)
    list_of_custom_transaction_report_file_paths = list_of_custom_transaction_report_file_paths(desktop_folder_path)
    master_df = assemble_master_dataframe(list_of_custom_transaction_report_file_paths)


if __name__ == "__main__":
    main()