# from urllib.request import urlopen
# import re
#
# def get_public_ip():
#     response = urlopen('http://checkip.dyndns.com/').read().decode('utf-8')
#     public_ip = re.search(r'Address: (\d+\.\d+\.\d+\.\d+)', response).group(1)
#     return public_ip
#
# print(f"Public IP Address: {get_public_ip()}")
