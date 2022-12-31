# from random import random
#
# avg = 0
# sum = 0
# count = 0
# for i in range(100):
#     x = random() * 1000
#     sum += x
#     real_avg = sum / (count + 1)
#     avg = ((avg * count) + x) / (count + 1)
#     count += 1
#     delta = abs(avg - real_avg)
#     print(f"x:{x} real:{real_avg} avg:{avg} delta:{delta}")
#
# from tabulate import tabulate, SEPARATING_LINE
#
# mse_table = tabulate(
#     [
#         ["Mean-Squared Current Error", "∑ΔI² / N", "0.00000000000000000032486767" + " A²"],
#         ["Mean-Squared Voltage Error", "∑ΔV² / N", "0.00000000000000000000000019092038" + " V p.u.²"],
#         SEPARATING_LINE,
#         ["Mean-Absolute Current Error", "∑|ΔI| / N", "0.00000000021306265" + " A"],
#         ["Mean-Absolute Voltage Error", "∑|ΔV| / N", "0.000000000000341719" + " V p.u."]
#     ],
#     headers=["Summarizing Error", "Formula", "Value"],
#     tablefmt="mixed_outline"
#     #    tablefmt = "psql"
#
# )
#
# print(mse_table)
#

from tabulate import tabulate, SEPARATING_LINE

table = [["1", "one"],   # "1" as a str on purpose
         [1_000, "one K"],
         SEPARATING_LINE,
         [1_000_000, "one M"]]

print(tabulate(table, tablefmt="psql"))

expected = "\n".join(
    [
        "+---------+-------+",
        "|       1 | one   |",
        "|    1000 | one K |",
        "+---------+-------+",
        "| 1000000 | one M |",
        "+---------+-------+",
    ]
)
