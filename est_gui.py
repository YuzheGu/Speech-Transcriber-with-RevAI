# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import tkinter
from tkinter import *
from tkinter import ttk
import sys
import configparser
from est import *

config = configparser.ConfigParser()
config.read('transcription_config.ini')

#config file entry names
# a full list of all entries in the config file - used to check config file validity.
config_entries = {'API.token':['token'],
                  'folders':['input_folder', 'output_folder'],
                  'concatenation':['input_concatenate', 'plain_text'],
                  'transcribe.config':['skip_diarization', 'skip_punctuation', 'remove_disfluencies', 'speaker_channels_count', 'language']
                 }

# the dict that stores all the entry inputs
# used to organize GUI input and write to the config file.
entry_inputs = {'token':'', 'input_folder':'', 'output_folder':'', 'input_concatenate':'', 'plain_text':'', 'skip_diarization':'', 'remove_disfluencies':'',
                'speaker_channels_count':'', 'language':''}


# submit button click function
# write to and check the config file first, then run the transcription function if there are no config errors
def submit_click():
    global error_message

    # update config entries with new inputs from the GUI
    for entry in config_entries:
        for item in config_entries[entry]:
            config[entry][item] = entry_inputs[item].get()


    # write the current config entries to the config file
    with open("transcription_config.ini", 'w') as cf:
        config.write(cf)

    #check the validity of all config entries
    try:
        config_message, check_result = config_check(config)
        # display new error message from config check
        error_message.set("")
        error_message.set(error_message.get() + config_message)
        message_label.update()
        #return

        #run the transcription only when every entry is valid
        if check_result:
            #execute transcription script
            main(message_label)
    except Exception:
        print("Error: exception found, program exited.")
        exit()


def redirect_text(message_output):
    #message_label.config(text = message_output)
    error_message.set(error_message.get() + message_output)


# start GUI
root = Tk()
root.title("Transcription Parameters")

# canvas size
root.geometry("800x850")

error_message = tkinter.StringVar()
error_message.set('')

# display the label and textbox for all entries
# all entry will have default value from the config file
token_label = tkinter.Label(root, text="API token")
token_label.place(x= 30, y = 50)
token = ttk.Entry(root, width = 100, font = ('Helvetica 10'))
token.place(x= 120, y = 50, height = 40)
token.delete(0, "end")
token.insert(0, config['API.token']['token'])
entry_inputs['token'] = token
#token_note = tkinter.Label(root, text="RevAI token")
#token_note.place(x= 700, y = 50)

input_folder_label = tkinter.Label(root, text="input folder")
input_folder_label.place(x= 30, y = 110)
input_folder = ttk.Entry(root)
input_folder.place(x= 120, y = 110)
input_folder.delete(0, "end")
input_folder.insert(0, config['folders']['input_folder'])
entry_inputs['input_folder'] = input_folder
input_folder_note = tkinter.Label(root, text="Subfolder of input audio files")
input_folder_note.place(x= 400, y = 110)


output_folder_label = tkinter.Label(root, text="output folder")
output_folder_label.place(x= 30, y = 140)
output_folder = ttk.Entry(root)
output_folder.place(x= 120, y = 140)
output_folder.delete(0, "end")
output_folder.insert(0, config['folders']['output_folder'])
entry_inputs['output_folder'] = output_folder
output_folder_note = tkinter.Label(root, text="Subfolder for output transcriptions")
output_folder_note.place(x= 400, y = 140)

input_concatenate_label = tkinter.Label(root, text="input concatenation")
input_concatenate_label.place(x= 30, y = 170)
input_concatenate = ttk.Entry(root)
input_concatenate.place(x= 170, y = 170)
input_concatenate.delete(0, "end")
input_concatenate.insert(0, config['concatenation']['input_concatenate'])
entry_inputs['input_concatenate'] = input_concatenate
input_concatenate_note = tkinter.Label(root, text="Concatenate audio files for transcription?")
input_concatenate_note.place(x= 400, y = 170)

plain_text_label = tkinter.Label(root, text="plain_text")
plain_text_label.place(x= 30, y = 210)
plain_text = ttk.Entry(root)
plain_text.place(x= 120, y = 210)
plain_text.delete(0, "end")
plain_text.insert(0, config['concatenation']['plain_text'])
entry_inputs['plain_text'] = plain_text
plain_text_note = tkinter.Label(root, text="create a plain text version for each transcription?")
plain_text_note.place(x= 400, y = 210)

