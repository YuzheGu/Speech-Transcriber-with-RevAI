# -*- coding: utf-8 -*-
"""
MIT License

Copyright (c) 2023, Margaret Broeren, Yuzhe Gu, Mark Pitt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
import os
import csv
import datetime
import time
import shutil
import re
import tkinter
from tkinter import *
from tkinter import ttk
import sys
import configparser
from pydub import AudioSegment, utils
from rev_ai import apiclient
import string

config = configparser.ConfigParser()
config.read('transcription_config.ini')

confirm_ctr = 0

#config file entry names
# a full list of all entries in the config file - used to check config file validity.
config_entries = {'API.token':['token'],
                  'folders':['input_folder', 'output_folder'],
                  'output_format': ['format'],
                  'concatenation':['concatenate_input', 'text_only'],
                  'transcribe.config':['skip_diarization', 'skip_punctuation', 'remove_disfluencies', 'speaker_channels_count', 'language', 'delete_after_seconds']
                 }

# the dict that stores all the entry inputs
# used to organize GUI input and write to the config file.
entry_inputs = {'token':'', 'input_folder':'', 'output_folder':'', 'format':'','concatenate_input':'', 'text_only':'', 'skip_diarization':'', 'remove_disfluencies':'',
                'speaker_channels_count':'', 'language':'', 'delete_after_seconds':''}



def config_check(config):
    valid = True

    # the message(error message etc.) output to the console
    console_message = ''

    #check if all entries exist
    for entry in config_entries:
        if not config.has_section(entry):
            console_message += f'section miss: {entry}\n'
            valid = False
        for item in config_entries[entry]:
            if not config.has_option(entry, item):
                console_message += f'option miss: {entry}, {item}\n'
                valid = False

    # Simple way to check if the API token is valid
    # Error is generated if it fails to retrieve the last job.
    client = apiclient.RevAiAPIClient(config['API.token']['token'])
    try:
        jobs = client.get_list_of_jobs(limit=1)
    except Exception:
        console_message += 'Error: API token is invalid.\n'
        valid = False

    # Check input and output folders
    if not os.path.exists(config['folders']['input_folder']):
        console_message += 'Error: Input folder does not exist. Ensure the corret folder name is specified.\n'
        valid = False

    if not os.path.exists(config['folders']['output_folder']):
        console_message += 'Error: Output folder does not exist, so we made it. It is named "output"\n'
        os.mkdir(config['folders']['output_folder'])
    
    if config['output_format']['format'] != 'CHAT' and config['output_format']['format'] != 'customize':
        console_message += 'Error: output format should be CHAT or customize.\n'
        valid = False

    # checking for other boolean parameters
    if config['concatenation']['concatenate_input'] != "True" and config['concatenation']['concatenate_input'] != "False":
        console_message += 'Error: Input concatenate should be True or False.\n'
        valid = False
    if config['concatenation']['text_only'] != "True" and config['concatenation']['text_only'] != "False":
        console_message += 'Error: Plain text should be True or False.\n'
        valid = False
    if config['transcribe.config']['skip_diarization'] != "True" and config['transcribe.config']['skip_diarization'] != "False":
        console_message += 'Error: Skip diarization should be True or False.\n'
        valid = False
    if config['transcribe.config']['skip_punctuation'] != "True" and config['transcribe.config']['skip_punctuation'] != "False":
        console_message += 'Error: Skip punctuation should be True or False.\n'
        valid = False
    if config['transcribe.config']['remove_disfluencies'] != "True" and config['transcribe.config']['remove_disfluencies'] != "False":
        console_message += 'Error: Remove disfluencies should be True or False.\n'
        valid = False
    try:
        # check the speaker channels count - it needs to be a positive integer or None
        channel_check = config['transcribe.config']['speaker_channels_count']
        if not channel_check.isnumeric() and channel_check != 'None':
            console_message += 'Error: Speaker channels count should be either None or a positive number.\n'
            valid = False
        if channel_check.isnumeric() and int(channel_check) <= 0:
            console_message += "Error: Speaker channels count should be a positive integer.\n"
            valid = False
    except Exception:
        console_message += 'Error: Speaker channels count should be either None or a positive number.\n'
        valid = False

    try:
        # check the delete after seconds - it needs to be a positive integer or None
        delete_check = config['transcribe.config']['delete_after_seconds']
        if not delete_check.isnumeric() and delete_check != 'None':
            console_message += 'Error: Delete after seconds should be either None or a positive number.\n'
            valid = False
        if delete_check.isnumeric() and int(delete_check) <= 0:
            console_message += "Error: Delete after seconds should be a positive integer.\n"
            valid = False
    except Exception:
        console_message += 'Error: Delete after seconds should be either None or a positive number.\n'
        valid = False

    # display the error message on GUI if not valid
    if valid:
        console_message += 'Configuration check passed.\n'
    else:
        console_message += 'Invalid configurations, program exited. Please correct the errors and try again.\n'

    return console_message, valid


#concatenate the audio files.
#Parameters:
#file_list - the file list that contains the audio files to be concatenated.
#return: [temp_audiofile] - the file name of the long temp audio file.
def concatenate_audiofiles(temp_folder_name, afile_list, file_extension):

    # temporary audio file used to hold concatenated files
    temp_audiofile = "".join((temp_folder_name, 'combinedaudiofiles.', file_extension))
    # initialize an audiosegment for concatenating audio files
    concatenated_audio = AudioSegment.empty()

    for audiofile in afile_list:
        # Read the audiofile in the folder
        if file_extension == 'ogg':
            filecodec = utils.mediainfo(audiofile)['codec_name']
            if filecodec == 'vorbis':
                filecodec = ''.join(('lib',filecodec))
            concatenated_audio += AudioSegment.from_file(audiofile, codec=filecodec)
        else:
            concatenated_audio += AudioSegment.from_file(audiofile)

        # Add silence between audio files to minimize confusing segmentation
        # This might not be a problem but it is a cheap safeguard
        concatenated_audio += AudioSegment.silent(duration=100)

    # Save concatenated sound files to a temporary file for use by rev.ai
    if file_extension == 'ogg':
        file_handle = concatenated_audio.export(temp_audiofile, format=file_extension, codec=filecodec)
    else:
        file_handle = concatenated_audio.export(temp_audiofile, format=file_extension)
    file_handle.close()
    return temp_audiofile


# Append silence to the end of audio files that are shorter than 2 seconds.
#Parameters:
#   original_file_name - the original short audio file.
#Return:
#   elongated_file_name - the new long audio file.
def elongate_audiofile(t_folder, original_file_name, added_duration, file_extension):

    #elongate if less than 2s long
    stim = AudioSegment.empty()
    if file_extension == 'ogg':
        filecodec = utils.mediainfo(original_file_name)['codec_name']
        if filecodec == 'vorbis':
            filecodec = ''.join(('lib',filecodec))
        stim += AudioSegment.from_file(original_file_name, codec=filecodec)
    else:
        stim += AudioSegment.from_file(original_file_name)

    stim += AudioSegment.silent(duration = 1000 * added_duration)

    # Assumes the input folder is only one level down. Otherwise rsplit will fail
    base_file_name = original_file_name.rsplit('.')[0].split('/')[1]
    elongated_file_name = ''.join((t_folder, base_file_name, '_long', '.', file_extension))

    if file_extension == 'ogg':
        file_handle = stim.export(elongated_file_name, format=file_extension, codec=filecodec)
    else:
        file_handle = stim.export(elongated_file_name, format=file_extension)

    file_handle.close()
    return elongated_file_name


# Transcribe speech file located in a folder
# Parameters:
# audiofile - the file to be transcribed
#
def transcribe_speech(audiofile, client_api, message_label):
    # Submit job for transcription
    print(f'transcribing:{audiofile}')

    # update the GUI if in GUI mode
    if message_label != None:
        message_label.update()
    CHAT_mode = True if config['output_format']['format'] == 'CHAT' else False
    # speaker channels count is a positive integer or None
    speaker_channels_count = None if config['transcribe.config']['speaker_channels_count'] == 'None' else int(config['transcribe.config']['speaker_channels_count'])
    # delete after seconds is a positive integer or None
    delete_after_seconds = None if config['transcribe.config']['delete_after_seconds'] == 'None' else int(config['transcribe.config']['delete_after_seconds'])
    if config['transcribe.config']['language'] == 'en':
        job = client_api.submit_job_local_file(
            filename = audiofile,  # file name
            skip_diarization = False if CHAT_mode else config.getboolean('transcribe.config', 'skip_diarization'),  # needed for conversations. Tries to match audio with speakers
            skip_punctuation = True if CHAT_mode else config.getboolean('transcribe.config', 'skip_punctuation'),  # removes punctuations
            remove_disfluencies = False if CHAT_mode else config.getboolean('transcribe.config', 'remove_disfluencies'),  # removes speech disfluencies ("uh", "um"). Only avalable for English, Spanish, French languages
            speaker_channels_count = None if CHAT_mode else speaker_channels_count,  # Number of audio channels. Only avalable for English, Spanish, French languages
            language = config['transcribe.config']['language'],  # language of the audio file(s)
            delete_after_seconds = delete_after_seconds,  # Amount of time after job completion when job is auto-deleted. Default (after 30 days) is None.
            #verbatim = True,  # transcribe every syllable
            #remove_atmospherics = True,  # remove atmospherics (e.g. <laugh>)
            #filter_profanity = True,  # filter profanities
            #diarization_type = "standard",  # diarization type
            #custom_vocabularies = []  # additional vocabulary
            )
    else:
        job = client_api.submit_job_local_file(
            filename = audiofile,  # file name
            skip_diarization = False if CHAT_mode else config.getboolean('transcribe.config', 'skip_diarization'),  # needed for conversations. Tries to match audio with speakers
            language = config['transcribe.config']['language'],  # language of the audio file(s)
            delete_after_seconds = delete_after_seconds,  # Amount of time after job completion when job is auto-deleted. Default (after 30 days) is None.
            #verbatim = True,  # transcribe every syllable
            #remove_atmospherics = False,  # remove atmospherics (e.g. <laugh>)
            #filter_profanity = False,  # filter profanities
            #custom_vocabularies = []  # additional vocabulary
            )



    # Retrieve transcription job info
    job_details = client_api.get_job_details(job.id)

    # Poll job progress until finished
    # To see all details: var(job_details) in console
    while (job_details.status.name == 'IN_PROGRESS'):
        time.sleep(20)
        job_details = client_api.get_job_details(job.id)


    # Grab the transcript or raise an exception on failure
    # See transcription history in your account at rev.ai for explanation
    if job_details.status.name == 'TRANSCRIBED':
        transcript_json = client_api.get_transcript_json(job.id)
    elif job_details.status.name == 'FAILED':
        failure_message = f'Transcription failed: {job_details.failure}\n{job_details.failure_detail}\n\n'
        if message_label != None:
            # update the GUI if in GUI mode
            message_label.update()
        raise Exception(failure_message)

    transcript = []


    # Assumes a single speaker, else multiple speakers when set to "None"
    if speaker_channels_count != None:
        for transcript_num in range(len(transcript_json["monologues"])):
            for j, a in enumerate(transcript_json["monologues"][transcript_num]["elements"], start=0):
                # remove white space
                if a['type'] == 'punct' and a['value'] == ' ':
                    continue
                # output file name, transcribed word, and confidence level
                transcript.append({'filename':audiofile,
                            'transcription':a['value'].lower(),
                            'confidence': a['confidence'] if a['type'] != 'punct' else '/' })
    else:
        for j in transcript_json["monologues"]:
            # a = ''.join(("Speaker ", str(j['speaker']),":"))
            # remove white space
            for a in j['elements']:
                if a['type'] == 'punct' and a['value'] == ' ':
                    continue
                # a = ' '.join((a,str(i['value'])))
                # output file name, transcribed word, confidence level, and speaker information
                transcript.append({'filename':audiofile,
                               'transcription':a['value'].lower(),
                               'confidence': a['confidence'] if a['type'] != 'punct' else '/',
                               'speaker': str(j['speaker'])})



    return transcript


#Save transcriptions to CSV file
#Parameters:
#   output_data - transcription data dict.
#   output_file_name_def - the output file name.
#   text_only - to output a plain text (TXT) version or not.
def save_transcription(output_data, output_file_name_def, text_only, CHAT_output):
    replace_dict = {
        "dr.": "Doctor",
        "mr.": "Mister",
        "mrs.": "Missus",
        "ms.": "Ms"
    }

    header_text = (
        "@Begin\n"
        "@Languages:\n"
        "@Participants:\n"
        "@ID:\n"
        "@ID:\n"
        "@ID:\n"
        "@Media:\n"
        "@Location:\n"
        "@Recording Quality:\n"
        "@Transcriber:\n"
        "@Date:\n"
        "@Situation:"
    )

    # Ending text - same as CHAT file
    footer_text = "\n@End"

    keys_list = output_data[0].keys()
    with open(output_file_name_def,'w', newline='', encoding = 'utf-8-sig') as outfile:
        csv_writer = csv.DictWriter(outfile, keys_list)
        csv_writer.writeheader()
        csv_writer.writerows(output_data)
    if text_only:
        
        
        if CHAT_output:
            text_filename = output_file_name_def.rsplit('.')[0] + '.cha'
            if 'speaker' not in output_data[0]: # not a conversation
                with open(text_filename,'w', newline='') as outtextfile:
                    outtextfile.write(header_text)
                    for result_word in output_data:
                        # no white space before a punctuation
                        if result_word['transcription'] in string.punctuation:
                            outtextfile.write(result_word['transcription'])
                        else:
                            if result_word['transcription'] in replace_dict:
                                outtextfile.write(''.join((' ', replace_dict[result_word['transcription']])))
                            else:
                                outtextfile.write(''.join((' ', result_word['transcription'])))
                    outtextfile.write(footer_text)
            else: # example use: conversation
                current_speaker = -1
                with open(text_filename,'w', newline='') as outtextfile:
                    outtextfile.write(header_text)
                    for result_word in output_data:
                        # switch speaker
                        if result_word['speaker'] != current_speaker:
                            outtextfile.write(''.join(('\nSP', str(int(result_word['speaker']) + 1), ': ', result_word['transcription'])))
                            current_speaker = result_word['speaker']
                        else:
                            # no white space before a punctuation
                            if result_word['transcription'] in string.punctuation:
                                outtextfile.write(result_word['transcription'])
                            else:
                                if result_word['transcription'] in replace_dict:
                                    outtextfile.write(''.join((' ', replace_dict[result_word['transcription']])))
                                else:
                                    outtextfile.write(''.join((' ', result_word['transcription'])))
                    outtextfile.write(footer_text)
            return

        text_filename = output_file_name_def.rsplit('.')[0] + '.txt'
        if 'speaker' not in output_data[0]: # not a conversation
            with open(text_filename,'w', newline='') as outtextfile:
                for result_word in output_data:
                    # no white space before a punctuation
                    if result_word['transcription'] in string.punctuation:
                        outtextfile.write(result_word['transcription'])
                    else:
                        outtextfile.write(''.join((' ', result_word['transcription'])))
        else: # example use: conversation
            current_speaker = -1
            with open(text_filename,'w', newline='') as outtextfile:
                for result_word in output_data:
                    # switch speaker
                    if result_word['speaker'] != current_speaker:
                        outtextfile.write(''.join(('\nspeaker ', result_word['speaker'], ': ', result_word['transcription'])))
                        current_speaker = result_word['speaker']
                    else:
                        # no white space before a punctuation
                        if result_word['transcription'] in string.punctuation:
                            outtextfile.write(result_word['transcription'])
                        else:
                            outtextfile.write(''.join((' ', result_word['transcription'])))
                            
        


    


# Delete temp/ and its contents
def delete_temp_folder(folder):
    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
        except OSError:
            pass

#############################################################################################
# Main
# Parameter:
# message_label: the GUI text element needed to be updated
def main(message_label):
    global config

    config = configparser.ConfigParser()
    config.read('transcription_config.ini')

    client_api = apiclient.RevAiAPIClient(config['API.token']['token'])
    input_folder = ''.join((config['folders']['input_folder'], '/'))
    output_folder = ''.join((config['folders']['output_folder'], '/'))
    CHAT_mode = True if config['output_format']['format'] == 'CHAT' else False
    # Process the audio files individually or concatenate them into a single file for transcription
    #  For short files, this is more efficient and less costly.
    #True - concatenated. False - individual files
    concatenate_input = config.getboolean('concatenation', 'concatenate_input')
    text_only = config.getboolean('concatenation', 'text_only')

    # Used as part of the transcription output filename
    date_time = datetime.datetime.now()
    date_today = date_time.strftime('%m%d%Y')

    supported_extensions = ['mp3', 'wav', 'ogg', 'opus', 'flac', 'webm']

    # Make a temporary folder for storing elongated and concatenated audio files
    temp_folder = 'temp/'
    delete_temp_folder(temp_folder)
    os.mkdir(temp_folder)

    # make list of all audio files in input folder that have a supported extension
    audiofile_list = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.rsplit('.')[1] in supported_extensions]

    # check if all audio files have the same extension
    dummy, first_extension = audiofile_list[0].rsplit(".")
    if not all(f.endswith(first_extension) for f in audiofile_list):
        print('Error: All audio files in the input folder must have the same file extension (be the same format).')
        sys.exit()

    # Ensure extension is supported
    if first_extension not in supported_extensions:
        print(f'Error: You are using an unsupported audio format. Spported formats: {supported_extensions} ')
        sys.exit()


    # concatenate the audio files in the list if in input concatenated mode
    if concatenate_input == True:

        audiofile = concatenate_audiofiles(temp_folder, audiofile_list, first_extension)


        transcript = transcribe_speech(audiofile, client_api, message_label)

        # Save all trascriptions in output folder
        output_filename = ''.join((output_folder + 'concatenated_transcription_' + date_today + '.csv'))
        save_transcription(transcript, output_filename, text_only, CHAT_mode)

    # concatenate_input = False
    else:
        # Transcribe speech files
        for audiofile in audiofile_list:

                # Check file length relative to 2sec minimum
                audio_duration_shortfall = 2.01 - AudioSegment.from_file(audiofile).duration_seconds

                # Elongate if less than 2s long
                if audio_duration_shortfall > 0:
                    audiofile = elongate_audiofile(temp_folder, audiofile, audio_duration_shortfall, first_extension)

                transcript = transcribe_speech(audiofile, client_api, message_label)
                # Save all trascriptions in output folder
                audio_file_name =  re.split('[/.]', audiofile)[-2]
                output_filename = ''.join((output_folder + audio_file_name + '_transcription_' + date_today + '.csv'))
                save_transcription(transcript, output_filename, text_only, CHAT_mode)


    print('\nAll transcription is finished')
    # update the GUI if in GUI mode
    if message_label != None:
        message_label.update()
    # Delete folders and files that were created
    delete_temp_folder(temp_folder)





# submit button click function
# write to and check the config file first, then run the transcription function if there are no config errors
def submit_click():
    global error_message
    
    if confirm_ctr < 2:
        error_message.set("")
        error_message.set(error_message.get() + 'Error: you need to confirm your output format choice.')
        message_label.update()
        return

    # update config entries with new inputs from the GUI
    for entry in config_entries:
        for item in config_entries[entry]:
            config[entry][item] = entry_inputs[item].get()


    # write the current config entries to the config file
    with open('transcription_config.ini', 'w') as cf:
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
        print('Error: exception found, program exited.')
        sys.exit()
        
def CHAT_switch():
    skip_diarization.delete(0, 'end')
    skip_diarization.insert(0, 'False')
    skip_diarization.config(state='disabled')
    
    skip_punctuation.delete(0, 'end')
    skip_punctuation.insert(0, 'True')
    skip_punctuation.config(state='disabled')
    
    remove_disfluencies.delete(0, 'end')
    remove_disfluencies.insert(0, 'False')
    remove_disfluencies.config(state='disabled')
    
    speaker_channels_count.delete(0, 'end')
    speaker_channels_count.insert(0, 'None')
    speaker_channels_count.config(state='disabled')


def customize_switch():
    skip_diarization.config(state='normal')
    skip_punctuation.config(state='normal')
    remove_disfluencies.config(state='normal')
    speaker_channels_count.config(state='normal')

def mode_switch():
    global confirm_ctr
    confirm_ctr += 1
    if mode.get() == 'CHAT':
        CHAT_switch()
    else:
        mode.set('customize')
        customize_switch()


def redirect_text(message_output):
    #message_label.config(text = message_output)
    error_message.set(error_message.get() + message_output)

# start GUI
root = Tk()
root.title('Transcription Parameters')

# canvas size
root.geometry('800x850')

error_message = tkinter.StringVar()
error_message.set('')

# display the label and textbox for all entries
# all entry will have default value from the config file
token_label = tkinter.Label(root, text='API token')
token_label.place(x= 30, y = 50)
token = ttk.Entry(root, width = 100, font = ('Helvetica 10'))
token.place(x= 120, y = 50, height = 40)
token.delete(0, 'end')
token.insert(0, config['API.token']['token'])
entry_inputs['token'] = token
#token_note = tkinter.Label(root, text="RevAI token")
#token_note.place(x= 700, y = 50)

input_folder_label = tkinter.Label(root, text='input folder')
input_folder_label.place(x= 30, y = 110)
input_folder = ttk.Entry(root)
input_folder.place(x= 120, y = 110)
input_folder.delete(0, "end")
input_folder.insert(0, config['folders']['input_folder'])
entry_inputs['input_folder'] = input_folder
input_folder_note = tkinter.Label(root, text='Subfolder of input audio files')
input_folder_note.place(x= 400, y = 110)


output_folder_label = tkinter.Label(root, text='output folder')
output_folder_label.place(x= 30, y = 140)
output_folder = ttk.Entry(root)
output_folder.place(x= 120, y = 140)
output_folder.delete(0, 'end')
output_folder.insert(0, config['folders']['output_folder'])
entry_inputs['output_folder'] = output_folder
output_folder_note = tkinter.Label(root, text='Subfolder for output transcriptions')
output_folder_note.place(x= 400, y = 140)






concatenate_input_label = tkinter.Label(root, text='concatenate input')
concatenate_input_label.place(x= 30, y = 220)
concatenate_input = ttk.Entry(root)
concatenate_input.place(x= 170, y = 220)
concatenate_input.delete(0, 'end')
concatenate_input.insert(0, config['concatenation']['concatenate_input'])
entry_inputs['concatenate_input'] = concatenate_input
concatenate_input_note = tkinter.Label(root, text='Concatenate audio files for transcription?')
concatenate_input_note.place(x= 400, y = 220)

text_only_label = tkinter.Label(root, text='text_only')
text_only_label.place(x= 30, y = 260)
text_only = ttk.Entry(root)
text_only.place(x= 120, y = 260)
text_only.delete(0, 'end')
text_only.insert(0, config['concatenation']['text_only'])
entry_inputs['text_only'] = text_only
text_only_note = tkinter.Label(root, text='create an extra text-only TXT file for each transcription?')
text_only_note.place(x= 400, y = 260)

language_config_label = tkinter.Label(root, text='Configure the transcriber', font=('Helvetica', 12))
language_config_label.place(x= 30, y = 310)

skip_diarization_label = tkinter.Label(root, text='skip diarization')
skip_diarization_label.place(x= 30, y = 340)
skip_diarization = ttk.Entry(root)
skip_diarization.place(x= 150, y = 340)
skip_diarization.delete(0, 'end')
skip_diarization.insert(0, config['transcribe.config']['skip_diarization'])
entry_inputs['skip_diarization'] = skip_diarization
skip_diarization_note = tkinter.Label(root, text='Do not separate speakers?')
skip_diarization_note.place(x= 400, y = 340)

skip_punctuation_label = tkinter.Label(root, text='skip punctuation')
skip_punctuation_label.place(x= 30, y = 370)
skip_punctuation = ttk.Entry(root)
skip_punctuation.place(x= 150, y = 370)
skip_punctuation.delete(0, 'end')
skip_punctuation.insert(0, config['transcribe.config']['skip_punctuation'])
entry_inputs['skip_punctuation'] = skip_punctuation
skip_punctuation_note = tkinter.Label(root, text='Skip punctuation?')
skip_punctuation_note.place(x= 400, y = 370)

remove_disfluencies_label = tkinter.Label(root, text='remove disfluencies')
remove_disfluencies_label.place(x= 30, y = 400)
remove_disfluencies = ttk.Entry(root)
remove_disfluencies.place(x= 160, y = 400)
remove_disfluencies.delete(0, 'end')
remove_disfluencies.insert(0, config['transcribe.config']['remove_disfluencies'])
entry_inputs['remove_disfluencies'] = remove_disfluencies
remove_disfluencies_note = tkinter.Label(root, text='Remove disfluencies (uh, ah)?')
remove_disfluencies_note.place(x= 400, y = 400)

speaker_channels_count_label = tkinter.Label(root, text='speaker channels count')
speaker_channels_count_label.place(x= 30, y = 430)
speaker_channels_count = ttk.Entry(root)
speaker_channels_count.place(x= 185, y = 430)
speaker_channels_count.delete(0, 'end')
speaker_channels_count.insert(0, config['transcribe.config']['speaker_channels_count'])
entry_inputs['speaker_channels_count'] = speaker_channels_count
speaker_channels_note = tkinter.Label(root, text='number of audio channels (mono = 1, stereo = 2, etc.)')
speaker_channels_note.place(x= 400, y = 430)

language_label = tkinter.Label(root, text='language')
language_label.place(x= 30, y = 460)
language = ttk.Entry(root)
language.place(x= 100, y = 460)
language.delete(0, 'end')
language.insert(0, config['transcribe.config']['language'])
entry_inputs['language'] = language
language_note = tkinter.Label(root, text='English: en, Spanish: es, Mandarin: cmn, French: fr')
language_note.place(x= 400, y = 460)

delete_after_seconds_label = tkinter.Label(root, text='delete_after_seconds')
delete_after_seconds_label.place(x= 30, y = 490)
delete_after_seconds = ttk.Entry(root)
delete_after_seconds.place(x= 180, y = 490)
delete_after_seconds.delete(0, 'end')
delete_after_seconds.insert(0, config['transcribe.config']['delete_after_seconds'])
entry_inputs['delete_after_seconds'] = delete_after_seconds
delete_after_seconds_note = tkinter.Label(root, text='How long does it take to delete the file from the server?')
delete_after_seconds_note.place(x= 400, y = 490)

# GUI style settings
style = ttk.Style()
style.theme_use('alt')
style.configure('TButton', font=('Helvetica', 12), background='blue', foreground='white')
style.map('TButton', background=[('active', '#ff0000')])


# customize_switch_button = ttk.Button(root, text='customize', command=lambda:customize_switch())
# customize_switch_button.pack()
# customize_switch_button.place(x = 300, y = 20)


radio_label = tkinter.Label(root, text='output format:')
radio_label.place(x = 30, y = 180)

mode = tkinter.StringVar()


radio_CHAT = Radiobutton(root, text='CHAT', variable=mode, value='CHAT')
radio_CHAT.pack()
radio_CHAT.place(x = 120, y = 180)

radio_customize = Radiobutton(root, text='customize', variable=mode, value='customize')
radio_customize.pack()
radio_customize.place(x = 190, y = 180)
mode.set(config['output_format']['format'])
mode_switch()
entry_inputs['format'] = mode

mode_switch_button = ttk.Button(root, text='confirm', command=lambda:mode_switch())
mode_switch_button.pack()
mode_switch_button.place(x = 310, y = 180)


# button to save the input and run the transcription
submit_button = ttk.Button(root, text='Save & Transcribe', command=lambda:submit_click())
submit_button.pack()
submit_button.place(x = 60, y = 530)


# message shown in the GUI (error message, transcribing status etc.)
message_label = tkinter.Label(root, textvariable = error_message, justify = LEFT)
#message_label.pack()
message_label.place(x= 30, y = 580)

sys.stdout.write = redirect_text
# run the GUI
root.mainloop()


