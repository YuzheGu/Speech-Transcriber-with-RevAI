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
import sys
from pydub import AudioSegment, utils
from rev_ai import apiclient
import configparser

config = configparser.ConfigParser()
config.read('transcription_config.ini')

config_entries = {'API.token':['token'],
                  'folders':['input_folder', 'output_folder'],
                  'concatenation':['input_concatenate', 'plain_text'],
                  'transcribe.config':['skip_diarization', 'skip_punctuation', 'remove_disfluencies', 'speaker_channels_count', 'language']
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

    # Simple way to check if hte the API token is valid
    # Error is generated if it fails retriveinv the last job.
    client = apiclient.RevAiAPIClient(config['API.token']['token'])
    try:
        jobs = client.get_list_of_jobs(limit=1)
    except Exception:
        console_message += "Error: API token is invalid.\n"
        valid = False

    # Check input and output folders
    if not os.path.exists(config['folders']['input_folder']):
        console_message += "Error: Input folder does not exist. Ensure the corret folder name is specified.\n"
        valid = False

    if not os.path.exists(config['folders']['output_folder']):
        console_message += "Error: Output folder does not exist, so we made it. It is named \"output\"\n"
        os.mkdir(config['folders']['output_folder'])

    # checking for other parameters
    if config['concatenation']['input_concatenate'] != "True" and config['concatenation']['input_concatenate'] != "False":
        console_message += "Error: Input concatenate should be True or False.\n"
        valid = False
    if config['concatenation']['plain_text'] != "True" and config['concatenation']['plain_text'] != "False":
        console_message += "Error: Plain text should be True or False.\n"
        valid = False
    if config['transcribe.config']['skip_diarization'] != "True" and config['transcribe.config']['skip_diarization'] != "False":
        console_message += "Error: Skip diarization should be True or False.\n"
        valid = False
    if config['transcribe.config']['skip_punctuation'] != "True" and config['transcribe.config']['skip_punctuation'] != "False":
        console_message += "Error: Skip punctuation should be True or False.\n"
        valid = False
    if config['transcribe.config']['remove_disfluencies'] != "True" and config['transcribe.config']['remove_disfluencies'] != "False":
        console_message += "Error: Remove disfluencies should be True or False.\n"
        valid = False
    try:
        channel_check = config['transcribe.config']['speaker_channels_count']
        if channel_check != '1' and channel_check != 'None':
            console_message += "Error: Speaker channels count should be either None or 1.\n"
            valid = False
        # if channel_check <= 0:
        #     console_message += "Error: Speaker channels count should be a positive integer.\n"
        #     valid = False
    except Exception:
        console_message += "Error: Speaker channels count should be either None or 1.\n"
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
def concatenate_audiofiles(t_folder, afile_list, file_extension):

    # temporary audiofile used to hold concatenated files
    temp_audiofile = "".join((t_folder, 'combinedaudiofiles.', file_extension))

    # initialize an audiosegment for cancatenating audio files
    concatenated_audio = AudioSegment.empty()

    for audiofile in afile_list:
        # Read the audio file in the folder
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

    # Save concatenated sound files to a temporary file for use by rev.ai, next
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
    o_file = original_file_name.rsplit('.')[0].split('/')[1]
    elongated_file_name = ''.join((t_folder, o_file, "_long", ".", file_extension))

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
    print(f"transcribing:{audiofile}")

    # update the GUI if in GUI mode
    if message_label != None:
        message_label.update()

    speaker_channels_count = None if config['transcribe.config']['speaker_channels_count'] == 'None' else 1

    job = client_api.submit_job_local_file(
        filename = audiofile,
        skip_diarization = config.getboolean('transcribe.config', 'skip_diarization'),  # needed for conversations. Tries to match audio with speakers
        skip_punctuation = config.getboolean('transcribe.config', 'skip_punctuation'),
        remove_disfluencies = config.getboolean('transcribe.config', 'remove_disfluencies'),   # Set false for conversations, dialogs
        speaker_channels_count = speaker_channels_count,    # Number of audio channels
        language = config['transcribe.config']['language'])

    # Retrieve transcription job info
    job_details = client_api.get_job_details(job.id)

    # Poll job progress until finished
    # To see all details: var(job_details) in console
    while (job_details.status.name == "IN_PROGRESS"):
        time.sleep(20)
        job_details = client_api.get_job_details(job.id)


    # Grab the transcript or raise an exception on failure
    # See transcription history in your account at rev.ai for explanation
    if job_details.status.name == "TRANSCRIBED":
        transcript_json = client_api.get_transcript_json(job.id)
    elif job_details.status.name == "FAILED":
        failure_message = f"Transcription failed: {job_details.failure}\n{job_details.failure_detail}\n\n"
        if message_label != None:
            # update the GUI if in GUI mode
            message_label.update()
        raise Exception(failure_message)

    transcript = []

    # Assumes a single speaker, else multiple speakers when set to "None"
    # Should this be "== 1" if 2+ channels is formated like "None", number of monologues?
    if speaker_channels_count != None:
        for j, a in enumerate(transcript_json["monologues"][0]["elements"], start=0):
         transcript.append({'filename':audiofile,
                        'transcription':a['value'].lower(),
                        'confidence': a['confidence']})

    else:
        for j in transcript_json["monologues"]:
            # a = ''.join(("Speaker ", str(j['speaker']),":"))
            for a in j['elements']:
                # a = ' '.join((a,str(i['value'])))
                transcript.append({'filename':audiofile,
                               'transcription':a['value'].lower(),
                               'confidence': a['confidence'],
                               'speaker': str(j['speaker'])})


    return transcript


#Save transcriptions to csv file
#Parameters:
#   output_data - transcription data dict.
#   output_file_name_def - the output file name.
#   plain_text - to output a plain text version or not.
def save_transcription(output_data, output_file_name_def, plain_text):
    keys_list = output_data[0].keys()
    with open(output_file_name_def,'w', newline='') as outfile:
        csv_writer = csv.DictWriter(outfile, keys_list)
        csv_writer.writeheader()
        csv_writer.writerows(output_data)
    if plain_text:
        text_filename = output_file_name_def.rsplit('.')[0] + '.txt'
        with open(text_filename,'w', newline='') as outtextfile:
            for result_word in output_data:
                outtextfile.write(result_word['transcription'] + ' ')


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

    # Process the audio files individually or concatenate them into a single file for transcription
    #  For short files, this is more efficient and less costly.
    #True - concatenated. False - individual files
    input_concatenate = config.getboolean('concatenation', 'input_concatenate')
    plain_text = config.getboolean('concatenation', 'plain_text')

    # Used as part of the transcription output filename
    date_time = datetime.datetime.now()
    date_today = date_time.strftime('%m%d%Y')

    supported_extensions = ["mp3", "wav", "ogg", "opus", "flac", "webm"]

    # Make a temporary folder for storing elongated and concatenated audio files
    temp_folder = 'temp/'
    delete_temp_folder(temp_folder)
    os.mkdir(temp_folder)

    # make list of all audio files in input folder that have a supported extension
    audiofile_list = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.rsplit('.')[1] in supported_extensions]

    # check if all audio files have the same extension
    dummy, first_extension = audiofile_list[0].rsplit(".")
    if not all(f.endswith(first_extension) for f in audiofile_list):
        print("Error: All audio files in the input folder must have the same file extension (be the same format).")
        exit()

    # Ensure extension is supported
    if first_extension not in supported_extensions:
        print(f"Error: You are using an unsupported audio format. Spported formats: {supported_extensions} ")
        exit()


    # concatenate the audio files in the list if in input concatenated mode
    if input_concatenate == True:

        audiofile = concatenate_audiofiles(temp_folder, audiofile_list, first_extension)


        transcript = transcribe_speech(audiofile, client_api, message_label)

        # Save all trascriptions in output folder
        output_filename = "".join((output_folder + "concatenated_transcription_" + date_today + ".csv"))
        save_transcription(transcript, output_filename, plain_text)

    # input_concatenate = False
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
                # prefix = name of audio file
                prefix =  re.split('[/.]', audiofile)[-2]
                output_filename = "".join((output_folder + prefix + "_transcription_" + date_today + ".csv"))
                save_transcription(transcript, output_filename, plain_text)


    print("\nAll transcription is finished")
    # update the GUI if in GUI mode
    if message_label != None:
        message_label.update()
    # Delete folders and files that were created
    delete_temp_folder(temp_folder)

if __name__ == "__main__":
    try:
        # Check that entries in ini are valid
        # Program will abort if errors are found
        config_message, config_valid = config_check(config)
        print(config_message)

        #run the transcription only when every entry is valid
        if not config_valid:
           exit()
        main(None) # pass None to suggest that the program is running in script mode and no gui used.
    except Exception:
        print("Error: exception found, program exited.")
        exit()
