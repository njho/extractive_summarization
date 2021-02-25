import json
import re
import operator
from pydub import AudioSegment
from datetime import timedelta
from text2digits import text2digits

t2d = text2digits.Text2Digits()

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


class Word:
    def __init__(self, word, timestamp=None):
        self.original_word = word
        self.word = clean_word(word)
        self.timestamp = timestamp
        self.del_me = False

    def srt(self):
        return self.timestamp + self.original_word

    def __repr__(self):
        return self.word


def clean_word(word):
    word = re.sub("[^a-z0-9A-Z ]+", "", word)
    word = word.replace(" ", "")
    return word.lower()


transcript_data = read_from_file(TRANSCRIPTION_DATA, json=False)
transcript_data = transcript_data.split("\n")

rev_data = read_from_file(FINAL_TRANSCRIPT, json=False)

rev_data = rev_data.split("\n")
split_transcript_data = []
words_only = []


SAFE_WORDS = ["beep", "", "uh", " ", ""]


def clean_words(all_words):
    new_string = ""
    del_list = []
    for i, word in enumerate(all_words):
        if word.word in SAFE_WORDS:
            del_list.append(i)
            continue
        new_string += word.word + " "

    for i in sorted(del_list, reverse=True):
        del all_words[i]

    prev_split_string = new_string.split(" ")
    prev_split_string = [value for value in prev_split_string if value != ""]
    t2d_split_string = t2d.convert(new_string).split(" ")

    def update_word_list(all_words, prev_split_string, t2d_split_string):
        del_list = []
        update_key = None
        update_word = None

        for word_i, word in enumerate(prev_split_string):
            if word != t2d_split_string[word_i]:

                test_word = ""
                for i in range(3):
                    test_word += f" {all_words[word_i + i].word}"
                    if i == 0:
                        update_key = word_i
                    del_list.append(word_i + i)

                    if t2d_split_string[word_i] == clean_word(t2d.convert(test_word)):
                        update_word = t2d_split_string[word_i]
                        break
                break

        for i in sorted(del_list, reverse=True):
            if i != update_key:
                del prev_split_string[i]
                del t2d_split_string[i]
                del all_words[i]

        if update_word is not None:
            all_words[update_key].word = update_word
            all_words[update_key].original_word = update_word
            all_words[update_key].altered = True

            prev_split_string[update_key] = update_word
            t2d_split_string[update_key] = update_word

            return update_word_list(
                all_words.copy(), prev_split_string, t2d_split_string
            )
        else:
            return all_words

    def remove_inaudible(all_words):
        del_list = []
        for i, word in enumerate(all_words):
            if "inaudible" == word.word:
                # print("Found inaudible")
                del_list.append(i)
                del_list.append(i + 1)
                break

        if len(del_list) == 2:
            for i in sorted(del_list, reverse=True):
                del all_words[i]
            return remove_inaudible(all_words)

        else:
            return all_words

    all_words = update_word_list(all_words, prev_split_string, t2d_split_string)
    all_words = remove_inaudible(all_words)

    return all_words


# timed_words = ""
timed_words = []
for i, item in enumerate(transcript_data):
    split_data = item.split("-->")
    split_transcript_data.append(split_data)

    if len(split_data) == 3:
        word = Word(split_data[2], f"{split_data[0]}-->{split_data[1]}")
        timed_words.append(word)
        # timed_words += split_data[2] + " "


# rev_words = ""
rev_words = []
for i, item in enumerate(rev_data):
    split_data = item.split("                                             ")
    if len(split_data) == 3:
        for word in split_data[2].split(" "):
            rev_words.append(Word(word))
        # rev_words += split_data[2] + " "

# print(rev_words)
words_only = clean_words(timed_words)
rev_words_only = clean_words(rev_words)
# print(f"Rev Words Len: {len(rev_words_only)} vs {len(words_only)}")


def count_score(list1, list2):
    """
    Compares the score between two word lists
    """
    score = 0
    for i, wrd in enumerate(list1):
        if (
            i < len(list2)
            and wrd is not None
            and list2[i] is not None
            and wrd.word == list2[i].word
        ):
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
# for i, word in enumerate(rev_subset):
#     if word.word == "100000":
#         print(i)

# for i, word in enumerate(timed_subset):
#     if word.word == "month":
#         print(i)

# rev_subset = rev_subset[122:]
# timed_subset = timed_subset[136:]

# print("Prev Rev Subset")
# print(rev_subset)
# print("Prev Timed Subset")
# print(timed_subset)

prev_rev_subset = None
prev_shifted_right = False

while len(rev_subset) > 0 and (prev_rev_subset != rev_subset or prev_shifted_right):

    prev_rev_subset = rev_subset.copy()

    for i, word in enumerate(rev_subset):
        word = word.word
        if len(timed_subset) > i:
            other_word = None if timed_subset[i] is None else timed_subset[i].word
            if other_word != word:
                RIGHT_SHIFT_CNT = 7
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
                    matched_sequences.append(
                        [[], timed_subset[0 : i + shift_key].copy()]
                    )

                    # We adjust the subsets
                    rev_subset = rev_subset[i:]
                    for i in range(shift_key):
                        timed_subset.insert(0, None)

                    # Important because the prev_reev_data will not be reset
                    prev_shifted_right = True

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

                    # Important because the prev_reev_data will not be reset
                    prev_shifted_right = False
                else:
                    print("Key is likely 0 ")
                    matched_sequences.append(
                        [[rev_subset[i]].copy(), [timed_subset[i]].copy()]
                    )
                    prev_set = rev_subset.copy()

                    rev_subset = rev_subset[i + 1 :]
                    timed_subset = timed_subset[i + 1 :]

                    prev_shifted_right = False

                print()
                print("=" * 10)
                print("Adjusted Rev Subset")
                print(rev_subset)
                print("Adjusted Timed Subset")
                print(timed_subset)
                print()
                print(prev_rev_subset)
                break

        else:
            print("prev_rev_subset == rev_subset")
            matched_sequences.append([rev_subset, timed_subset])
            rev_subset = []
            timed_subset = []
            prev_word = word

            break

matched_sequences.append([rev_subset, timed_subset])
rev_subset = []
timed_subset = []
prev_word = word


print("==" * 200)
import csv
import itertools

with open("./output.csv", "w") as f:
    wr = csv.writer(f)
    wr.writerow(["Timestamp", "Transcript", "Timed Words"])

    for sequence in matched_sequences:
        print(sequence)
        wr.writerow(["====", "====", "===="])

        thing = list(itertools.zip_longest(sequence[0], sequence[1], fillvalue="-"))

        for item in thing:
            if isinstance(item[1], str) or item[1] is None:
                wr.writerow([item[0], item[1]])
            else:
                wr.writerow([item[1].timestamp, item[0], item[1]])


with open("./srt.srt", "w") as wr:
    for sequence in matched_sequences:
        thing = list(itertools.zip_longest(sequence[0], sequence[1], fillvalue="-"))
        for item in thing:
            wr.write(f"{item[1].timestamp} {item[0].original_word}\n")


def get_ms(string):
    string = string.replace(",", ":")
    h, m, s, ms = map(float, string.split(":"))
    res = (
        timedelta(hours=h, minutes=m, seconds=s, milliseconds=ms).total_seconds() * 1000
    )
    return res

