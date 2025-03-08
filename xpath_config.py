"""
XPATH配置文件
用于集中管理所有XPATH路径
修改XPATH时只需要在此文件中更新对应的值
"""

class XPathConfig:
    # 1.登录相关，长期有效
    LOGIN_BUTTON = [
        '//button[contains(text(), "Log In")]',
        '//button[@class="c-gBrBnR c-gBrBnR-gDWzxt-variant-primary c-gBrBnR-bxvuTL-fontWeight-medium c-gBrBnR-dRRWyf-fontSize-md c-gBrBnR-gFoOfa-cv c-gBrBnR-ikLDqfK-css"]',
        '//*[@id="__pm_viewport"]/nav[1]/div[1]/div[3]/div/nav/div/ul/div[1]/div/button'
    ]
    # 2.Metamask相关，长期有效
    METAMASK_BUTTON = [
        '//*[@id="authentication-modal"]/div/div[2]/div/div/div/div/div[3]/button[1]'
    ]

    # 3.Buy按钮
    BUY_BUTTON = [
        '//button[(text()="Buy")]', # 长期有效
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[1]/div/div/button[1]'
    ]

    # 4.Buy Yes 按钮
    BUY_YES_BUTTON = [
        '//button[.//span[contains(text(), "Yes")] and .//span[contains(text(), "¢")]]',# 长期有效
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[2]/div[1]/span[1]/button'
    ]

    # 5.Buy No 按钮
    BUY_NO_BUTTON = [
        '//button[.//span[contains(text(), "No")] and .//span[contains(text(), "¢")]]',# 长期有效
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[2]/div[1]/span[2]/button'
    ]

    # 6.Sell Yes 按钮
    SELL_YES_BUTTON = [
        '//button[.//span[contains(text(), "Yes")] and .//span[contains(text(), "¢")]]',# 长期有效
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[2]/div[1]/span[1]/button',
        'button.c-bDcLpV c-bDcLpV-jwKyHk-color-gray c-bDcLpV-ijBXsHa-css'
    ]

    # 7.Sell No 按钮
    SELL_NO_BUTTON = [
        '//button[.//span[contains(text(), "No")] and .//span[contains(text(), "¢")]]',# 长期有效
        'button.c-bDcLpV c-bDcLpV-kTZFjb-color-red c-bDcLpV-ijBXsHa-css'
    ]

    # 8.Buy-确认买入按钮
    BUY_CONFIRM_BUTTON = [
        '//button[@class="c-bDcLpV c-bDcLpV-fLyPyt-color-blue c-bDcLpV-ileGDsu-css"]',
        '//button[.//span[contains(text(), "B")] and .//span[contains(text(), "u")] and .//span[contains(text(), "y")] and .//span[contains(text(), "Y")] and .//span[contains(text(), "e")] and .//span[contains(text(), "s")]]',
        '//button[.//span[contains(text(), "B")] and .//span[contains(text(), "u")] and .//span[contains(text(), "y")] and .//span[contains(text(), "N")] and .//span[contains(text(), "o")]',
        '//button[contains(text(), "Buy Yes") or contains(text(), "Buy No")]',
        '//button[contains(text(), "Buy" and contains(text(), "Yes")) or contains(text(), "Buy" and contains(text(), "No"))]'
    ]

    # 9.Sell-卖出按钮
    SELL_PROFIT_BUTTON = [
        '//button[@class="c-bDcLpV c-bDcLpV-fLyPyt-color-blue c-bDcLpV-ileGDsu-css"]',
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[3]/div[2]/div/span/button',
        '//button[.//span[contains(text(), "S")] and .//span[contains(text(), "e")] and .//span[contains(text(), "l")] and .//span[contains(text(), "l")]and .//span[contains(text(), "N")] and .//span[contains(text(), "o")]',
        '//button[.//span[contains(text(), "S")] and .//span[contains(text(), "e")] and .//span[contains(text(), "l")] and .//span[contains(text(), "l")] and .//span[contains(text(), "Y")] and .//span[contains(text(), "e")] and .//span[contains(text(), "s")]]',
        '//button[contains(text(), "Sell Yes") or contains(text(), "Sell No")]',
        '//button[contains(text(), "Sell" and contains(text(), "Yes")) or contains(text(), "Sell" and contains(text(), "No"))]'
    ]

    # 10.Amount输入框
    AMOUNT_INPUT = [
        '//input[@id="market-order-amount-input"]',
        '//p[text()="Amount"]/ancestor::div//input[@placeholder="$0"]',# 长期有效
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[3]/div/div/div/div/div[1]/div/div[1]/div[2]/div/div/input'
    ]

    # 11.Position-Yes标签
    POSITION_YES_LABEL = [
        '//div[text()="Yes"]',# 长期有效
        '//div[@class="c-dhzjXW c-chKWaB c-chKWaB-eVTycx-color-green c-dhzjXW-ibxvuTL-css" and text()="Yes"]'
    ]

    # 12.Position-No标签
    POSITION_NO_LABEL = [
        '//div[text()="No"]',# 长期有效
        '//div[@class="c-dhzjXW c-chKWaB c-chKWaB-kNNGp-color-red c-dhzjXW-ibxvuTL-css" and text()="No"]'
    ]

    # 13.Position-Yes值
    POSITION_YES_VALUE = [
        '(//span[@class="c-PJLV c-dnafHo"])[1]',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div/div/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[1]/td[4]/span[2]',
        '//*[@id="event-detail-container"]/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[1]/td[4]/span[2]'
    ]

    # 14.Position-No值
    POSITION_NO_VALUE = [
        '(//span[@class="c-PJLV c-dnafHo"])[2]',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div/div/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[2]/td[4]/span[2]',
        '//*[@id="event-detail-container"]/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[2]/td[4]/span[2]'
    ]

    # 15.Position-Sell按钮
    POSITION_SELL_BUTTON = [
        '//button[@class="c-gBrBnR c-gBrBnR-iifsICY-css"]',# 长期有效
        '//td//div//button[text()="Sell"]', # 长期有效
    ]

    # 16.Position-Sell Yes按钮
    POSITION_SELL_YES_BUTTON = [
        '(//button[@class="c-gBrBnR c-gBrBnR-iifsICY-css"])[1]',# 长期有效
        '(//td//div//button[text()="Sell"])[1]'
        ]

    # 17.Position-Sell No按钮
    POSITION_SELL_NO_BUTTON = [
        '(//button[@class="c-gBrBnR c-gBrBnR-iifsICY-css"])[2]',# 长期有效
        '(//td//div//button[text()="Sell"])[2]'
        ]

    # 18.Portfolio值
    PORTFOLIO_VALUE = [
        '(//span[@class="c-PJLV c-jaFKlk c-PJLV-ibdakYG-css"])[1]',# 长期有效
        '//a[@href="/portfolio"]//span[contains(text(), "$")]' # 长期有效
    ]

    # 19.Cash值
    CASH_VALUE = [
        '(//span[@class="c-PJLV c-jaFKlk c-PJLV-ibdakYG-css"])[2]',# 长期有效
        '//button[.//span[text()="Cash"]]/span[contains(text(), "$")]', # 长期有效
        '/html/body/div[1]/div[2]/nav[1]/div[1]/div[3]/div/nav/div/ul/div[1]/button[1]/span[1]',
        '//*[@id="__pm_viewport"]/nav[1]/div[1]/div[3]/div/nav/div/ul/div[1]/button[1]/span[1]'
    ]

    # 20.History-交易记录
    HISTORY = [
        '(//div[@class="PJLV PJLV-ihovmxi-css"])[1]',# 长期有效
        '(//div[@class="PJLV PJLV-ihovmxi-css"]//p)[1]', # 长期有效
        '//*[@id="event-detail-container"]/div/div[3]/div/div[5]/div/div[2]/div/p',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div/div/div/div[3]/div/div[5]/div/div[2]/div/p'  
    ]
    
    # 21.搜索框
    SEARCH_INPUT = [
        '//input[@id="markets-grid-search-input"]',# 长期有效
        '/html/body/div[1]/div[2]/div/div/main/div/div/div[3]/div/div/div/div[1]/div[2]/div[2]/input',
        'input#markets-grid-search-input',
        'input[placeholder="Search by market"]'
    ] 

    # 22.Portfolio_button
    PORTFOLIO_BUTTON = [
        '//a[@href="/portfolio"]' # 长期有效
    ]