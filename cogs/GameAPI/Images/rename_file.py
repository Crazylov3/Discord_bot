# import os
# import random
# mapping = {}
# for i in ['A']+[f'{i}' for i in range(2,11)]+['J','Q','K']:
#     mapping[f"{i} nhep"] = f"{i} ♧"
#     mapping[f"{i} co"] = f"{i} ♡"
#     mapping[f"{i} ro"] = f"{i} ♢"
#     mapping[f"{i} bich"] = f"{i} ♤"
#
# for name in mapping.keys():
#     os.rename(f"{name}.png",f"{mapping[name]}.png")

# from PIL import Image
#
# def resize(path):
#     img = Image.open(path)
#     img = img.resize((200, 250), Image.ANTIALIAS)
#     img.save(path)
#
# for key in mapping.keys():
#     resize(mapping[key])
list_card = []
mapping_point = {}
for i in ['A'] + [f'{i}' for i in range(2, 11)] + ['J', 'Q', 'K']:
    list_card.extend([f"{i} ♧", f"{i} ♡", f"{i} ♤", f"{i} ♢"])
    if i.isdigit() and 3 <= int(i) <= 10:
        mapping_point[f"{i} ♧"] = int(i)
        mapping_point[f"{i} ♡"] = int(i)
        mapping_point[f"{i} ♢"] = int(i)
        mapping_point[f"{i} ♤"] = int(i)
    elif i == "A":
        mapping_point[f"{i} ♧"] = 14
        mapping_point[f"{i} ♡"] = 14
        mapping_point[f"{i} ♢"] = 14
        mapping_point[f"{i} ♤"] = 14
    elif i == "J":
        mapping_point[f"{i} ♧"] = 11
        mapping_point[f"{i} ♡"] = 11
        mapping_point[f"{i} ♢"] = 11
        mapping_point[f"{i} ♤"] = 11
    elif i == "Q":
        mapping_point[f"{i} ♧"] = 12
        mapping_point[f"{i} ♡"] = 12
        mapping_point[f"{i} ♢"] = 12
        mapping_point[f"{i} ♤"] = 12
    elif i == "K":
        mapping_point[f"{i} ♧"] = 13
        mapping_point[f"{i} ♡"] = 13
        mapping_point[f"{i} ♢"] = 13
        mapping_point[f"{i} ♤"] = 13
    else:
        mapping_point[f"{i} ♧"] = 15
        mapping_point[f"{i} ♡"] = 15
        mapping_point[f"{i} ♢"] = 15
        mapping_point[f"{i} ♤"] = 15
print(mapping_point)