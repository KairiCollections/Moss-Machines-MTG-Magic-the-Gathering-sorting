This script connects to your camera, finds a card shape, hashes it and attempts to identify the card.
As an additional effort it will also try to read the card name and compare it to similarities within the perceptual hash identification. Edit the config for for your particular need, you may have to edit some other variables in other scripts for your needs. Once it identifies the card all it does is send the variable requested to Arduino via a serial connection but could be easily adapted to whatever machine you may be using over USB or piping it to some other script

You will also need the default-cards json file from scryfall.com

Note: This script works pretty well now, but it can still make mistakes. I will continue to make the code as accurate as I can and upload major breakthroughs. If you wish to contribute to the identification script I am open to contributors

By default connection to Ardiuno is off and so is send_to_Ardiuno, uncomment to enable

	3D Construction - https://www.tinkercad.com/things/8l4ww8YQsPP-construction?sharecode=WEaZcndq0rZ0zSs5aMsZIZqRYVMQgGnU2T5gb_6l3to
	3D Print files - https://www.tinkercad.com/things/8H79OmknuDc-all-sorting-machine-blocks?sharecode=gUBeHjsUa5k9O5WAyYCGVbsvjMlA86fZP6nKU6qNViU

Support - Help keep my motivation and my wife less annoyed with the machine's existence

	Patreon - https://www.patreon.com/KairiCollections
	By me a coffee - https://www.buymeacoffee.com/KairiCollections
	Ko-fi - http://ko-fi.com/kairiskyewillow

Other non-related support:

	https://www.etsy.com/shop/KairiCollections
