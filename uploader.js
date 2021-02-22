'use strict';

/* 	==================================
	 PING
	 > web.js
	 -------------------------------- 
	 Web
	 -------------------------------- 
	 1. Spotify connect
	 2. User creation
	 3. Share link
	================================== 	*/

/*  ----------------------------------------------
	== BOILERPLATE
	---------------------------------------------- */

/*  >>>> Require
	---------------------------------------------- */
var speech = require('@google-cloud/speech'),
  fs = require('fs'),
  tr = require('textrank'),
  SoxCommand = require('sox-audio'),
  async = require('async'),
  _ = require('lodash');

/*  >>>> Vars
	---------------------------------------------- */
var Vars = {
  Settings: {
    audio: {
      secondsCountsAsContinuation: 2,
      nanosDivisor: 100000000,

      extendClipBySeconds: 0.4,
      padBetweenClipsWithSeconds: 1.5,
      padOutsideClipsWithSeconds: 0.5,
    },
  },

  audio: {
    // path: 'trimmed.wav',
    // uri: 'gs://aerial-grid-233801.appspot.com/trimmed.wav',
    // path: 'the_hustle-source-clipped.wav',
    // uri: 'gs://aerial-grid-233801.appspot.com/audio/the_hustle-source-clipped.wav',

    // path: '20minvc-mono_audacity.wav',
    // uri: 'gs://aerial-grid-233801.appspot.com/audio/20minvc-mono_audacity.wav',

    path: 'petit_trimmed.wav',
    uri: 'gs://aerial-grid-233801.appspot.com/audio/petit.wav',
  },
};

/*  ----------------------------------------------
	== PROCESS
	---------------------------------------------- */

/*  >>>> Google Cloud Speech to Text
	---------------------------------------------- */
