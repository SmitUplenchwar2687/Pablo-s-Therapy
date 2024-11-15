import 'dart:io';
import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:rive/rive.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:logger/logger.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class Session extends StatefulWidget {
  final String name;
  const Session({super.key, required this.name});

  @override
  SessionState createState() => SessionState();
}

class SessionState extends State<Session> {
  double _scaleFactor = 0.5;
  bool useMicInput = true;
  bool _isRecording = false;
  bool _isPlaying = false;
  final myRecorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  double volume = 0.0;
  double minVolume = -45.0;
  Timer? timer;
  var logger = Logger();
  WebSocketChannel? _channel;
  late File _audioFile;

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  void _connectWebSocket() {
    _channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8000/ws/chat'));
  }

  Future<String> getFilePath() async {
    final directory = await getApplicationDocumentsDirectory();
    return '${directory.path}/myFile.wav';
  }

  Future<void> requestPermissionAndStartRecording() async {
    if (await myRecorder.hasPermission()) {
      startRecording();
    } else {
      logger.e("Microphone Access is denied");
    }
  }

  Uint8List convertPcmToWav(List<int> pcmData,
      {int sampleRate = 44100, int numChannels = 1, int bitsPerSample = 16}) {
    // Validate that pcmData values are in 16-bit range
    for (int sample in pcmData) {
      if (sample < -32768 || sample > 32767) {
        throw ArgumentError("PCM data value out of range for 16-bit audio");
      }
    }

    // Create a ByteData to write the WAV file
    var wavHeaderSize = 44; // Standard WAV header size
    var totalSize = wavHeaderSize + pcmData.length * 2;
    var byteData = ByteData(totalSize);

    // Write the RIFF header
    byteData.setUint8(0, 'R'.codeUnitAt(0));
    byteData.setUint8(1, 'I'.codeUnitAt(0));
    byteData.setUint8(2, 'F'.codeUnitAt(0));
    byteData.setUint8(3, 'F'.codeUnitAt(0));
    byteData.setUint32(4, totalSize - 8, Endian.little);
    byteData.setUint8(8, 'W'.codeUnitAt(0));
    byteData.setUint8(9, 'A'.codeUnitAt(0));
    byteData.setUint8(10, 'V'.codeUnitAt(0));
    byteData.setUint8(11, 'E'.codeUnitAt(0));

    // Write the fmt subchunk
    byteData.setUint8(12, 'f'.codeUnitAt(0));
    byteData.setUint8(13, 'm'.codeUnitAt(0));
    byteData.setUint8(14, 't'.codeUnitAt(0));
    byteData.setUint8(15, ' '.codeUnitAt(0));
    byteData.setUint32(16, 16, Endian.little); // Subchunk size
    byteData.setUint16(20, 1, Endian.little); // Audio format (1 = PCM)
    byteData.setUint16(22, numChannels, Endian.little);
    byteData.setUint32(24, sampleRate, Endian.little);
    byteData.setUint32(28, sampleRate * numChannels * (bitsPerSample ~/ 8),
        Endian.little); // Byte rate
    byteData.setUint16(
        32, numChannels * (bitsPerSample ~/ 8), Endian.little); // Block align
    byteData.setUint16(34, bitsPerSample, Endian.little);

    // Write the data subchunk
    byteData.setUint8(36, 'd'.codeUnitAt(0));
    byteData.setUint8(37, 'a'.codeUnitAt(0));
    byteData.setUint8(38, 't'.codeUnitAt(0));
    byteData.setUint8(39, 'a'.codeUnitAt(0));
    byteData.setUint32(40, pcmData.length * 2, Endian.little);
    for (int i = 0; i < pcmData.length; i++) {
      byteData.setInt16(wavHeaderSize + i * 2, pcmData[i], Endian.little);
    }

    return byteData.buffer.asUint8List();
  }

  Future<bool> startRecording() async {
    final path = await getFilePath();
    if (await myRecorder.hasPermission()) {
      if (!await myRecorder.isRecording()) {
        await myRecorder.start(RecordConfig(encoder: AudioEncoder.wav), path: path);
        setState(() {
          _isRecording = true;
        });
      }
      startTimer();
      return true;
    } else {
      return false;
    }
  }

  Future<void> stopRecording() async {
    await myRecorder.stop();
    final path = await getFilePath();
    File file = File(path);
    List<int> fileBytes = await file.readAsBytes();
    _channel!.sink.add(fileBytes);
    timer?.cancel();
    setState(() {
      _isRecording = false;
    });
    ListenWebSocket();
  }

  Future<void> ListenWebSocket() async {
    _channel?.stream?.listen(
      (data) {
        if (data is Uint8List) {
          // Write received binary data (WAV file) to a file
          _writeToFile(data);
        }
      },
      onError: (error) {
        print('WebSocket Error: $error');
      },
      onDone: () {
        print('WebSocket connection closed');
      },
    );
  }

  Future<void> _writeToFile(Uint8List data) async {
    final directory = await getApplicationDocumentsDirectory();
    final filePath = '${directory.path}/received_audio.wav';

    _audioFile = File(filePath);
    await _audioFile.writeAsBytes(data);
    print('File saved to $filePath');

    _playAudio();
  }

  Future<void> _playAudio() async {
    await _audioPlayer.play(DeviceFileSource(_audioFile.path));
    setState(() {
      _isPlaying = true;
    });
  }

  Future<void> pauseAudio() async {
    await _audioPlayer.pause();
    setState(() {
      _isPlaying = false;
    });
  }

  Future<void> stopAudio() async {
    await _audioPlayer.stop();
    setState(() {
      _isPlaying = false;
    });
  }

  startTimer() async {
    timer ??= Timer.periodic(
      const Duration(milliseconds: 50), (timer) => updateVolume());
  }

  updateVolume() async {
    Amplitude ampl = await myRecorder.getAmplitude();
    if (ampl.current > minVolume) {
      setState(() {
        volume = (ampl.current - minVolume) / minVolume;
        _scaleFactor = 0.5 - (volume * 1.25);
      });
    }
  }

  int volume0to(int maxVolumeToDisplay) {
    return (volume * maxVolumeToDisplay).round().abs();
  }

  @override
  void dispose() {
    timer?.cancel();
    myRecorder.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text('Session'),
      ),
      body: Container(
        color: Colors.white,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Transform.scale(
                scale: _scaleFactor,
                child: const SizedBox(
                  width: 300,
                  height: 300,
                  child: RiveAnimation.asset('images/pablo.riv'),
                ),
              ),
              Text(
                'Ye Sab Kuch Nai Hota h ${widget.name}!',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              Text(
                'Padhle Chutiye! 😒',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              Text(
                "VOLUME\n${volume0to(100)}",
                textAlign: TextAlign.center,
              ),
              ElevatedButton(
                onPressed: _isRecording ? stopRecording : requestPermissionAndStartRecording,
                child: Text(_isRecording ? 'Stop Streaming' : 'Start Streaming'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

