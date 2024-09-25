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
# import required packages

import os
import csv
import datetime
import time
import shutil
import re
import sys
from pydub import AudioSegment, utils
from rev_ai import apiclient
import configparser
import string

# create config file reader
config = configparser.ConfigParser()
config.read('transcription_config.ini')

# config file entries structure
config_entries = {'API.token':['token', 'save_check'],
                  'folders':['input_folder', 'output_folder'],
                  'output_format': ['format'],
                  'concatenation':['concatenate_input', 'csv_file'],
                  'transcribe.config':['diarization', 'punctuation', 'remove_disfluencies', 'speaker_channels_count', 'language']
                 }

# Check if all config.ini values are available and valid
#Parameters:
#config - the reader config file
#return:
#console_message - the message (error message, etc.) generated during the config checking
#valid - the validity of the config fil. True: all entries valid; False: error existed
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
    
    try:
        save_check = config['API.token']['save_check']
        if not save_check.isnumeric():
            console_message += 'Error: API save check should be either 1 or 0.\n'
            valid = False
        if int(save_check) != 0 and int(save_check) != 1:
            console_message += 'Error: API save check should be either 1 or 0.\n'
            valid = False
    except Exception:
        console_message += 'Error: API save check should be either 1 or 0.\n'
        valid = False
    

    # Check input and output folders
    if not os.path.exists(config['folders']['input_folder']):
        console_message += 'Error: Input folder does not exist. Ensure the correct folder name is specified.\n'
        valid = False

    if not os.path.exists(config['folders']['output_folder']):
        console_message += 'Error: Output folder does not exist, so we made it. It is named "output"\n'
        os.mkdir(config['folders']['output_folder'])
    
    if config['output_format']['format'] != 'CHAT' and config['output_format']['format'] != 'unformatted':
        console_message += 'Error: output format should be CHAT or unformatted.\n'
        valid = False

    # checking for other boolean parameters
    if config['concatenation']['concatenate_input'] != "True" and config['concatenation']['concatenate_input'] != "False":
        console_message += 'Error: Input concatenate should be True or False.\n'
        valid = False
    if config['concatenation']['csv_file'] != "True" and config['concatenation']['csv_file'] != "False":
        console_message += 'Error: Csv only should be True or False.\n'
        valid = False
    if config['transcribe.config']['diarization'] != "True" and config['transcribe.config']['diarization'] != "False":
        console_message += 'Error: Diarization should be True or False.\n'
        valid = False
    if config['transcribe.config']['punctuation'] != "True" and config['transcribe.config']['punctuation'] != "False":
        console_message += 'Error: Punctuation should be True or False.\n'
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

    # try:
    #     # check the delete after seconds - it needs to be a positive integer or None
    #     delete_check = config['transcribe.config']['delete_after_seconds']
    #     if not delete_check.isnumeric() and delete_check != 'None':
    #         console_message += 'Error: Delete after seconds should be either None or a positive number.\n'
    #         valid = False
    #     if delete_check.isnumeric() and int(delete_check) <= 0:
    #         console_message += "Error: Delete after seconds should be a positive integer.\n"
    #         valid = False
    # except Exception:
    #     console_message += 'Error: Delete after seconds should be either None or a positive number.\n'
    #     valid = False

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
    #delete_after_seconds = None if config['transcribe.config']['delete_after_seconds'] == 'None' else int(config['transcribe.config']['delete_after_seconds'])
    if config['transcribe.config']['language'] == 'en':
        job = client_api.submit_job_local_file(
            filename = audiofile,  # file name
            skip_diarization = False if CHAT_mode else not config.getboolean('transcribe.config', 'diarization'),  # needed for conversations. Tries to match audio with speakers
            skip_punctuation = False if CHAT_mode else not config.getboolean('transcribe.config', 'punctuation'),  # removes punctuations
            remove_disfluencies = False if CHAT_mode else config.getboolean('transcribe.config', 'remove_disfluencies'),  # removes speech disfluencies ("uh", "um"). Only avalable for English, Spanish, French languages
            speaker_channels_count = None if CHAT_mode else speaker_channels_count,  # Number of audio channels. Only avalable for English, Spanish, French languages
            language = config['transcribe.config']['language'],  # language of the audio file(s)
            #delete_after_seconds = delete_after_seconds,  # Amount of time after job completion when job is auto-deleted. Default (after 30 days) is None.
            #verbatim = True,  # transcribe every syllable
            #remove_atmospherics = True,  # remove atmospherics (e.g. <laugh>)
            #filter_profanity = True,  # filter profanities
            #diarization_type = "standard",  # diarization type
            #custom_vocabularies = []  # additional vocabulary
            )
    else:
        job = client_api.submit_job_local_file(
            filename = audiofile,  # file name
            skip_diarization = False if CHAT_mode else not config.getboolean('transcribe.config', 'diarization'),  # needed for conversations. Tries to match audio with speakers
            language = config['transcribe.config']['language'],  # language of the audio file(s)
            #delete_after_seconds = delete_after_seconds,  # Amount of time after job completion when job is auto-deleted. Default (after 30 days) is None.
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
#   csv_file - to output a csv version or not.
def save_transcription(output_data, output_file_name_def, csv_file, CHAT_output):
    replace_dict = {
        "dr.": "Doctor",
        "dr": "Doctor",
        "mr.": "Mister",
        "mrs.": "Missus",
        "mrs": "Missus",
        "mss": "Missus",
        "ms.": "Miss",
        "ms": "Miss",
        "<laugh>": "&=laughs",
        "um": "&-um",
        "uh": "&-uh",
        "er": "&-er",
        "eh": "&-eh"
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
    
    if csv_file:
        if CHAT_output:
            if 'speaker' in output_data[0]:
                for m in range(len(output_data)):
                    output_data[m]['speaker'] = str(int(output_data[m]['speaker']) + 1)
        keys_list = output_data[0].keys()
        csv_filename = output_file_name_def.rsplit('.')[0] + '.csv'
        with open(csv_filename,'w', newline='', encoding = 'utf-8-sig') as outfile:
            csv_writer = csv.DictWriter(outfile, keys_list)
            csv_writer.writeheader()
            csv_writer.writerows(output_data)        
        
    if CHAT_output:
        text_filename = output_file_name_def
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
                        if csv_file:
                            outtextfile.write(''.join(('\nSP', str(int(result_word['speaker'])), ':\t', result_word['transcription'])))
                        else:
                            outtextfile.write(''.join(('\nSP', str(int(result_word['speaker']) + 1), ':\t', result_word['transcription'])))
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
    csv_file = config.getboolean('concatenation', 'csv_file')

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
        output_filename = ''.join((output_folder + 'concatenated_transcription_' + date_today + '.cha'))
        save_transcription(transcript, output_filename, csv_file, CHAT_mode)

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
                output_filename = ''.join((output_folder + audio_file_name + '_transcription_' + date_today + '.cha'))
                save_transcription(transcript, output_filename, csv_file, CHAT_mode)


    print('\nAll transcription is finished')
    # update the GUI if in GUI mode
    if message_label != None:
        message_label.update()
    # Delete folders and files that were created
    delete_temp_folder(temp_folder)


if __name__ == '__main__':
    # Check that entries in config.ini are valid
    # Program will abort if errors are found
    config_message, config_valid = config_check(config)
    print(config_message)
    
    #run the transcription only when every entry is valid
    if not config_valid:
        sys.exit()
    main(None) # pass None to suggest that the program is running in script mode (not using GUI).
