# SubtitleVisor
this is from the video
https://youtu.be/dacxmLN4koM

items used:

Raspberry Pi Pico 2

Adafruit 16x9 Charlieplexed PWM LED Matrix Driver - IS31FL3731

some leds and such



grid.py is for assigning a predefined grid pattern to the matrix

realtime.py is for interfacing with tail_to_pico_words_stable.py which analyzes the whisper.cpp data to output words "realtime"

test.py tests the LEDs in the matrix

textDisplay.py is to output a predefined string of characters

transcription.py runs the whisper.cpp instance and cleanses the text output from the VAD mode, also the whisper.cpp build used was just the standard base_en whose build instructions are given in the whisper documentation
