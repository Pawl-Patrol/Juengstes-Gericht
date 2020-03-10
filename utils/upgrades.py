def convert_upgrade_levels(mult_lvl, money_lvl, income_lvl, crit_lvl, power_lvl):
    mult = 100 + mult_lvl * 5
    money = money_lvl + money_lvl * 2 + 2
    income = round(income_lvl * 1.5)
    crit = round(crit_lvl * 1.5)
    power = power_lvl * power_lvl + power_lvl * 10
    return mult, money, income, crit, power

def get_upgrade_price(mult_lvl=0, money_lvl=0, income_lvl=0, crit_lvl=0, power_lvl=0):
    if mult_lvl:
        return (mult_lvl * mult_lvl + mult_lvl) * 100
    if money_lvl:
        return money_lvl * 850
    if income_lvl:
        return (income_lvl * income_lvl + income_lvl) * 150 + 500
    if crit_lvl:
        return crit_lvl * 455
    if power_lvl:
        return power_lvl * 560