async function main() {
  // Creates a client
  const client = new speech.SpeechClient();

  // // The name of the audio file to transcribe
  // 	const fileName = Vars.audio.path; // './resources/audio.raw';

  // // Reads a local audio file and converts it to base64
  // 	const file = fs.readFileSync(fileName);
  // 	const audioBytes = file.toString('base64');

  // The audio file's encoding, sample rate in hertz, and BCP-47 language code
  const audio = {
    // content: audioBytes,
    uri: Vars.audio.uri,
  };
  const config = {
    // encoding: 'LINEAR16',
    // sampleRateHertz: 16000,
    // audioChannelCount: 2,
    languageCode: 'en-US',
    enableWordTimeOffsets: true,
    enableAutomaticPunctuation: true,
  };
  const request = {
    audio: audio,
    config: config,
  };

  // Do speech detection
  client
    .longRunningRecognize(request, {
      longrunning: {
        initialRetryDelayMillis: 100,
        retryDelayMultiplier: 1,
        maxRetryDelayMillis: 60000,
        initialRpcTimeoutMillis: null,
        rpcTimeoutMultiplier: null,
        maxRpcTimeoutMillis: null,
        totalTimeoutMillis: 3600000, //null
      },
      deadline: new Date(Date.now() + 3600000),
    })
    .then(responses => {
      var operation = responses[0];
      var initialApiResponse = responses[1];

      // Adding a listener for the "complete" event starts polling for the
      // completion of the operation.
      operation.on('complete', (response, metadata, finalApiResponse) => {
        // doSomethingWith(response);
        // console.log("RESULT: ", response.results, response.results[0].alternatives[0].transcript);
        // console.log("METADATA: ", metadata);
        // console.log("FINAL API RESPONSE: ", finalApiResponse);

        // Save the responses
        fs.writeFile(
          Vars.audio.path + '-response.txt',
          JSON.stringify(response),
          function (err) {
            console.log(' > Writing -response.txt');

            fs.writeFile(
              Vars.audio.path + '-metadata.txt',
              JSON.stringify(metadata),
              function (err) {
                console.log(' > Writing -metadata.txt');

                fs.writeFile(
                  Vars.audio.path + '-finalApiResponse.txt',
                  JSON.stringify(finalApiResponse),
                  function (err) {
                    console.log(' > Writing -finalApiResponse.txt');

                    // Compose the transcript (from async promised results)
                    const transcription = response.results
                      .map(result => result.alternatives[0].transcript)
                      .join('\n');

                    // Save the transcript (just in case)
                    fs.writeFile(
                      Vars.audio.path + '.txt',
                      transcription,
                      function (err) {
                        console.log(' > Writing .txt (transcription)');
                        if (!err) {
                          console.log(' > Running extraction summarizer.');
                          // Run extraction summarizer
                          var textRank = new tr.TextRank(transcription, {
                            // extractAmount: 2,
                            summaryType: 'array',
                          });
                          var summarizedArticleArray =
                            textRank.summarizedArticle;
                          // console.log(summarizedArticleArray);
                          // console.log(textRank, textRank.summarizedArticle);

                          // Use word timestamps to grab audio ranges for extracted sentences
                          var wordsArr = response.results.map(
                            result => result.alternatives[0].words,
                          );
                          wordsArr = _.flatten(wordsArr);
                          console.log(wordsArr);
                          // var wordsArr = response.results[0].alternatives[0].words;
                          // console.log("wordsArr", wordsArr, wordsArr[0].word, wordsArr[0].startTime.seconds, wordsArr[0].startTime.nanos, wordsArr[0].endTime.seconds, wordsArr[0].endTime.nanos);

                          // Set up relevant audio ranges to trim audio to
                          var relevantAudioRanges = [];

                          // For each extracted sentence...
                          console.log(
                            ' > Grabbing timestamps for extracted sentences...',
                          );
                          _.each(
                            summarizedArticleArray,
                            function (sentence, idx) {
                              // Find the sentence in the `transcription`
                              var sentencePositionInTranscript = transcription.search(
                                sentence,
                              );
                              if (sentencePositionInTranscript > -1) {
                                // Find start/end times by counting words before sentence
                                var tmpTranscriptBeforeSentence = transcription.substr(
                                  0,
                                  sentencePositionInTranscript - 1,
                                );
                                // console.log("tmpTranscriptBeforeSentence", tmpTranscriptBeforeSentence);

                                // Count number of words in `tmpTranscriptBeforeSentence`
                                var wordsArrStartIdx = tmpTranscriptBeforeSentence.split(
                                  ' ',
                                ).length;
                                // console.log("wordsArrStartIdx", wordsArrStartIdx);

                                // Count number of words in `sentence`
                                var wordsArrEndAtLength = sentence.split(' ')
                                  .length;
                                // console.log("wordsArrEndAtLength", wordsArrEndAtLength);

                                // Grab relevant word info from `wordsArr`. First(start) + Last(end) are our audio bounds
                                // console.log(wordsArr[wordsArrStartIdx], wordsArr[wordsArrStartIdx + wordsArrEndAtLength - 1])
                                var proposedStartTime =
                                  wordsArr[wordsArrStartIdx].startTime;
                                var proposedEndTime =
                                  wordsArr[
                                    wordsArrStartIdx + wordsArrEndAtLength - 1
                                  ].endTime;

                                // Add some time to proposedEndTime (`Vars.Settings.audio.extendClipBySeconds`)
                                var adjustedEndTime = parseFloat(
                                  parseFloat(
                                    proposedEndTime.seconds +
                                      '.' +
                                      proposedEndTime.nanos /
                                        Vars.Settings.audio.nanosDivisor,
                                  ) +
                                    parseFloat(
                                      Vars.Settings.audio.extendClipBySeconds,
                                    ),
                                ).toFixed(2);
                                var splitEndTime = adjustedEndTime.split('.');
                                proposedEndTime.seconds = splitEndTime[0].toString();
                                proposedEndTime.nanos = parseInt(
                                  splitEndTime[1] *
                                    Vars.Settings.audio.nanosDivisor,
                                );

                                // console.log("ADJUSTED END TIME: ", proposedEndTime);

                                // Is startTime.seconds outside of x seconds of the last endTime?
                                // console.log(proposedStartTime, relevantAudioRanges[relevantAudioRanges.length - 1], Vars.Settings.audio.secondsCountsAsContinuation);

                                if (
                                  _.isEmpty(relevantAudioRanges) ||
                                  proposedStartTime.seconds >
                                    parseInt(
                                      relevantAudioRanges[
                                        relevantAudioRanges.length - 1
                                      ][1].seconds,
                                    ) +
                                      Vars.Settings.audio
                                        .secondsCountsAsContinuation
                                ) {
                                  // [1] = endTime in array of [start, end]

                                  // Push it into the array as a new audio position to keep
                                  relevantAudioRanges.push([
                                    proposedStartTime,
                                    proposedEndTime,
                                    sentence,
                                  ]);

                                  // No, so it's a continuation.
                                } else {
                                  // Just edit the last one to use the proposedEndTime
                                  relevantAudioRanges[
                                    relevantAudioRanges.length - 1
                                  ][1] = proposedEndTime;
                                  relevantAudioRanges[
                                    relevantAudioRanges.length - 1
                                  ][2] += ' ' + sentence;
                                }
                              } else {
                                console.log(
                                  "ERROR: Couldn't find sentence in transcript:",
                                  sentence,
                                );
                              }
                            },
                          );

                          // Set up trim commands for relevant ranges
                          console.log(' > Preparing to write trim commands.');
                          var compiledTrimCommand = '';
                          var compiledPadCommand = '';
                          var compiledPadTimeCounter = 0;

                          // console.log(relevantAudioRanges);
                          console.log(' > Writing trim commands.');
                          _.each(relevantAudioRanges, function (range, idx) {
                            // async.forEachOf(relevantAudioRanges, (range, idx, callback) => {
                            // Evaluating range:

                            // console.log(" > ", [parseFloat(range[0].seconds + "." + range[0].nanos / Vars.Settings.audio.nanosDivisor), parseFloat(range[1].seconds + "." + range[1].nanos / Vars.Settings.audio.nanosDivisor)], compiledPadTimeCounter, range[2]); //range[2] = sentence

                            // Use Sox to trim. Compose trim command to keep all ranges [start, end] and output new audio
                            //- `sox trimmed.wav output.wav trim =12 =22.4 =33.5 =41.6 =45.1 =54.1`
                            // console.log(range);
                            compiledTrimCommand =
                              compiledTrimCommand +
                              ' =' +
                              parseFloat(
                                range[0].seconds +
                                  '.' +
                                  range[0].nanos /
                                    Vars.Settings.audio.nanosDivisor,
                              ) + // (idx == 0 ? " " : " =")
                              ' =' +
                              parseFloat(
                                range[1].seconds +
                                  '.' +
                                  range[1].nanos /
                                    Vars.Settings.audio.nanosDivisor,
                              );

                            if (idx < relevantAudioRanges.length - 1) {
                              var rangeLength = parseFloat(
                                parseFloat(
                                  range[1].seconds +
                                    '.' +
                                    range[1].nanos /
                                      Vars.Settings.audio.nanosDivisor,
                                ) -
                                  parseFloat(
                                    range[0].seconds +
                                      '.' +
                                      range[0].nanos /
                                        Vars.Settings.audio.nanosDivisor,
                                  ),
                              ).toFixed(2);
                              compiledPadTimeCounter = parseFloat(
                                parseFloat(compiledPadTimeCounter) +
                                  parseFloat(rangeLength),
                              ).toFixed(2);

                              compiledPadCommand =
                                compiledPadCommand +
                                ' pad ' +
                                Vars.Settings.audio.padBetweenClipsWithSeconds +
                                '@=' +
                                parseFloat(
                                  parseFloat(compiledPadTimeCounter) +
                                    parseFloat(
                                      parseInt(idx) *
                                        parseFloat(
                                          Vars.Settings.audio
                                            .padBetweenClipsWithSeconds,
                                        ),
                                    ),
                                ).toFixed(2);
                            }
                          });

                          // Trim audio
                          // console.log("|sox trimmed.wav trim" + compiledTrimCommand);
                          console.log(' > Trimming audio...');
                          console.log(
                            '\n|sox ' +
                              Vars.audio.path +
                              ' SYNTHED-' +
                              Vars.audio.path +
                              ' trim' +
                              compiledTrimCommand +
                              compiledPadCommand,
                          );
                          var trimAudio = SoxCommand().input(
                            '|sox trimmed.wav output.wav trim' +
                              compiledTrimCommand +
                              compiledPadCommand,
                          );
                          // .outputFileType('wav')
                          // .output('-p');
                          // .input('|sox trimmed.wav -t wav -p trim' + compiledTrimCommand);

                          // Sox Events
                          trimAudio.on('start', function (commandLine) {
                            console.log(
                              ' > Spawned sox with command ' + commandLine,
                            );
                          });
                          trimAudio.on('progress', function (progress) {
                            console.log(' > Processing progress: ', progress);
                          });
                          trimAudio.on('error', function (err, stdout, stderr) {
                            console.log(
                              ' > Cannot process audio: ' + err.message,
                            );
                            console.log(' > Sox Command Stdout: ', stdout);
                            console.log(' > Sox Command Stderr: ', stderr);
                          });
                          trimAudio.on('end', function () {
                            console.log(' > Sox command succeeded!');
                          });

                          // Run Trim
                          trimAudio.run();

                          // Done
                          console.log(' > Done.');
                        } else {
                          console.log(
                            'Could not write transcript to local file.',
                          );
                        }
                      },
                    );
                  },
                );
              },
            );
          },
        );
      });

      // Adding a listener for the "progress" event causes the callback to be
      // called on any change in metadata when the operation is polled.
      operation.on('progress', (metadata, apiResponse) => {
        // doSomethingWith(metadata)
        console.log(
          'Progressing... ' + (metadata.progressPercent || 0) + '%\n',
        );

        if (apiResponse.done && !apiResponse.response) {
          operation.emit('error');
        }
      });

      // Adding a listener for the "error" event handles any errors found during polling.
      operation.on('error', err => {
        // throw(err);
        console.log('Speech polling error: ', err);
      });
    })
    .catch(err => {
      console.error(err);
    });
}
main().catch(console.error);