language_config_label = tkinter.Label(root, text="Configure the transcriber", font=('Helvetica', 12))
language_config_label.place(x= 30, y = 260)

skip_diarization_label = tkinter.Label(root, text="skip diarization")
skip_diarization_label.place(x= 30, y = 290)
skip_diarization = ttk.Entry(root)
skip_diarization.place(x= 150, y = 290)
skip_diarization.delete(0, "end")
skip_diarization.insert(0, config['transcribe.config']['skip_diarization'])
entry_inputs['skip_diarization'] = skip_diarization
skip_diarization_note = tkinter.Label(root, text="Do not separate speakers?")
skip_diarization_note.place(x= 400, y = 290)

skip_punctuation_label = tkinter.Label(root, text="skip punctuation")
skip_punctuation_label.place(x= 30, y = 320)
skip_punctuation = ttk.Entry(root)
skip_punctuation.place(x= 150, y = 320)
skip_punctuation.delete(0, "end")
skip_punctuation.insert(0, config['transcribe.config']['skip_punctuation'])
entry_inputs['skip_punctuation'] = skip_punctuation
skip_punctuation_note = tkinter.Label(root, text="Skip punctuation?")
skip_punctuation_note.place(x= 400, y = 320)

remove_disfluencies_label = tkinter.Label(root, text="remove disfluencies")
remove_disfluencies_label.place(x= 30, y = 350)
remove_disfluencies = ttk.Entry(root)
remove_disfluencies.place(x= 160, y = 350)
remove_disfluencies.delete(0, "end")
remove_disfluencies.insert(0, config['transcribe.config']['remove_disfluencies'])
entry_inputs['remove_disfluencies'] = remove_disfluencies
remove_disfluencies_note = tkinter.Label(root, text="Remove disfluencies (uh, ah)?")
remove_disfluencies_note.place(x= 400, y = 350)

speaker_channels_count_label = tkinter.Label(root, text="speaker channels count")
speaker_channels_count_label.place(x= 30, y = 380)
speaker_channels_count = ttk.Entry(root)
speaker_channels_count.place(x= 185, y = 380)
speaker_channels_count.delete(0, "end")
speaker_channels_count.insert(0, config['transcribe.config']['speaker_channels_count'])
entry_inputs['speaker_channels_count'] = speaker_channels_count
speaker_channels_note = tkinter.Label(root, text="number of audio channels (mono = 1, stereo = 2, etc.)")
speaker_channels_note.place(x= 400, y = 380)

language_label = tkinter.Label(root, text="language")
language_label.place(x= 30, y = 410)
language = ttk.Entry(root)
language.place(x= 100, y = 410)
language.delete(0, "end")
language.insert(0, config['transcribe.config']['language'])
entry_inputs['language'] = language
language_note = tkinter.Label(root, text="English: en, Spanish: es, Mandarin: cmn, French: fr")
language_note.place(x= 400, y = 410)

# transcriber_label = tkinter.Label(root, text="transcriber")
# #transcriber_label.place(x= 30, y = 410)
# transcriber = ttk.Entry(root)
# #transcriber.place(x= 100, y = 410)
# transcriber.delete(0, "end")
# transcriber.insert(0, config['transcribe.config']['transcriber'])
# entry_inputs['transcriber'] = transcriber
# transcriber_note = tkinter.Label(root, text="transcriber")
# #transcriber_note.place(x= 400, y = 410)

# GUI style settings
style = ttk.Style()
style.theme_use('alt')
style.configure('TButton', font=('Helvetica', 12), background='blue', foreground='white')
style.map('TButton', background=[('active', '#ff0000')])

# button to save the input and run the transcription
submit_button = ttk.Button(root, text="Save & Transcribe", command=lambda:submit_click())
submit_button.pack()
submit_button.place(x = 60, y = 480)


# message shown in the GUI (error message, transcribing status etc.)
message_label = tkinter.Label(root, textvariable = error_message, justify = LEFT)
#message_label.pack()
message_label.place(x= 30, y = 530)

sys.stdout.write = redirect_text
# run the GUI
root.mainloop()
