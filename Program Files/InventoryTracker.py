import time
import os

def CheckInventory(card):
    file_path1="Collection/Collection.txt"
    if not os.path.exists(file_path1):
        with open(file_path1,'w'):
            time.sleep(0.2)
    if os.path.exists(file_path1):
        with open(file_path1) as myfile:
            if card in myfile.read():
                print('Found card')
                return ("RejectCard")
            else:
                with open(file_path1,"a") as file1:
                    file1.write(card + "\n")
                    print('Not found, added to your collection list')
                    return (card)