// console.log("Starting...");
// var compiledPadTimeCounter = 0;
// var compiledTrimCommand = "";
// var relevantAudioRanges = [
// 	[{ seconds: '12', nanos: 0 }, { seconds: '22', nanos: 400000000 }],
// 	[{ seconds: '33', nanos: 500000000 }, { seconds: '41', nanos: 300000000 }],
// 	[{ seconds: '45', nanos: 100000000 }, { seconds: '54', nanos: 200000000 }]
// ];
// _.each(relevantAudioRanges, function(range, idx){
// // Echo Evaluation
// 	console.log(" > Evaluating range: ", [parseFloat(range[0].seconds + "." + range[0].nanos / Vars.Settings.audio.nanosDivisor), parseFloat(range[1].seconds + "." + range[1].nanos / Vars.Settings.audio.nanosDivisor)], compiledPadTimeCounter, range[2]);

// // Use Sox to trim. Compose trim command to keep all ranges [start, end] and output new audio
// 	// console.log(range);
// 	compiledTrimCommand = compiledTrimCommand
// 						+ " =" + parseFloat(range[0].seconds + "." + range[0].nanos / Vars.Settings.audio.nanosDivisor) // (idx == 0 ? " " : " =")
// 						+ " =" + parseFloat(range[1].seconds + "." + range[1].nanos / Vars.Settings.audio.nanosDivisor);

// 						console.log(" >>> Trim command: ", compiledTrimCommand);

// // Pad Time Counter test
// 	// var rangeLength = parseFloat(parseFloat(range[1].seconds + "." + range[1].nanos) - parseFloat(range[0].seconds + "." + range[0].nanos)).toFixed(2);

// 	// 	console.log("START: ", compiledPadTimeCounter, " + " + rangeLength);

// 	// compiledPadTimeCounter = parseFloat(parseFloat(compiledPadTimeCounter) + parseFloat(rangeLength)).toFixed(2);

// 	// 	console.log("END: ", compiledPadTimeCounter);
// });
// console.log("Ended!");
