Use virtual environment with python 3.6.9 (NOTE: It will have dependency issues with >= Python 3.7)

Download the code from <a href="https://github.com/TalatIqbal/extractive_summarization.git">Extractive Summarization github</a>

Install all the required packages by running the following command

pip install -r requirements.txt

Input format: 
The input file is of the following format
--------- START ----------
1
00:00:03,030 --> 00:00:03,120
All

2
00:00:03,120 --> 00:00:03,420
right.

3
00:00:03,420 --> 00:00:03,840
Hey,
----------- END ------------

Output File format
The output file will contain a file that will have a list of sentences, each sentence with the start time and end time

--------- START ----------
00:00:03,420-->00:00:10,190-->Hey, John and Breton, uh, wanting to send over this screen cap to give you a glimpse into what I've been working on
00:00:19,065-->00:00:31,085-->So, uh, right here, this is kind of the, kind of more on earth on your side, type of like what we would set up a config to look like, uh, for the API we'd be building for the pre script build
----------- END ------------

Functions: 
The primary function is the extract() function that takes in the following parameters
input_file (string) - The file path of the .srt file
output_file (string) - The file path of a text file
num_sentences (int) = The number of sentences required for the output
