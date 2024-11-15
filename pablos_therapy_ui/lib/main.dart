import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'login.dart';
import 'package:rive/rive.dart';

void main() {
  runApp(const PablosTheraphy());
}

class PablosTheraphy extends StatelessWidget {
  const PablosTheraphy({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pablo Therapy',
      theme: ThemeData(
        useMaterial3: true,
        fontFamily: 'Geist',
      ),
      home: Scaffold(
        appBar: AppBar(
          backgroundColor: const Color(0x00000000),
          title: const Text(
            'Pablo Therapy'
          ),
        ),
        extendBodyBehindAppBar: true,
        body: Stack(
          children: [
            const RiveAnimation.asset(
              'images/background.riv',
              fit: BoxFit.cover,
            ),
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SvgPicture.asset(
                    'images/home.svg',
                    width: 200,
                    height: 200,
                  ),
                  Padding(
                    padding: const EdgeInsets.all(31),
                    child: Builder(
                      builder: (context) => const Login(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
