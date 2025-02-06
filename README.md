This script connects to you camera, finds a card shape, hashes it, and attempts to identify the card.
As an additial effort it will also try to read the card name and mana cost and compare it to similarities within the perceptual hash identification

Edit the config for for your particular need, you may have to edit some other variables in other scripts for your needs

This script is written for my personal machine once it identifies the card all it does is send the variable requested to Arduino but could be easily adapted to whatever machine you may be using over USB

If you wish to contribute to the identification I am open to contributors

You will also need the default-cards json file from scryfall.com and mana_v14.pt which you can download from https://www.dropbox.com/scl/fi/yx0w944iium3tbhto8v28/mana_v14.pt?rlkey=45a20t9p3imsxh6srms1c867t&st=e511d907

Note: This script works pretty well now, but it can still make mistakes. I will continue to make the code as accurate as I can and upload major breakthroughs
