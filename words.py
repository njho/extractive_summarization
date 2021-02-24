import json
import re
import operator
from pydub import AudioSegment
from datetime import timedelta

INPUT_FILE = "./test.mp3"
TRANSCRIPTION_DATA = "./data/podcast__transcription_test_op_10.txt"
FINAL_TRANSCRIPT = "./final.txt"


def read_from_file(file_path, json=True):
    with open(file_path, "r") as f:
        val = f.read()
        if json:
            return json.loads(val)
        else:
            return val


transcript_data = read_from_file(TRANSCRIPTION_DATA, json=False)
transcript_data = transcript_data.split("\n")

rev_data = read_from_file(FINAL_TRANSCRIPT, json=False)

rev_data = rev_data.split("\n")
split_transcript_data = []
words_only = []

for i, item in enumerate(transcript_data):
    split_data = item.split("-->")
    split_transcript_data.append(split_data)
    if len(split_data) == 3:
        words_only.extend(split_data[2].replace("uh", "").replace("  ", " ").split(" "))

split_rev_data = []
rev_words_only = []
for i, item in enumerate(rev_data):
    split_data = item.split("                                             ")
    split_rev_data.append(split_data)
    if len(split_data) == 3:
        rev_words_only.extend(
            split_data[2]
            .replace("\\", "")
            .replace("uh", "")
            .replace("  ", " ")
            .split(" ")
        )


def clean_word(word):
    word = re.sub("[^a-z0-9A-Z ]+", "", word)
    return word.lower()


words_only = [clean_word(item) for item in words_only]
rev_words_only = [clean_word(item) for item in rev_words_only]


# print(words_only[0:30])
# print(rev_words_only[0:30])

print(f"Rev Words Len: {len(rev_words_only)} vs {len(words_only)}")

adjustment = 0


def count_score(list1, list2):
    """
    Compares the score between two word lists
    """
    score = 0
    for i, wrd in enumerate(list1):
        if i < len(list2) and wrd == list2[i]:
            score += 1
    return score


def calculate_score(list1, list2):
    """
    Compares the score between two word lists. We shift list2 left and right it's length
    """

    temp_list2 = list2.copy()
    shift_scores = {}
    # GET SCORE CURRENTLY
    shift_scores[0] = count_score(list1, temp_list2)

    # SHIFT IT LEFT
    for i in range(len(list2)):
        key = -(i + 1)
        temp_list2.pop(0)
        shift_scores[key] = count_score(list1, temp_list2)

    temp_list2 = list2.copy()
    # SHIFT IT RIGHT
    for i in range(len(list1)):
        key = i + 1
        temp_list2.insert(0, None)
        shift_scores[key] = count_score(list1, temp_list2)

    return shift_scores


matched_sequences = []

rev_subset = rev_words_only.copy()
timed_subset = words_only.copy()

prev_set = None
while len(rev_subset) > 0:
    print("=" * 100)

    for i, word in enumerate(rev_subset):
        if len(timed_subset) > i:
            other_word = timed_subset[i]
            if other_word != word:
                RIGHT_SHIFT_CNT = 13
                prev_rev_words = timed_subset[i - 10 : i]
                prev_timed_words = timed_subset[i - 10 : i]
                future_timed_words = timed_subset[i : i + RIGHT_SHIFT_CNT]
                future_rev_words = rev_subset[i : i + RIGHT_SHIFT_CNT]

                print("=" * 10)
                print("rev: ", prev_rev_words, word)
                print("timed: ", prev_timed_words, other_word)
                print("Analyze Rev: ", future_rev_words)
                print("Analyze Timed: ", future_timed_words)

                all_scores = calculate_score(future_rev_words, future_timed_words)
                print(all_scores.values())
                shift_key, score = max(all_scores.items(), key=operator.itemgetter(1))

                matched_rev_sequence = rev_subset[0:i]
                matched_timed_words = timed_subset[0:i]
                matched_sequences.append([matched_rev_sequence, matched_timed_words])

                print()
                print("Pushing Simple Sequence")
                print(matched_rev_sequence)
                print(matched_timed_words)
                print()

                shift_key = int(shift_key)
                if shift_key > 0:
                    print(f"Found a shift right with {shift_key} and score: {score}")
                    print("Pushing right Sequence")
                    print([])
                    print(timed_subset[0 : i + shift_key])
                    matched_sequences.append("From Right")
                    matched_sequences.append(
                        [[], timed_subset[0 : i + shift_key].copy()]
                    )

                    # We adjust the subsets
                    rev_subset = rev_subset[i:]
                    for i in range(shift_key):
                        timed_subset.insert(0, None)

                elif shift_key < 0:
                    print(f"Found a shift left with {shift_key} and score: {score}")
                    print("Pushing left Sequence")
                    # print(rev_subset[i : i - shift_key])
                    # print([])
                    # matched_sequences.append("From Left")
                    # matched_sequences.append([rev_subset[i : i - shift_key].copy(), []])

                    # We adjust the subsets
                    prev_set = rev_subset.copy()
                    rev_subset = rev_subset[i:]
                    timed_subset = timed_subset[i - shift_key :]

                else:
                    print("Key is likely 0 ")
                    matched_sequences.append(
                        [[rev_subset[i]].copy(), [timed_subset[i]].copy()]
                    )
                    prev_set = rev_subset.copy()

                    rev_subset = rev_subset[i + 1 :]
                    timed_subset = timed_subset[i + 1 :]

                print()
                print("=" * 10)
                print("Adjusted")
                print(rev_subset)
                print(timed_subset)
                print(f"Finished with {i} and last_match")

                break

        else:
            matched_sequences.append([rev_subset, timed_subset])
            rev_subset = []
            timed_subset = []
            prev_word = word

            break

    if prev_set == rev_subset:
        matched_sequences.append([rev_subset, timed_subset])
        rev_subset = []
        timed_subset = []
        prev_word = word

        break

import csv
import itertools

with open("./output.csv", "w") as f:
    wr = csv.writer(f)
    wr.writerow(["Transcript", "Timed Words"])

    for sequence in matched_sequences:
        print(sequence)
        wr.writerow(["====", "===="])

        thing = list(itertools.zip_longest(sequence[0], sequence[1], fillvalue="-"))
        for item in thing:
            wr.writerow(item)


def get_ms(string):
    string = string.replace(",", ":")
    h, m, s, ms = map(float, string.split(":"))
    res = (
        timedelta(hours=h, minutes=m, seconds=s, milliseconds=ms).total_seconds() * 1000
    )
    return res

