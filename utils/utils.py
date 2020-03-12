def convert_upgrade_levels(mult_lvl, money_lvl, crit_lvl):
    mult = 100 + mult_lvl * 5
    money = money_lvl + money_lvl * 2 + 2
    crit = round(crit_lvl * 1.5)
    return mult, money, crit
